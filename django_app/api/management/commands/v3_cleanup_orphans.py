# api/management/commands/v3_cleanup_orphans.py
#
# Usage: python manage.py v3_cleanup_orphans

from django.core.management.base import BaseCommand
from django.db import transaction

from api.models_v3 import (
    V3_Contact,
    V3_Location,
)

class Command(BaseCommand):
    help = (
        "Clean up orphaned V3 contacts and locations.\n\n"
        "Orphan contact = no V3_Service_Contact rows and no V3_Location rows referencing it.\n"
        "Orphan location = no V3_Service_Location rows referencing it.\n"
        "By default this is a dry run; pass --commit to actually delete."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--commit",
            action="store_true",
            help="Actually delete the orphan contacts and locations.",
        )

    def handle(self, *args, **options):
        commit = options["commit"]

        # Orphan contacts: no service contacts, no locations referencing them
        orphan_contacts = V3_Contact.objects.filter(
            v3_service_contact__isnull=True,  # no V3_Service_Contact rows
            v3_location__isnull=True,         # no V3_Location rows
        )

        # Orphan locations: no service locations referencing them
        orphan_locations = V3_Location.objects.filter(
            v3_service_location__isnull=True
        )

        num_contacts = orphan_contacts.count()
        num_locations = orphan_locations.count()

        self.stdout.write(self.style.NOTICE("V3 orphan cleanup (dry-run summary):"))
        self.stdout.write(f"- Orphan contacts:  {num_contacts}")
        self.stdout.write(f"- Orphan locations: {num_locations}")

        if not commit:
            self.stdout.write("")
            self.stdout.write(
                "No changes made (dry run).\n"
                "Run again with --commit to actually delete these objects."
            )
            return

        with transaction.atomic():
            c_deleted, _ = orphan_contacts.delete()
            l_deleted, _ = orphan_locations.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {c_deleted} orphan contacts and {l_deleted} orphan locations."
            )
        )
