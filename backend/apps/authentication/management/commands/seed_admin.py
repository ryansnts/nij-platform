"""
Management command: python manage.py seed_admin
Creates the default admin user if it doesn't exist.
Reads credentials from env vars ADMIN_USERNAME / ADMIN_PASSWORD.
"""
import os
from django.core.management.base import BaseCommand
from apps.authentication.models import User


class Command(BaseCommand):
    help = "Create default admin user from environment variables"

    def handle(self, *args, **options):
        username = os.environ.get("ADMIN_USERNAME", "admin")
        password = os.environ.get("ADMIN_PASSWORD", "")
        email = os.environ.get("ADMIN_EMAIL", "admin@nij.local")

        if not password:
            self.stderr.write(self.style.ERROR(
                "ADMIN_PASSWORD env var is required. Skipping admin creation."
            ))
            return

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(
                f'User "{username}" already exists. Skipping.'
            ))
            return

        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
            role=User.Role.ADMIN,
        )
        self.stdout.write(self.style.SUCCESS(
            f'Admin user "{username}" created successfully.'
        ))
