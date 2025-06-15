from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
# UserProfile import removed as the model doesn't exist
import os

class Command(BaseCommand):
    help = 'Set up T3 Chat Clone with initial configuration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-superuser',
            action='store_true',
            help='Create a superuser account',
        )
        parser.add_argument(
            '--username',
            type=str,
            default='admin',
            help='Username for the superuser (default: admin)',
        )
        parser.add_argument(
            '--email',
            type=str,
            default='admin@t3chat.local',
            help='Email for the superuser (default: admin@t3chat.local)',
        )
        parser.add_argument(
            '--password',
            type=str,
            default='t3chat123',
            help='Password for the superuser (default: t3chat123)',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Setting up T3 Chat Clone...')
        )

        # Create superuser if requested
        if options['create_superuser']:
            self.create_superuser(
                options['username'],
                options['email'],
                options['password']
            )

        # Run migrations
        self.stdout.write('📦 Running database migrations...')
        from django.core.management import call_command
        call_command('migrate', verbosity=0)

        # Collect static files
        self.stdout.write('📁 Collecting static files...')
        call_command('collectstatic', verbosity=0, interactive=False)

        # Create demo user profiles
        self.create_demo_profiles()

        # Display setup information
        self.display_setup_info()

        self.stdout.write(
            self.style.SUCCESS('✅ T3 Chat Clone setup completed successfully!')
        )

    def create_superuser(self, username, email, password):
        """Create a superuser account"""
        try:
            if User.objects.filter(username=username).exists():
                self.stdout.write(
                    self.style.WARNING(f'⚠️  Superuser "{username}" already exists')
                )
                return

            with transaction.atomic():
                user = User.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password
                )
                self.stdout.write(
                    self.style.SUCCESS(f'👤 Created superuser: {username}')
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error creating superuser: {e}')
            )

    def create_demo_profiles(self):
        """Create demo user profiles for testing"""
        demo_users = [
            {'username': 'demo', 'email': 'demo@t3chat.local', 'password': 'demo123'},
            {'username': 'judge', 'email': 'judge@t3chat.local', 'password': 'judge123'},
        ]

        for user_data in demo_users:
            try:
                if User.objects.filter(username=user_data['username']).exists():
                    continue

                with transaction.atomic():
                    user = User.objects.create_user(
                        username=user_data['username'],
                        email=user_data['email'],
                        password=user_data['password']
                    )
                    
                    # User created successfully
                    self.stdout.write(
                        self.style.SUCCESS(f'👤 Created demo user: {user_data["username"]}')
                    )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Error creating demo user {user_data["username"]}: {e}')
                )

    def display_setup_info(self):
        """Display setup information and next steps"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('🎉 T3 Chat Clone Setup Complete!'))
        self.stdout.write('='*60)
        
        self.stdout.write('\n📋 Next Steps:')
        self.stdout.write('1. Start the development server:')
        self.stdout.write('   python manage.py runserver')
        
        self.stdout.write('\n2. Start Celery worker (in another terminal):')
        self.stdout.write('   celery -A config worker -l info')
        
        self.stdout.write('\n3. Start Redis server (if not running):')
        self.stdout.write('   redis-server')
        
        self.stdout.write('\n🌐 Access Points:')
        self.stdout.write('• Main Chat: http://localhost:8000/')
        self.stdout.write('• Admin Panel: http://localhost:8000/admin/')
        self.stdout.write('• API Docs: http://localhost:8000/api/docs/')
        
        self.stdout.write('\n👤 Demo Accounts:')
        self.stdout.write('• Username: demo, Password: demo123')
        self.stdout.write('• Username: judge, Password: judge123')
        
        self.stdout.write('\n🔧 Configuration:')
        self.stdout.write('• Set your OpenRouter API key in user settings')
        self.stdout.write('• Set your Tavily API key for web search')
        self.stdout.write('• Configure Redis URL in settings if needed')
        
        self.stdout.write('\n📚 Features Available:')
        self.stdout.write('✅ Multiple AI Models via OpenRouter')
        self.stdout.write('✅ Real-time WebSocket Chat')
        self.stdout.write('✅ File Upload Support')
        self.stdout.write('✅ Web Search Integration')
        self.stdout.write('✅ Chat History & Persistence')
        self.stdout.write('✅ User Authentication')
        self.stdout.write('✅ Admin Interface')
        self.stdout.write('✅ API Documentation')
        
        self.stdout.write('\n' + '='*60) 