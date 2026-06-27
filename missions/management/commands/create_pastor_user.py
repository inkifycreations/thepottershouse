from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from missions.models import Pastor
import getpass

CustomUser = get_user_model()

class Command(BaseCommand):
    help = 'Create a pastor user account with access to upload and live streaming'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username for the pastor account')
        parser.add_argument('email', type=str, help='Email address for the pastor account')
        parser.add_argument('pastor_id', type=int, help='Pastor ID from the Pastor model')
        parser.add_argument('--password', type=str, help='Password for the account (will prompt if not provided)')

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        pastor_id = options['pastor_id']
        password = options.get('password')

        # Check if pastor exists
        try:
            pastor = Pastor.objects.get(id=pastor_id)
        except Pastor.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Pastor with ID {pastor_id} does not exist.'))
            return

        # Check if user already exists
        if CustomUser.objects.filter(username=username).exists():
            self.stdout.write(self.style.ERROR(f'User with username "{username}" already exists.'))
            return

        # Get password if not provided
        if not password:
            password = getpass.getpass('Enter password for the pastor account: ')
            password_confirm = getpass.getpass('Confirm password: ')
            if password != password_confirm:
                self.stdout.write(self.style.ERROR('Passwords do not match.'))
                return

        # Create the pastor user
        try:
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=password,
                is_pastor=True,
                pastor_profile=pastor,
                referred_by=None
            )
            self.stdout.write(self.style.SUCCESS(
                f'Pastor user "{username}" created successfully!\n'
                f'- Username: {username}\n'
                f'- Email: {email}\n'
                f'- Pastor: {pastor.name} ({pastor.state.name})\n'
                f'- Can upload videos and manage live streams'
            ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating pastor user: {str(e)}'))
