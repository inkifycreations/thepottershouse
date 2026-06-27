from django.db import models
from django.core.validators import RegexValidator
from django.contrib.auth.models import AbstractUser
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid

username_validator = RegexValidator(
    regex=r'^[\w.@+\-\s]+$',
    message=_('Enter a valid username. This value may contain only letters, numbers, spaces and @/./+/-/_ characters.'),
    code='invalid',
)

class State(models.Model):
    STATUS_CHOICES = [
        ('RED', 'Not Reached'),
        ('BLUE', 'Reached (Work Needed)'),
    ]
    code = models.CharField(max_length=10, unique=True, help_text="State code matching SVG path ID (e.g. 'wb', 'up')")
    name = models.CharField(max_length=100)
    population = models.CharField(max_length=50, help_text="Population count/description (e.g. '91.3 Million')")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='RED')
    description = models.TextField(blank=True, default='')

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"


class Pastor(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField(blank=True, default='', help_text="Pastor's email address for approval notifications")
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='pastors')
    referral_code = models.CharField(max_length=50, unique=True, help_text="Referral code for new users")
    stream_key = models.CharField(max_length=100, unique=True, blank=True, null=True, help_text="RTMP/HLS stream key for OBS and viewer playback")

    def save(self, *args, **kwargs):
        if not self.stream_key:
            base_key = slugify(self.name) or 'pastor'
            candidate = base_key
            index = 1
            while Pastor.objects.filter(stream_key=candidate).exclude(pk=self.pk).exists():
                index += 1
                candidate = f"{base_key}-{index}"
            self.stream_key = candidate
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Pastor {self.name} ({self.state.name}) [{self.stream_key}]"


class CustomUser(AbstractUser):
    APPROVAL_PENDING = 'pending'
    APPROVAL_APPROVED = 'approved'
    APPROVAL_REJECTED = 'rejected'
    APPROVAL_STATUS_CHOICES = [
        (APPROVAL_PENDING, 'Pending Approval'),
        (APPROVAL_APPROVED, 'Approved'),
        (APPROVAL_REJECTED, 'Rejected'),
    ]

    username = models.CharField(
        _('username'),
        max_length=150,
        unique=True,
        validators=[username_validator],
        error_messages={
            'unique': _("A user with that username already exists."),
        },
    )
    phone_number = models.CharField(max_length=20, blank=True, default='')
    address = models.TextField(blank=True, default='')
    age = models.IntegerField(null=True, blank=True)
    referred_by = models.ForeignKey(Pastor, on_delete=models.SET_NULL, null=True, blank=True, related_name='referred_users')
    is_pastor = models.BooleanField(default=False, help_text="Designates whether the user is a pastor.")
    pastor_profile = models.OneToOneField(Pastor, on_delete=models.SET_NULL, null=True, blank=True, related_name='user_account')

    # Approval workflow fields
    approval_status = models.CharField(
        max_length=20, choices=APPROVAL_STATUS_CHOICES,
        default=APPROVAL_APPROVED,
        help_text="Account approval status"
    )
    approval_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    approval_token_created_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default='', help_text="Reason provided by pastor on rejection")

    def __str__(self):
        return self.username

    @property
    def is_pending(self):
        return self.approval_status == self.APPROVAL_PENDING

    @property
    def is_approved(self):
        return self.approval_status == self.APPROVAL_APPROVED

    @property
    def is_rejected(self):
        return self.approval_status == self.APPROVAL_REJECTED


class ApprovalLog(models.Model):
    ACTION_APPROVED = 'approved'
    ACTION_REJECTED = 'rejected'
    ACTION_CHOICES = [
        (ACTION_APPROVED, 'Approved'),
        (ACTION_REJECTED, 'Rejected'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='approval_logs')
    pastor = models.ForeignKey(Pastor, on_delete=models.SET_NULL, null=True, blank=True, related_name='approval_logs')
    actioned_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='approval_actions_taken',
        help_text="Which user/pastor performed the action (null = email token link)"
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    notes = models.TextField(blank=True, default='')
    timestamp = models.DateTimeField(auto_now_add=True)
    via_email_link = models.BooleanField(default=False, help_text="True if actioned via email token link")

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        pastor_name = self.pastor.name if self.pastor else 'Unknown'
        return f"{self.action.title()}: {self.user.username} by Pastor {pastor_name} at {self.timestamp:%Y-%m-%d %H:%M}"


class VideoGroup(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Video(models.Model):
    title = models.CharField(max_length=255)
    video_file = models.FileField(upload_to='videos/')
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='videos')
    pastor = models.ForeignKey(Pastor, on_delete=models.CASCADE, related_name='videos')
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_videos')
    group = models.ForeignKey(VideoGroup, on_delete=models.SET_NULL, null=True, blank=True, related_name='videos')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - Pastor {self.pastor.name} ({self.state.name})"


class LiveStream(models.Model):
    pastor = models.ForeignKey(Pastor, on_delete=models.CASCADE, related_name='streams')
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='streams')
    is_active = models.BooleanField(default=False)
    started_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"Live Stream: Pastor {self.pastor.name} ({self.state.name}) - {status}"


class ChurchEvent(models.Model):
    EVENT_SPECIAL_PRAYER = 'special_prayer'
    EVENT_MEETING = 'meeting'
    EVENT_SERVICE = 'service'
    EVENT_OTHER = 'other'
    EVENT_TYPE_CHOICES = [
        (EVENT_SPECIAL_PRAYER, 'Special Prayer'),
        (EVENT_MEETING, 'Meeting'),
        (EVENT_SERVICE, 'Service'),
        (EVENT_OTHER, 'Other'),
    ]

    pastor = models.ForeignKey(Pastor, on_delete=models.CASCADE, related_name='church_events')
    title = models.CharField(max_length=180)
    event_type = models.CharField(max_length=30, choices=EVENT_TYPE_CHOICES, default=EVENT_MEETING)
    description = models.TextField(blank=True, default='')
    location = models.CharField(max_length=180, blank=True, default='')
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_church_events')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['starts_at']

    def __str__(self):
        return f"{self.title} - Pastor {self.pastor.name}"

    @property
    def has_ended(self):
        end_time = self.ends_at or self.starts_at
        return end_time < timezone.now()
