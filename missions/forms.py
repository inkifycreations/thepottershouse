from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import ChurchEvent, CustomUser, Pastor, State, Video, VideoGroup

class CustomUserCreationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password', 'required': 'required'}))
    password_confirm = forms.CharField(label="Confirm Password", widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password', 'required': 'required'}))
    referral_code = forms.CharField(required=True, label="Pastor Referral Code", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. CHRIS_WB', 'required': 'required'}))
    
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'phone_number', 'address', 'age']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username', 'required': 'required'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address', 'required': 'required'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number', 'required': 'required'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Full Address', 'required': 'required'}),
            'age': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Age', 'required': 'required'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ['username', 'email', 'phone_number', 'address', 'age', 'password', 'password_confirm', 'referral_code']:
            self.fields[field_name].required = True

    def clean_age(self):
        age = self.cleaned_data.get('age')
        if age is not None and age <= 0:
            raise forms.ValidationError("Please enter a valid age.")
        return age

    def clean_referral_code(self):
        code = self.cleaned_data.get('referral_code', '')
        return code.strip() if code else ''

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")
        referral_code = cleaned_data.get('referral_code', '').strip()

        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', "Passwords do not match. Please double-check.")

        # Validate referral code
        if not referral_code:
            self.add_error('referral_code', "A valid pastor referral code is required.")
            raise forms.ValidationError("Referral code is required to complete registration.")

        try:
            pastor = Pastor.objects.get(referral_code__iexact=referral_code)
            self.cleaned_pastor = pastor
        except Pastor.DoesNotExist:
            self.add_error('referral_code', "Invalid pastor referral code.")
            raise forms.ValidationError("Please enter a valid pastor referral code.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.is_pastor = False
        user.pastor_profile = None
        user.referred_by = self.cleaned_pastor

        # Set pending approval — user cannot log in until pastor approves
        from django.utils import timezone
        import uuid
        user.approval_status = 'pending'
        user.is_active = False  # Block login at the auth level too
        user.approval_token = uuid.uuid4()
        user.approval_token_created_at = timezone.now()

        if commit:
            user.save()
        return user



class VideoUploadForm(forms.ModelForm):
    group = forms.ModelChoiceField(
        queryset=VideoGroup.objects.all().order_by('name'),
        required=False,
        empty_label="Select Existing Group (Optional)",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    new_group_name = forms.CharField(
        required=False,
        max_length=255,
        label="Or Create New Group",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Revival Meetings 2026'})
    )

    class Meta:
        model = Video
        fields = ['title', 'state', 'pastor', 'video_file']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Video Title'}),
            'state': forms.Select(attrs={'class': 'form-select', 'id': 'state-select'}),
            'pastor': forms.Select(attrs={'class': 'form-select', 'id': 'pastor-select'}),
            'video_file': forms.FileInput(attrs={'class': 'form-control', 'accept': 'video/*'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # If the user is a pastor, restrict options or hide
        if self.user and getattr(self.user, 'is_pastor', False) and self.user.pastor_profile:
            self.fields['pastor'].initial = self.user.pastor_profile.id
            self.fields['state'].initial = self.user.pastor_profile.state.id
            self.fields['pastor'].required = False
            self.fields['state'].required = False

    def clean(self):
        cleaned_data = super().clean()
        
        if self.user and getattr(self.user, 'is_pastor', False) and self.user.pastor_profile:
            cleaned_data['pastor'] = self.user.pastor_profile
            cleaned_data['state'] = self.user.pastor_profile.state
        else:
            state = cleaned_data.get('state')
            pastor = cleaned_data.get('pastor')
            if state and pastor and pastor.state != state:
                raise forms.ValidationError("The selected pastor does not serve in the selected state.")
                
        return cleaned_data


class ChurchEventForm(forms.ModelForm):
    class Meta:
        model = ChurchEvent
        fields = ['title', 'event_type', 'description', 'location', 'starts_at', 'ends_at', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Event title'}),
            'event_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Prayer focus, meeting details, or instructions'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Church, home fellowship, online, etc.'}),
            'starts_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'ends_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'event-checkbox'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        starts_at = cleaned_data.get('starts_at')
        ends_at = cleaned_data.get('ends_at')
        if starts_at and ends_at and ends_at < starts_at:
            self.add_error('ends_at', "End time cannot be before the start time.")
        return cleaned_data
