# api/management/commands/v3_seed_data.py

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection, transaction


TABLES_IN_DELETE_ORDER = [
    # Through tables that depend on others
    "V3_SERVICE_LOCATION",
    "V3_SERVICE_CONTACT",
    "V3_SERVICE_TAXONOMY",
    "V3_SERVICE_COSTS",
    "V3_SERVICE_ACCESS",
    "V3_SERVICE_TIME_REQUIRED",
    "V3_SERVICE_MITIGATIONS",
    "V3_SERVICE_WHO_NOT_FOR",
    "V3_SERVICE_WHO_FOR",
    "V3_SERVICE_HELPS_WITH",
    "V3_SERVICE_CATEGORY",
    # Core tables that depend on lookups
    "V3_SERVICE",
    "V3_LOCATION",
    "V3_CONTACT",
    # Lookups
    "V3_CATEGORY",
    "V3_TAXONOMY",
    "V3_COSTS",
    "V3_ACCESS",
    "V3_TIME_REQUIRED",
    "V3_MITIGATIONS",
    "V3_WHO_NOT_FOR",
    "V3_WHO_FOR",
    "V3_HELPS_WITH",
    "V3_SERVICE_TYPE",
    "V3_ACTION_TYPE",
]

# Tables where we need to reset the sequence after loaddata
SEQ_TABLES = [
    "V3_ACTION_TYPE",
    "V3_SERVICE_TYPE",
    "V3_ACCESS",
    "V3_CATEGORY",
    "V3_COSTS",
    "V3_HELPS_WITH",
    "V3_MITIGATIONS",
    "V3_TAXONOMY",
    "V3_TIME_REQUIRED",
    "V3_WHO_FOR",
    "V3_WHO_NOT_FOR",
    "V3_CONTACT",
    "V3_LOCATION",
    "V3_SERVICE",
    "V3_SERVICE_CATEGORY",
    "V3_SERVICE_HELPS_WITH",
    "V3_SERVICE_WHO_FOR",
    "V3_SERVICE_WHO_NOT_FOR",
    "V3_SERVICE_MITIGATIONS",
    "V3_SERVICE_TIME_REQUIRED",
    "V3_SERVICE_ACCESS",
    "V3_SERVICE_COSTS",
    "V3_SERVICE_TAXONOMY",
    "V3_SERVICE_CONTACT",
    "V3_SERVICE_LOCATION",
]


class Command(BaseCommand):
    help = (
        "Wipe and reseed ALL V3_* tables using the v3_seed.json fixture.\n\n"
        "This is called by `update_db` for V3 after v3_update_db has ensured the tables exist."
    )

    def handle(self, *args, **options):
        self.stdout.write(self.style.HTTP_INFO("Clearing all V3_* tables..."))

        with transaction.atomic():
            with connection.cursor() as cur:
                for table in TABLES_IN_DELETE_ORDER:
                    cur.execute(f'DELETE FROM "{table}";')
            self.stdout.write(self.style.WARNING("Cleared all V3_* tables."))

            # Clear htsh activity-attribute tables (also seeded from v3_seed.json)
            self.stdout.write(self.style.HTTP_INFO("Clearing activity attribute tables..."))
            with connection.cursor() as cur:
                cur.execute('DELETE FROM "service_activity_attribute";')
                cur.execute('DELETE FROM "activity_attribute";')
            self.stdout.write(self.style.WARNING("Cleared activity attribute tables."))

            self.stdout.write(self.style.HTTP_INFO("Loading V3 fixture (v3_seed)..."))
            # This expects api/fixtures/v3_seed.json to be present in the repo.
            call_command("loaddata", "v3_seed")

            self.stdout.write(self.style.HTTP_INFO("Resetting V3_* sequences..."))
            with connection.cursor() as cur:
                for table in SEQ_TABLES:
                    # Get the sequence backing the 'id' column (if any)
                    cur.execute("SELECT pg_get_serial_sequence(%s, 'id')", [f'"{table}"'])
                    seq_name = cur.fetchone()[0]
                    if not seq_name:
                        continue
                    # Bump it to max(id) so new rows won't conflict with seeded ones
                    cur.execute(
                        f'SELECT setval(%s, COALESCE((SELECT MAX(id) FROM "{table}"), 1))',
                        [seq_name],
                    )

            # Reset sequences for activity attribute tables
            for table in ["activity_attribute", "service_activity_attribute"]:
                try:
                    cur = connection.cursor()
                    cur.execute("SELECT pg_get_serial_sequence(%s, 'id')", [table])
                    seq_name = cur.fetchone()[0]
                    if seq_name:
                        cur.execute(
                            f'SELECT setval(%s, COALESCE((SELECT MAX(id) FROM "{table}"), 1))',
                            [seq_name],
                        )
                except Exception:
                    pass  # Table may not have a sequence (e.g., SQLite in tests)

        self.stdout.write(self.style.SUCCESS("V3_* tables reseeded from v3_seed.json."))
