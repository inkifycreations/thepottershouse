from django.db.models import Q
from django.utils import timezone

from .models import ChurchEvent


def church_event_popup(request):
    user = getattr(request, 'user', None)
    events = ChurchEvent.objects.none()
    upcoming_filter = Q(ends_at__isnull=True, starts_at__gte=timezone.now()) | Q(ends_at__gte=timezone.now())

    if user and user.is_authenticated and not getattr(user, 'is_pastor', False) and user.referred_by:
        events = ChurchEvent.objects.filter(
            pastor=user.referred_by,
            is_active=True,
        ).filter(upcoming_filter)
        events = events.select_related('pastor', 'pastor__state').order_by('starts_at')[:5]
    elif not (user and user.is_authenticated):
        events = ChurchEvent.objects.filter(
            is_active=True,
        ).filter(upcoming_filter)
        events = events.select_related('pastor', 'pastor__state').order_by('starts_at')[:5]

    return {
        'church_popup_events': events,
        'church_popup_is_visitor_view': not (user and user.is_authenticated),
    }
