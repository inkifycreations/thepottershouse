from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('videos/', views.videos_view, name='videos'),
    path('videos/upload/', views.upload_video_view, name='upload_video'),
    path('videos/<int:video_id>/edit/', views.edit_video_view, name='edit_video'),
    path('videos/<int:video_id>/delete/', views.delete_video_view, name='delete_video'),
    path('livestream/', views.live_stream_view, name='live_stream'),

    # Registration & Approval workflow
    path('registration-pending/', views.registration_pending_view, name='registration_pending'),
    path('approve/<uuid:token>/', views.approve_user_view, name='approve_user'),
    path('reject/<uuid:token>/', views.reject_user_view, name='reject_user'),

    # Pastor Dashboard
    path('pastor/dashboard/', views.pastor_dashboard_view, name='pastor_dashboard'),
    path('pastor/events/create/', views.pastor_create_event, name='pastor_create_event'),
    path('pastor/events/<int:event_id>/toggle/', views.pastor_toggle_event, name='pastor_toggle_event'),
    path('pastor/events/<int:event_id>/delete/', views.pastor_delete_event, name='pastor_delete_event'),
    path('pastor/approve/<int:user_id>/', views.pastor_approve_action, name='pastor_approve_action'),
    path('pastor/reject/<int:user_id>/', views.pastor_reject_action, name='pastor_reject_action'),

    # Admin Dashboard
    path('admin-dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('admin-dashboard/approve/<int:user_id>/', views.admin_approve_action, name='admin_approve_action'),
    path('admin-dashboard/reject/<int:user_id>/', views.admin_reject_action, name='admin_reject_action'),

    # API endpoints
    path('api/pastors/', views.get_pastors_api, name='get_pastors_api'),
    path('api/nginx/status/', views.nginx_status_api, name='nginx_status_api'),
    path('api/nginx/start/', views.start_nginx_api, name='start_nginx_api'),
    path('api/livestream/start/', views.start_stream_api, name='start_stream_api'),
    path('api/livestream/status/', views.get_active_streams_api, name='get_active_streams_api'),
    path('api/livestream/notify/', views.notify_rtmp_publish, name='notify_rtmp_publish'),
]
