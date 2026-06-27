from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from functools import wraps

def pastor_required(view_func):
    """
    Decorator that checks if the user is a pastor, staff, or superuser.
    Redirects to 'videos' page if not authorized.
    """
    @wraps(view_func)
    @login_required
    def wrapped_view(request, *args, **kwargs):
        if not (request.user.is_pastor or request.user.is_staff or request.user.is_superuser):
            return redirect('videos')
        return view_func(request, *args, **kwargs)
    return wrapped_view
