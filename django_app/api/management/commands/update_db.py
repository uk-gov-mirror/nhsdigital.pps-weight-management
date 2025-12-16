"""
Management command: update_db

This command runs the update and seed operations for the versioned database
layers (V1, V2, V3) in sequence.

It calls:
    - <version>_update_db
    - <version>_seed_data

This command is primarily intended for developers and CI environments where
the versioned database schema and seed data need to be refreshed consistently.
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    """
    Management command entry point.

    Running:
        python manage.py update_db

    will sequentially execute:
        v1_update_db, v1_seed_data
        v2_update_db, v2_seed_data
        v3_update_db, v3_seed_data

    Any failure in a seed/update step will stop execution and surface the error.
    """

    help = (
        "Creates/updates and seeds V1_, V2_, V3_ tables in order "
        "(V1 first, then V2, then V3)."
    )

    def run_version(self, version: int):
        """
        Run one version's update and seed operations.

        Args:
            version (int): The version number (1, 2, or 3).

        Commands executed:
            - v{version}_update_db
            - v{version}_seed_data
        """
        prefix = f"v{version}"

        # update_db
        update_cmd = f"{prefix}_update_db"
        self.stdout.write(self.style.HTTP_INFO(f"Running {update_cmd}..."))
        call_command(update_cmd)
        self.stdout.write(self.style.SUCCESS(f"{update_cmd} completed."))

        # seed_data
        seed_cmd = f"{prefix}_seed_data"
        self.stdout.write(self.style.HTTP_INFO(f"Running {seed_cmd}..."))
        try:
            call_command(seed_cmd)
            self.stdout.write(self.style.SUCCESS(f"{seed_cmd} completed."))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"{seed_cmd} failed: {e}"))
            raise

    def handle(self, *args, **options):
        """Run update + seed operations for V1 → V2 → V3."""

        for version in (1, 2, 3):
            self.run_version(version)

        self.stdout.write(
            self.style.SUCCESS(
                "All update and seed operations completed successfully."
            )
        )
