import os
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from core.vault import import_vault


class Command(BaseCommand):
    help = "Import the Obsidian career/ tree (opportunities, CVs, job postings, strategy notes). Re-runnable."

    def add_arguments(self, parser):
        parser.add_argument("path", help="…/Knowledge Base/career")
        parser.add_argument("--owner", default=os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin"))

    def handle(self, path, owner, **options):
        user = get_user_model().objects.filter(username=owner).first()
        if not user:
            raise CommandError(f"no user {owner!r}; run seed_superuser or pass --owner")
        counts = import_vault(user, Path(path))
        self.stdout.write(self.style.SUCCESS(f"imported {counts}"))
