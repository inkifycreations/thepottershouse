from django.contrib import admin
from django.contrib import messages
from django.contrib.auth.admin import UserAdmin
from .models import State, Pastor, CustomUser, Video, LiveStream, ChurchEvent

class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Mission Fields', {'fields': ('phone_number', 'address', 'age', 'referred_by', 'is_pastor', 'pastor_profile', 'approval_status')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Custom Mission Fields', {'fields': ('phone_number', 'address', 'age', 'referred_by', 'is_pastor', 'pastor_profile', 'email')}),
    )
    list_display = ('username', 'email', 'phone_number', 'approval_status', 'is_pastor', 'pastor_profile', 'referred_by', 'is_staff', 'is_superuser')
    list_editable = ('approval_status', 'is_pastor', 'pastor_profile', 'referred_by', 'is_staff')
    list_filter = ('approval_status', 'is_pastor', 'is_staff', 'is_superuser', 'referred_by', 'pastor_profile')
    actions = ['make_believer', 'make_pastor', 'make_admin']

    @admin.action(description='Make selected users believers')
    def make_believer(self, request, queryset):
        updated = queryset.update(
            is_pastor=False,
            pastor_profile=None,
            is_staff=False,
            is_superuser=False,
            is_active=True,
            approval_status=CustomUser.APPROVAL_APPROVED,
        )
        self.message_user(request, f"{updated} user(s) changed to believer.", messages.SUCCESS)

    @admin.action(description='Make selected users pastors')
    def make_pastor(self, request, queryset):
        ready_users = queryset.filter(pastor_profile__isnull=False)
        missing_profile = queryset.filter(pastor_profile__isnull=True).count()
        updated = ready_users.update(
            is_pastor=True,
            is_staff=True,
            is_active=True,
            approval_status=CustomUser.APPROVAL_APPROVED,
        )
        if missing_profile:
            self.message_user(
                request,
                f"{missing_profile} user(s) were skipped. Select a Pastor profile for them first, then run this action again.",
                messages.WARNING,
            )
        self.message_user(request, f"{updated} user(s) changed to pastor.", messages.SUCCESS)

    @admin.action(description='Make selected users admins')
    def make_admin(self, request, queryset):
        updated = queryset.update(
            is_pastor=False,
            pastor_profile=None,
            is_staff=True,
            is_superuser=True,
            is_active=True,
            approval_status=CustomUser.APPROVAL_APPROVED,
        )
        self.message_user(request, f"{updated} user(s) changed to admin.", messages.SUCCESS)

@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'population', 'status')
    list_filter = ('status',)
    search_fields = ('name', 'code')

@admin.register(Pastor)
class PastorAdmin(admin.ModelAdmin):
    list_display = ('name', 'state', 'referral_code', 'stream_key')
    list_filter = ('state',)
    search_fields = ('name', 'referral_code', 'stream_key')

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'pastor', 'state', 'uploaded_at')
    list_filter = ('state', 'pastor')
    search_fields = ('title',)

@admin.register(LiveStream)
class LiveStreamAdmin(admin.ModelAdmin):
    list_display = ('pastor', 'state', 'is_active', 'started_at')
    list_filter = ('is_active', 'state', 'pastor')

@admin.register(ChurchEvent)
class ChurchEventAdmin(admin.ModelAdmin):
    list_display = ('title', 'pastor', 'event_type', 'starts_at', 'is_active')
    list_filter = ('is_active', 'event_type', 'pastor')
    search_fields = ('title', 'description', 'location', 'pastor__name')

admin.site.register(CustomUser, CustomUserAdmin)
