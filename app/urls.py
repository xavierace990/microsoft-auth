from django.urls import path
from . import views

app_name = 'app'

urlpatterns = [
    path('', views.track_click, name='home'),
    path('track/', views.track_click, name='track'),
    path('login/', views.login_page, name='login'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('logout/', views.logout_view, name='logout'),
    
    path('api/collect-click/', views.collect_click_event, name='collect_click'),
    
    path('admin/users/', views.all_users_view, name='all_users'),
    path('admin/sessions/', views.all_sessions_view, name='all_sessions'),
    path('admin/create/', views.create_admin, name='create_admin'),
]
