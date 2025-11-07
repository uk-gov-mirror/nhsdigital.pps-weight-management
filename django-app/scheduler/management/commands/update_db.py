from django.core.management.base import BaseCommand
from django.db import connection, transaction

SQL_EXISTS = """
SELECT 1
FROM information_schema.tables
WHERE table_schema = 'public' AND table_name = 'item';
"""

SQL_CREATE = """
CREATE TABLE public.item (
    item_id INTEGER PRIMARY KEY,
    value   VARCHAR(255)
);
"""

class Command(BaseCommand):
    help = "Creates table public.item(item_id int PRIMARY KEY, value varchar(255)) if it does not exist."

    def handle(self, *args, **options):
        with connection.cursor() as cur:
            cur.execute(SQL_EXISTS)
            exists = cur.fetchone() is not None

        if exists:
            self.stdout.write(self.style.SUCCESS("Table public.item already exists — nothing to do."))
            return

        with transaction.atomic():
            with connection.cursor() as cur:
                cur.execute(SQL_CREATE)

        self.stdout.write(self.style.SUCCESS("Created table public.item."))
