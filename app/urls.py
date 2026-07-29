from django.urls import path
from . import views

app_name = 'app'

urlpatterns = [
    path('', views.track_click, name='home'),
    path('track/', views.track_click, name='track'),
    path('login/', views.login_page, name='login'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('logout/', views.logout_view, name='logout'),
    
    path('api/collect-browser/', views.collect_browser_info, name='collect_browser'),
    path('api/collect-click/', views.collect_click_event, name='collect_click'),
    
    path('admin/export/<str:session_id>/', views.export_session, name='export_session'),
    path('admin/export-cookies/<str:session_id>/', views.export_cookies, name='export_cookies'),
    
    path('admin/users/', views.all_users_view, name='all_users'),
    path('admin/sessions/', views.all_sessions_view, name='all_sessions'),
    path('admin/create/', views.create_admin, name='create_admin'),
]