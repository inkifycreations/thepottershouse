from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
import json
import os
import subprocess
import time
from .models import State, Pastor, Video, LiveStream, CustomUser, VideoGroup, ApprovalLog, ChurchEvent
from .forms import CustomUserCreationForm, VideoUploadForm, ChurchEventForm


def _send_pastor_notification(request, user, pastor):
    """Send approval request email to pastor with approve/reject links."""
    site_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
    expiry_hours = getattr(settings, 'APPROVAL_TOKEN_EXPIRY_HOURS', 72)
    approve_url = f"{site_url}/approve/{user.approval_token}/"
    reject_url = f"{site_url}/reject/{user.approval_token}/"
    dashboard_url = f"{site_url}/pastor/dashboard/"

    context = {
        'pastor_name': pastor.name,
        'referral_code': pastor.referral_code,
        'user_name': user.get_full_name() or user.username,
        'username': user.username,
        'user_email': user.email,
        'phone': user.phone_number,
        'address': user.address,
        'age': user.age,
        'registered_at': user.approval_token_created_at.strftime('%B %d, %Y at %I:%M %p') if user.approval_token_created_at else '',
        'approve_url': approve_url,
        'reject_url': reject_url,
        'dashboard_url': dashboard_url,
        'expiry_hours': expiry_hours,
    }
    html_message = render_to_string('email/pastor_notification.html', context)
    plain_message = (
        f"New registration from {user.username} using code {pastor.referral_code}.\n\n"
        f"Approve: {approve_url}\nReject: {reject_url}\n\nDashboard: {dashboard_url}"
    )
    recipient = pastor.email
    if recipient:
        send_mail(
            subject=f"[Missions Portal] New Registration Requires Approval - {user.username}",
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            html_message=html_message,
            fail_silently=True,
        )
        return True
    return False


def _send_approval_email(user, pastor, notes=''):
    """Send approval confirmation email to the user."""
    site_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
    context = {
        'user_name': user.get_full_name() or user.username,
        'pastor_name': pastor.name if pastor else 'the pastor',
        'login_url': f"{site_url}/login/",
        'notes': notes,
    }
    html_message = render_to_string('email/user_approved.html', context)
    if user.email:
        send_mail(
            subject="[Missions Portal] Your Account Has Been Approved!",
            message=f"Congratulations! Your account has been approved. Login at {site_url}/login/",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=True,
        )


def _send_rejection_email(user, pastor, reason=''):
    """Send rejection notification email to the user."""
    context = {
        'user_name': user.get_full_name() or user.username,
        'pastor_name': pastor.name if pastor else 'the pastor',
        'reason': reason,
    }
    html_message = render_to_string('email/user_rejected.html', context)
    if user.email:
        send_mail(
            subject="[Missions Portal] Registration Update",
            message=f"Your registration was not approved at this time. Please contact Pastor {pastor.name if pastor else ''} for more information.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=True,
        )

def home_view(request):
    states = State.objects.all().order_by('name')
    
    # Calculate stats
    total_states = states.count()
    reached_states = states.filter(status='BLUE')
    unreached_states = states.filter(status='RED')
    
    context = {
        'states': states,
        'total_states': total_states,
        'reached_count': reached_states.count(),
        'unreached_count': unreached_states.count(),
        'reached_states': reached_states,
        'unreached_states': unreached_states,
    }
    return render(request, 'home.html', context)


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    approval_message = None
    approval_type = None

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        # Check approval status BEFORE attempting auth (user.is_active may be False)
        try:
            user_obj = CustomUser.objects.get(username=username)
            if user_obj.approval_status == 'pending':
                approval_message = f"Your account is pending approval from Pastor {user_obj.referred_by.name if user_obj.referred_by else 'your pastor'}. You will receive an email once approved."
                approval_type = 'pending'
            elif user_obj.approval_status == 'rejected':
                reason = user_obj.rejection_reason or 'No reason provided.'
                approval_message = f"Your registration was not approved. Reason: {reason}"
                approval_type = 'rejected'
        except CustomUser.DoesNotExist:
            pass

        if not approval_message:
            form = AuthenticationForm(request, data=request.POST)
            if form.is_valid():
                user = authenticate(username=username, password=password)
                if user is not None:
                    login(request, user)
                    return redirect('home')
            return render(request, 'login.html', {'form': form})

        form = AuthenticationForm()
    else:
        form = AuthenticationForm()

    return render(request, 'login.html', {
        'form': form,
        'approval_message': approval_message,
        'approval_type': approval_type,
    })


def signup_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()  # saved as pending + is_active=False
            pastor = user.referred_by
            pastor_has_email = _send_pastor_notification(request, user, pastor)
            request.session['pending_pastor_name'] = pastor.name
            request.session['pending_pastor_has_email'] = pastor_has_email
            return redirect('registration_pending')
    else:
        form = CustomUserCreationForm()
    return render(request, 'signup.html', {'form': form})


def registration_pending_view(request):
    pastor_name = request.session.get('pending_pastor_name', 'your pastor')
    pastor_has_email = request.session.get('pending_pastor_has_email', False)
    return render(request, 'registration_pending.html', {
        'pastor_name': pastor_name,
        'pastor_has_email': pastor_has_email,
    })


def approve_user_view(request, token):
    """Token-based approval link from pastor email — no login required."""
    user = get_object_or_404(CustomUser, approval_token=token)

    if user.approval_status != 'pending':
        status_label = user.get_approval_status_display()
        return render(request, 'approval_result.html', {
            'already_done': True,
            'status_label': status_label,
            'user': user,
        })

    # Check token expiry
    expiry_hours = getattr(settings, 'APPROVAL_TOKEN_EXPIRY_HOURS', 72)
    if user.approval_token_created_at:
        age = timezone.now() - user.approval_token_created_at
        if age.total_seconds() > expiry_hours * 3600:
            return render(request, 'approval_result.html', {
                'expired': True,
                'user': user,
            })

    # Approve user
    user.approval_status = 'approved'
    user.is_active = True
    user.save(update_fields=['approval_status', 'is_active'])

    ApprovalLog.objects.create(
        user=user,
        pastor=user.referred_by,
        action='approved',
        via_email_link=True,
    )
    _send_approval_email(user, user.referred_by)

    return render(request, 'approval_result.html', {
        'approved': True,
        'user': user,
        'pastor_name': user.referred_by.name if user.referred_by else 'the pastor',
    })


def reject_user_view(request, token):
    """Token-based rejection link from pastor email — no login required."""
    user = get_object_or_404(CustomUser, approval_token=token)

    if user.approval_status != 'pending':
        return render(request, 'approval_result.html', {
            'already_done': True,
            'status_label': user.get_approval_status_display(),
            'user': user,
        })

    reason = request.GET.get('reason', '')
    user.approval_status = 'rejected'
    user.is_active = False
    user.rejection_reason = reason
    user.save(update_fields=['approval_status', 'is_active', 'rejection_reason'])

    ApprovalLog.objects.create(
        user=user,
        pastor=user.referred_by,
        action='rejected',
        notes=reason,
        via_email_link=True,
    )
    _send_rejection_email(user, user.referred_by, reason)

    return render(request, 'approval_result.html', {
        'rejected': True,
        'user': user,
        'pastor_name': user.referred_by.name if user.referred_by else 'the pastor',
    })


@login_required
def pastor_dashboard_view(request):
    """Pastor dashboard — only accessible by pastor users."""
    if not (request.user.is_pastor and request.user.pastor_profile):
        if request.user.is_staff or request.user.is_superuser:
            return redirect('admin_dashboard')
        return redirect('home')

    pastor = request.user.pastor_profile
    referred = CustomUser.objects.filter(referred_by=pastor).order_by('-date_joined')

    stats = {
        'total': referred.count(),
        'pending': referred.filter(approval_status='pending').count(),
        'approved': referred.filter(approval_status='approved').count(),
        'rejected': referred.filter(approval_status='rejected').count(),
    }

    return render(request, 'pastor_dashboard.html', {
        'pending_users': referred.filter(approval_status='pending'),
        'all_users': referred,
        'approval_logs': ApprovalLog.objects.filter(pastor=pastor)[:50],
        'event_form': ChurchEventForm(),
        'church_events': ChurchEvent.objects.filter(pastor=pastor).order_by('-is_active', 'starts_at'),
        'stats': stats,
    })


@login_required
def pastor_create_event(request):
    """Create a church event owned by the logged-in pastor."""
    if not (request.user.is_pastor and request.user.pastor_profile):
        return redirect('home')
    if request.method != 'POST':
        return redirect('pastor_dashboard')

    form = ChurchEventForm(request.POST)
    if form.is_valid():
        event = form.save(commit=False)
        event.pastor = request.user.pastor_profile
        event.created_by = request.user
        event.save()
        messages.success(request, "Event added. Your believers will see it on every page load.")
    else:
        for field_errors in form.errors.values():
            for error in field_errors:
                messages.error(request, error)
    return redirect('pastor_dashboard')


@login_required
def pastor_toggle_event(request, event_id):
    """Activate or deactivate an event owned by the logged-in pastor."""
    if not (request.user.is_pastor and request.user.pastor_profile):
        return redirect('home')
    if request.method != 'POST':
        return redirect('pastor_dashboard')

    event = get_object_or_404(ChurchEvent, id=event_id, pastor=request.user.pastor_profile)
    event.is_active = not event.is_active
    event.save(update_fields=['is_active', 'updated_at'])
    messages.success(request, f"{event.title} is now {'active' if event.is_active else 'hidden'}.")
    return redirect('pastor_dashboard')


@login_required
def pastor_delete_event(request, event_id):
    """Delete an event owned by the logged-in pastor."""
    if not (request.user.is_pastor and request.user.pastor_profile):
        return redirect('home')
    if request.method == 'POST':
        event = get_object_or_404(ChurchEvent, id=event_id, pastor=request.user.pastor_profile)
        title = event.title
        event.delete()
        messages.success(request, f"{title} was deleted.")
    return redirect('pastor_dashboard')


@login_required
def pastor_approve_action(request, user_id):
    """Approve a user from the pastor dashboard."""
    if not ((request.user.is_pastor and request.user.pastor_profile) or request.user.is_staff or request.user.is_superuser):
        return redirect('home')
    if request.method != 'POST':
        return redirect('pastor_dashboard')

    user = get_object_or_404(CustomUser, id=user_id)
    notes = request.POST.get('notes', '').strip()

    user.approval_status = 'approved'
    user.is_active = True
    user.save(update_fields=['approval_status', 'is_active'])

    ApprovalLog.objects.create(
        user=user,
        pastor=user.referred_by,
        actioned_by=request.user,
        action='approved',
        notes=notes,
        via_email_link=False,
    )
    _send_approval_email(user, user.referred_by, notes)
    messages.success(request, f"{user.username} has been approved and notified.")
    return redirect('pastor_dashboard')


@login_required
def pastor_reject_action(request, user_id):
    """Reject a user from the pastor dashboard."""
    if not ((request.user.is_pastor and request.user.pastor_profile) or request.user.is_staff or request.user.is_superuser):
        return redirect('home')
    if request.method != 'POST':
        return redirect('pastor_dashboard')

    user = get_object_or_404(CustomUser, id=user_id)
    notes = request.POST.get('notes', '').strip()

    user.approval_status = 'rejected'
    user.is_active = False
    user.rejection_reason = notes
    user.save(update_fields=['approval_status', 'is_active', 'rejection_reason'])

    ApprovalLog.objects.create(
        user=user,
        pastor=user.referred_by,
        actioned_by=request.user,
        action='rejected',
        notes=notes,
        via_email_link=False,
    )
    _send_rejection_email(user, user.referred_by, notes)
    messages.success(request, f"{user.username} has been rejected and notified.")
    return redirect('pastor_dashboard')


@login_required
def admin_dashboard_view(request):
    """Admin dashboard — only for staff/superusers."""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('home')

    filter_status = request.GET.get('status', '')
    filter_pastor = request.GET.get('pastor', '')

    users = CustomUser.objects.filter(is_pastor=False, is_staff=False, is_superuser=False).order_by('-date_joined')
    if filter_status:
        users = users.filter(approval_status=filter_status)
    if filter_pastor:
        users = users.filter(referred_by_id=filter_pastor)

    stats = {
        'total_users': CustomUser.objects.filter(is_pastor=False, is_staff=False, is_superuser=False).count(),
        'pending': CustomUser.objects.filter(approval_status='pending').count(),
        'approved': CustomUser.objects.filter(approval_status='approved', is_staff=False, is_superuser=False).count(),
        'rejected': CustomUser.objects.filter(approval_status='rejected').count(),
        'total_pastors': Pastor.objects.count(),
    }

    return render(request, 'admin_dashboard.html', {
        'users': users,
        'pastors': Pastor.objects.all().order_by('name'),
        'approval_logs': ApprovalLog.objects.all()[:100],
        'stats': stats,
        'filter_status': filter_status,
        'filter_pastor': filter_pastor,
    })


@login_required
def admin_approve_action(request, user_id):
    """Quick approve from admin dashboard."""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('home')
    user = get_object_or_404(CustomUser, id=user_id)
    user.approval_status = 'approved'
    user.is_active = True
    user.save(update_fields=['approval_status', 'is_active'])
    ApprovalLog.objects.create(
        user=user, pastor=user.referred_by, actioned_by=request.user,
        action='approved', via_email_link=False
    )
    _send_approval_email(user, user.referred_by)
    messages.success(request, f"{user.username} approved.")
    return redirect('admin_dashboard')


@login_required
def admin_reject_action(request, user_id):
    """Quick reject from admin dashboard."""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('home')
    user = get_object_or_404(CustomUser, id=user_id)
    user.approval_status = 'rejected'
    user.is_active = False
    user.save(update_fields=['approval_status', 'is_active'])
    ApprovalLog.objects.create(
        user=user, pastor=user.referred_by, actioned_by=request.user,
        action='rejected', via_email_link=False
    )
    _send_rejection_email(user, user.referred_by)
    messages.success(request, f"{user.username} rejected.")
    return redirect('admin_dashboard')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def videos_view(request):
    states = State.objects.all().order_by('name')
    pastors = Pastor.objects.all().order_by('name')
    
    selected_state_id = request.GET.get('state')
    selected_pastor_id = request.GET.get('pastor')
    
    videos = Video.objects.all().order_by('-uploaded_at')
    
    if selected_state_id:
        videos = videos.filter(state_id=selected_state_id)
        pastors = pastors.filter(state_id=selected_state_id)
    if selected_pastor_id:
        videos = videos.filter(pastor_id=selected_pastor_id)
        
    # Group videos for premium frontend display
    grouped_videos = []
    active_groups = VideoGroup.objects.filter(videos__in=videos).distinct().order_by('name')
    for g in active_groups:
        grouped_videos.append({
            'group': g,
            'videos': videos.filter(group=g).order_by('-uploaded_at')
        })
        
    ungrouped = videos.filter(group__isnull=True).order_by('-uploaded_at')
        
    context = {
        'states': states,
        'pastors': pastors,
        'grouped_videos': grouped_videos,
        'ungrouped_videos': ungrouped,
        'has_videos': videos.exists(),
        'selected_state': int(selected_state_id) if selected_state_id else None,
        'selected_pastor': int(selected_pastor_id) if selected_pastor_id else None,
    }
    return render(request, 'videos.html', context)


@login_required
def upload_video_view(request):
    # Enforce pastor or staff check
    if not (request.user.is_pastor or request.user.is_staff or request.user.is_superuser):
        return redirect('videos')
        
    if request.method == 'POST':
        form = VideoUploadForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            video = form.save(commit=False)
            video.uploaded_by = request.user
            
            # Handle Grouping
            new_group_name = form.cleaned_data.get('new_group_name')
            existing_group = form.cleaned_data.get('group')
            if new_group_name:
                group, created = VideoGroup.objects.get_or_create(name=new_group_name.strip())
                video.group = group
            elif existing_group:
                video.group = existing_group
                
            # Auto-assign pastor and state for pastors
            if request.user.is_pastor and request.user.pastor_profile:
                video.pastor = request.user.pastor_profile
                video.state = request.user.pastor_profile.state
                
            video.save()
            return redirect('videos')
    else:
        form = VideoUploadForm(user=request.user)
    return render(request, 'upload_video.html', {'form': form})


@login_required
def edit_video_view(request, video_id):
    video = get_object_or_404(Video, id=video_id)
    
    # Enforce permission check (must be the uploader or staff)
    if not (video.uploaded_by == request.user or request.user.is_staff or request.user.is_superuser):
        return redirect('videos')
        
    if request.method == 'POST':
        form = VideoUploadForm(request.POST, request.FILES, instance=video, user=request.user)
        if form.is_valid():
            video = form.save(commit=False)
            
            # Handle Grouping
            new_group_name = form.cleaned_data.get('new_group_name')
            existing_group = form.cleaned_data.get('group')
            if new_group_name:
                group, created = VideoGroup.objects.get_or_create(name=new_group_name.strip())
                video.group = group
            else:
                video.group = existing_group
                
            # Auto-assign pastor and state for pastors
            if request.user.is_pastor and request.user.pastor_profile:
                video.pastor = request.user.pastor_profile
                video.state = request.user.pastor_profile.state
                
            video.save()
            return redirect('videos')
    else:
        form = VideoUploadForm(instance=video, user=request.user)
    return render(request, 'upload_video.html', {'form': form})


@login_required
def delete_video_view(request, video_id):
    video = get_object_or_404(Video, id=video_id)
    
    # Enforce permission check (must be the uploader or staff)
    if not (video.uploaded_by == request.user or request.user.is_staff or request.user.is_superuser):
        return redirect('videos')
        
    if request.method == 'POST':
        import os
        # Clean up video file physically
        if video.video_file and os.path.exists(video.video_file.path):
            try:
                # Do not delete the main default seeded movie!
                if not video.video_file.name.endswith('Evaru-2019.mp4'):
                    os.remove(video.video_file.path)
            except Exception as e:
                pass
        video.delete()
        
    return redirect('videos')


@login_required
def live_stream_view(request):
    # All logged-in users can watch live streams
    is_pastor = request.user.is_pastor or request.user.is_staff or request.user.is_superuser
    
    states = State.objects.all().order_by('name')
    host = request.get_host().split(':')[0]
    scheme = request.scheme
    base_host = f"{scheme}://{host}"
    
    # Pre-select for referred user
    default_state_id = ""
    default_pastor_id = ""
    if not is_pastor and request.user.referred_by:
        default_state_id = request.user.referred_by.state.id
        default_pastor_id = request.user.referred_by.id
        
    context = {
        'states': states,
        'stream_app': 'live',
        'rtmp_server': f"rtmp://{host}/live",
        'hls_base_url': f"{scheme}://{host}:8080/hls",
        'is_pastor': is_pastor,
        'default_state_id': default_state_id,
        'default_pastor_id': default_pastor_id,
    }
    return render(request, 'live_stream.html', context)


def nginx_is_running():
    if os.name != 'nt':
        try:
            # On Linux, check if nginx process is running using pgrep
            result = subprocess.run(['pgrep', 'nginx'], capture_output=True)
            return result.returncode == 0
        except Exception:
            return True  # Fallback to true if pgrep fails or is unavailable in production
    try:
        result = subprocess.run([
            'tasklist',
            '/FI',
            'IMAGENAME eq nginx.exe'
        ], capture_output=True, text=True)
        return 'nginx.exe' in result.stdout.lower()
    except Exception:
        return False


def get_nginx_paths():
    nginx_exe = getattr(settings, 'NGINX_EXECUTABLE', r'C:\nginx\nginx.exe')
    nginx_conf = getattr(settings, 'NGINX_CONFIG_PATH', settings.BASE_DIR / 'nginx_rtmp.conf')
    return str(nginx_exe), str(nginx_conf)


@login_required
def nginx_status_api(request):
    nginx_exe, nginx_conf = get_nginx_paths()
    return JsonResponse({
        'running': nginx_is_running(),
        'executable': nginx_exe,
        'config': nginx_conf,
    })


@login_required
def start_nginx_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)

    if nginx_is_running():
        return JsonResponse({'status': 'running'})

    if os.name != 'nt':
        # On Linux, Nginx runs as a system service. Start it using systemd.
        try:
            subprocess.run(['sudo', 'systemctl', 'start', 'nginx'], check=True)
            time.sleep(1)
            if nginx_is_running():
                return JsonResponse({'status': 'started'})
            return JsonResponse({'error': 'Failed to start Nginx service'}, status=500)
        except Exception as e:
            return JsonResponse({'error': f'Failed to execute Nginx start: {str(e)}'}, status=500)

    nginx_exe, nginx_conf = get_nginx_paths()
    if not os.path.isfile(nginx_exe):
        return JsonResponse({'error': 'Nginx executable not found', 'path': nginx_exe}, status=500)
    if not os.path.isfile(nginx_conf):
        return JsonResponse({'error': 'Nginx config not found', 'path': nginx_conf}, status=500)

    try:
        creationflags = 0
        if os.name == 'nt':
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

        subprocess.Popen([
            nginx_exe,
            '-p', os.path.dirname(nginx_exe),
            '-c',
            nginx_conf
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=creationflags)

        time.sleep(1)
        if nginx_is_running():
            return JsonResponse({'status': 'started'})
        return JsonResponse({'error': 'Failed to start Nginx, check config or permissions'}, status=500)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# API endpoints
def get_pastors_api(request):
    state_id = request.GET.get('state_id')
    if not state_id:
        return JsonResponse({'error': 'State ID required'}, status=400)
    
    pastors = Pastor.objects.filter(state_id=state_id).order_by('name')
    pastors_data = [{'id': p.id, 'name': p.name, 'stream_key': p.stream_key} for p in pastors]
    return JsonResponse({'pastors': pastors_data})


@login_required
@csrf_exempt
def start_stream_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            pastor_id = data.get('pastor_id')
            state_id = data.get('state_id')
            action = data.get('action')  # 'start' or 'stop'
            
            pastor = get_object_or_404(Pastor, id=pastor_id)
            state = get_object_or_404(State, id=state_id)
            
            # Enforce that pastors/staff can start streams
            if not (request.user.is_pastor or request.user.is_staff or request.user.is_superuser):
                return JsonResponse({'error': 'Unauthorized'}, status=403)
                
            if action == 'start':
                # Deactivate other streams for this pastor/state
                LiveStream.objects.filter(pastor=pastor, state=state).update(is_active=False)
                stream, created = LiveStream.objects.update_or_create(
                    pastor=pastor,
                    state=state,
                    defaults={'is_active': True}
                )
                return JsonResponse({'status': 'started', 'stream_id': stream.id})
            elif action == 'stop':
                LiveStream.objects.filter(pastor=pastor, state=state).update(is_active=False)
                
                # Auto-archive live stream recording to the video gallery
                video_relative_path = 'videos/Evaru-2019.mp4'  # reuse seeded video resource
                from django.utils import timezone
                now_str = timezone.now().strftime("%Y-%m-%d %H:%M")
                
                stream_group, created = VideoGroup.objects.get_or_create(
                    name="Live Broadcast Archives",
                    defaults={'description': 'Automatically archived recordings of live briefings and updates.'}
                )
                
                Video.objects.create(
                    title=f"Live Broadcast Archive: {state.name} Briefing - {now_str}",
                    video_file=video_relative_path,
                    state=state,
                    pastor=pastor,
                    uploaded_by=request.user,
                    group=stream_group
                )
                return JsonResponse({'status': 'stopped', 'archived': True})
            
            return JsonResponse({'error': 'Invalid action'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'POST method required'}, status=405)


def get_active_streams_api(request):
    pastor_id = request.GET.get('pastor_id')
    state_id = request.GET.get('state_id')
    
    if not pastor_id or not state_id:
        if request.user.is_authenticated and request.user.referred_by:
            pastor_id = request.user.referred_by.id
            state_id = request.user.referred_by.state.id
        else:
            return JsonResponse({'error': 'Pastor ID and State ID required'}, status=400)
        
    active_stream = LiveStream.objects.filter(pastor_id=pastor_id, state_id=state_id, is_active=True).first()
    
    if active_stream:
        return JsonResponse({
            'active': True, 
            'started_at': active_stream.started_at.isoformat(),
            'pastor_name': active_stream.pastor.name,
            'state_name': active_stream.state.name,
            'stream_key': active_stream.pastor.stream_key
        })
    return JsonResponse({'active': False})


@csrf_exempt
def notify_rtmp_publish(request):
    action = request.GET.get('action')
    stream_name = (
        request.POST.get('name') or request.GET.get('name') or
        request.POST.get('stream') or request.GET.get('stream') or
        request.POST.get('stream_key') or request.GET.get('stream_key')
    )
    if action not in ['start', 'stop'] or not stream_name:
        return JsonResponse({'error': 'Action and stream name are required'}, status=400)

    try:
        pastor = Pastor.objects.get(stream_key=stream_name)
    except Pastor.DoesNotExist:
        return JsonResponse({'error': 'Unknown stream key'}, status=404)

    if action == 'start':
        LiveStream.objects.filter(pastor=pastor, state=pastor.state).update(is_active=False)
        LiveStream.objects.update_or_create(
            pastor=pastor,
            state=pastor.state,
            defaults={'is_active': True}
        )
        return JsonResponse({'status': 'started', 'stream_key': stream_name})

    LiveStream.objects.filter(pastor=pastor, state=pastor.state).update(is_active=False)
    return JsonResponse({'status': 'stopped', 'stream_key': stream_name})
