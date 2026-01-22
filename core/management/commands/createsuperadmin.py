"""
Management command to create a superuser with phone authentication.
"""
from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from core.models import User


class Command(BaseCommand):
    help = 'Creates a superuser with phone as the authentication field'

    def add_arguments(self, parser):
        parser.add_argument(
            '--phone',
            type=str,
            help='Phone number for the superuser',
        )
        parser.add_argument(
            '--name',
            type=str,
            help='Name of the superuser',
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Email address of the superuser',
        )
        parser.add_argument(
            '--password',
            type=str,
            help='Password for the superuser',
        )
        parser.add_argument(
            '--noinput',
            action='store_true',
            help='Do not prompt for input (requires all arguments)',
        )

    def handle(self, *args, **options):
        phone = options.get('phone')
        name = options.get('name')
        email = options.get('email')
        password = options.get('password')
        noinput = options.get('noinput', False)

        # If noinput is False, prompt for missing fields
        if not noinput:
            if not phone:
                phone = self.get_input('Phone number: ')
            if not name:
                name = self.get_input('Name: ', allow_blank=True)
            if not email:
                email = self.get_input('Email address: ', allow_blank=True)
            if not password:
                password = self.get_password()

        # Validate required fields
        if not phone:
            self.stdout.write(self.style.ERROR('Error: Phone number is required.'))
            return

        if not password:
            self.stdout.write(self.style.ERROR('Error: Password is required.'))
            return

        # Check if user already exists
        if User.objects.filter(phone=phone).exists():
            self.stdout.write(self.style.ERROR(f'Error: User with phone number "{phone}" already exists.'))
            return

        try:
            # Create superuser
            user = User.objects.create_user(
                phone=phone,
                username=phone,  # Will be set automatically in save(), but set explicitly here
                name=name or None,
                email=email or None,
                password=password,
                is_staff=True,
                is_superuser=True,
            )
            self.stdout.write(
                self.style.SUCCESS(f'Superuser "{user.name or user.phone}" created successfully with phone: {phone}')
            )
        except IntegrityError as e:
            self.stdout.write(self.style.ERROR(f'Error creating superuser: {e}'))
        except ValidationError as e:
            self.stdout.write(self.style.ERROR(f'Validation error: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Unexpected error: {e}'))

    def get_input(self, prompt, allow_blank=False):
        """Get input from user with optional blank allowance"""
        while True:
            value = input(prompt).strip()
            if value or allow_blank:
                return value if value else None
            self.stdout.write(self.style.WARNING('This field cannot be blank.'))

    def get_password(self):
        """Get password from user with confirmation"""
        from getpass import getpass
        while True:
            password = getpass('Password: ')
            if not password:
                self.stdout.write(self.style.WARNING('Password cannot be blank.'))
                continue
            password_confirm = getpass('Password (again): ')
            if password != password_confirm:
                self.stdout.write(self.style.ERROR('Passwords do not match. Please try again.'))
                continue
            return password
