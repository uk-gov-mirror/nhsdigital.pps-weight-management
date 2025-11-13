from django.core.management.base import BaseCommand
from django.db import connection, transaction

SQL = [
    # --- Lookup + Category ---
    '''
    CREATE TABLE IF NOT EXISTS "V2_ACTION_TYPE" (
        "id" INTEGER PRIMARY KEY,
        "type" VARCHAR(120) NOT NULL
    );
    ''',
    '''
    CREATE TABLE IF NOT EXISTS "V2_SERVICE_TYPE" (
        "id" INTEGER PRIMARY KEY,
        "type" VARCHAR(120) NOT NULL
    );
    ''',
    '''
    CREATE TABLE IF NOT EXISTS "V2_HELPS_WITH" (
        "id" INTEGER PRIMARY KEY,
        "benefit" VARCHAR(120) NOT NULL
    );
    ''',
    '''
    CREATE TABLE IF NOT EXISTS "V2_WHO_FOR" (
        "id" INTEGER PRIMARY KEY,
        "target" VARCHAR(120) NOT NULL
    );
    ''',
    '''
    CREATE TABLE IF NOT EXISTS "V2_WHO_NOT_FOR" (
        "id" INTEGER PRIMARY KEY,
        "target" VARCHAR(120) NOT NULL
    );
    ''',
    '''
    CREATE TABLE IF NOT EXISTS "V2_MITIGATIONS" (
        "id" INTEGER PRIMARY KEY,
        "type" VARCHAR(120) NOT NULL
    );
    ''',
    '''
    CREATE TABLE IF NOT EXISTS "V2_TIME_REQUIRED" (
        "id" INTEGER PRIMARY KEY,
        "required" VARCHAR(120) NOT NULL
    );
    ''',
    '''
    CREATE TABLE IF NOT EXISTS "V2_ACCESS" (
        "id" INTEGER PRIMARY KEY,
        "type" VARCHAR(120) NOT NULL
    );
    ''',
    '''
    CREATE TABLE IF NOT EXISTS "V2_COSTS" (
        "id" INTEGER PRIMARY KEY,
        "name" VARCHAR(120) NOT NULL
    );
    ''',
    '''
    CREATE TABLE IF NOT EXISTS "V2_TAXONOMY" (
        "id" INTEGER PRIMARY KEY,
        "term" VARCHAR(120) NOT NULL
    );
    ''',
    '''
    CREATE TABLE IF NOT EXISTS "V2_CATEGORY" (
        "id" INTEGER PRIMARY KEY,
        "goal" VARCHAR(120) NOT NULL
    );
    ''',

    # --- Service table ---
    '''
    CREATE TABLE IF NOT EXISTS "V2_SERVICE" (
        "id" INTEGER PRIMARY KEY,
        "name" VARCHAR(120) NOT NULL,
        "description" TEXT,
        "what_it_is" TEXT,
        "how_it_works" TEXT,
        "what_it_could_do" TEXT,
        "cost_text" VARCHAR(120),
        "action_text" VARCHAR(120),
        "action_url" VARCHAR(255),
        "action_url_playstore" VARCHAR(255),
        "action_url_appstore" VARCHAR(255),
        "action_url_moreinfo" VARCHAR(255),
        "logo_image" VARCHAR(255),
        "promo" VARCHAR(255),
        "action_id" INTEGER,
        "service_type_id" INTEGER,
        "sort_order" DOUBLE PRECISION,
        CONSTRAINT "v2_service_action_fk"
            FOREIGN KEY ("action_id") REFERENCES "V2_ACTION_TYPE"("id")
            ON UPDATE NO ACTION ON DELETE SET NULL,
        CONSTRAINT "v2_service_servicetype_fk"
            FOREIGN KEY ("service_type_id") REFERENCES "V2_SERVICE_TYPE"("id")
            ON UPDATE NO ACTION ON DELETE SET NULL
    );
    ''',

    # --- M2M (through) tables ---
    '''
    CREATE TABLE IF NOT EXISTS "V2_SERVICE_CATEGORY" (
        "service_id" INTEGER NOT NULL,
        "category_id" INTEGER NOT NULL,
        PRIMARY KEY ("service_id","category_id"),
        FOREIGN KEY ("service_id") REFERENCES "V2_SERVICE"("id") ON DELETE CASCADE,
        FOREIGN KEY ("category_id") REFERENCES "V2_CATEGORY"("id") ON DELETE CASCADE
    );
    ''',
    '''
    CREATE TABLE IF NOT EXISTS "V2_SERVICE_HELPS_WITH" (
        "service_id" INTEGER NOT NULL,
        "helpswith_id" INTEGER NOT NULL,
        PRIMARY KEY ("service_id","helpswith_id"),
        FOREIGN KEY ("service_id") REFERENCES "V2_SERVICE"("id") ON DELETE CASCADE,
        FOREIGN KEY ("helpswith_id") REFERENCES "V2_HELPS_WITH"("id") ON DELETE CASCADE
    );
    ''',
    '''
    CREATE TABLE IF NOT EXISTS "V2_SERVICE_WHO_FOR" (
        "service_id" INTEGER NOT NULL,
        "who_for_id" INTEGER NOT NULL,
        PRIMARY KEY ("service_id","who_for_id"),
        FOREIGN KEY ("service_id") REFERENCES "V2_SERVICE"("id") ON DELETE CASCADE,
        FOREIGN KEY ("who_for_id") REFERENCES "V2_WHO_FOR"("id") ON DELETE CASCADE
    );
    ''',
    '''
    CREATE TABLE IF NOT EXISTS "V2_SERVICE_WHO_NOT_FOR" (
        "service_id" INTEGER NOT NULL,
        "who_not_for_id" INTEGER NOT NULL,
        PRIMARY KEY ("service_id","who_not_for_id"),
        FOREIGN KEY ("service_id") REFERENCES "V2_SERVICE"("id") ON DELETE CASCADE,
        FOREIGN KEY ("who_not_for_id") REFERENCES "V2_WHO_NOT_FOR"("id") ON DELETE CASCADE
    );
    ''',
    '''
    CREATE TABLE IF NOT EXISTS "V2_SERVICE_MITIGATIONS" (
        "service_id" INTEGER NOT NULL,
        "mitigation_id" INTEGER NOT NULL,
        PRIMARY KEY ("service_id","mitigation_id"),
        FOREIGN KEY ("service_id") REFERENCES "V2_SERVICE"("id") ON DELETE CASCADE,
        FOREIGN KEY ("mitigation_id") REFERENCES "V2_MITIGATIONS"("id") ON DELETE CASCADE
    );
    ''',
    '''
    CREATE TABLE IF NOT EXISTS "V2_SERVICE_TIME_REQUIRED" (
        "service_id" INTEGER NOT NULL,
        "time_id" INTEGER NOT NULL,
        PRIMARY KEY ("service_id","time_id"),
        FOREIGN KEY ("service_id") REFERENCES "V2_SERVICE"("id") ON DELETE CASCADE,
        FOREIGN KEY ("time_id") REFERENCES "V2_TIME_REQUIRED"("id") ON DELETE CASCADE
    );
    ''',
    '''
    CREATE TABLE IF NOT EXISTS "V2_SERVICE_ACCESS" (
        "service_id" INTEGER NOT NULL,
        "access_id" INTEGER NOT NULL,
        PRIMARY KEY ("service_id","access_id"),
        FOREIGN KEY ("service_id") REFERENCES "V2_SERVICE"("id") ON DELETE CASCADE,
        FOREIGN KEY ("access_id") REFERENCES "V2_ACCESS"("id") ON DELETE CASCADE
    );
    ''',
    '''
    CREATE TABLE IF NOT EXISTS "V2_SERVICE_COSTS" (
        "service_id" INTEGER NOT NULL,
        "cost_id" INTEGER NOT NULL,
        PRIMARY KEY ("service_id","cost_id"),
        FOREIGN KEY ("service_id") REFERENCES "V2_SERVICE"("id") ON DELETE CASCADE,
        FOREIGN KEY ("cost_id") REFERENCES "V2_COSTS"("id") ON DELETE CASCADE
    );
    ''',
    '''
    CREATE TABLE IF NOT EXISTS "V2_SERVICE_TAXONOMY" (
        "service_id" INTEGER NOT NULL,
        "taxonomy_id" INTEGER NOT NULL,
        PRIMARY KEY ("service_id","taxonomy_id"),
        FOREIGN KEY ("service_id") REFERENCES "V2_SERVICE"("id") ON DELETE CASCADE,
        FOREIGN KEY ("taxonomy_id") REFERENCES "V2_TAXONOMY"("id") ON DELETE CASCADE
    );
    ''',

    # --- Helpful indexes (optional) ---
    'CREATE INDEX IF NOT EXISTS "v2_service_idx_sort" ON "V2_SERVICE" ("sort_order","name");',
    'CREATE INDEX IF NOT EXISTS "v2_service_action_idx" ON "V2_SERVICE" ("action_id");',
    'CREATE INDEX IF NOT EXISTS "v2_service_type_idx" ON "V2_SERVICE" ("service_type_id");',
]

class Command(BaseCommand):
    help = "Creates all V2_* tables (lookup, service, category, and through) if they do not exist."

    def handle(self, *args, **options):
        with transaction.atomic():
            with connection.cursor() as cur:
                for stmt in SQL:
                    cur.execute(stmt)
        self.stdout.write(self.style.SUCCESS("V2_* tables ensured."))
