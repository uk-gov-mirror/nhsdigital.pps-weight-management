# api/management/commands/v3_cleanup_and_export.py
#
# Usage: python manage.py v3_cleanup_and_export
#        python manage.py v3_cleanup_and_export --output api/fixtures/v3_seed.json

from django.core.management.base import BaseCommand
from django.core.management import call_command

class Command(BaseCommand):
    help = (
        "Run v3 orphan cleanup (contacts + locations) and then export the V3 fixture.\n\n"
        "Equivalent to:\n"
        "  manage.py v3_cleanup_orphans --commit\n"
        "  manage.py v3_export_fixture [--output ...]\n"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            "-o",
            dest="output",
            default="api/fixtures/v3_seed.json",
            help="Path to write the JSON fixture (default: api/fixtures/v3_seed.json)",
        )

    def handle(self, *args, **options):
        output = options["output"]

        self.stdout.write(self.style.HTTP_INFO("Running v3_cleanup_orphans --commit ..."))
        # This will delete orphans; no dry-run here.
        call_command("v3_cleanup_orphans", commit=True)

        self.stdout.write(self.style.HTTP_INFO(f"Exporting V3 data to {output} ..."))
        # Delegate to the existing export command
        call_command("v3_export_fixture", output=output)

        self.stdout.write(self.style.SUCCESS("Cleanup + export completed."))
