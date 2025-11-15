from django.core.management.base import BaseCommand
from django.db import connection, transaction

SQL = [
    # --- Lookup tables ---
    '''
    DROP TABLE IF EXISTS "V1_ACTION_TYPE" CASCADE;
CREATE TABLE "V1_ACTION_TYPE" ("id" INTEGER PRIMARY KEY,
        "type" VARCHAR(120) NOT NULL);
    ''',
    '''
    DROP TABLE IF EXISTS "V1_SERVICE_TYPE" CASCADE;
CREATE TABLE "V1_SERVICE_TYPE" ("id" INTEGER PRIMARY KEY,
        "type" VARCHAR(120) NOT NULL);
    ''',
    '''
    DROP TABLE IF EXISTS "V1_HELPS_WITH" CASCADE;
CREATE TABLE "V1_HELPS_WITH" ("id" INTEGER PRIMARY KEY,
        "benefit" VARCHAR(120) NOT NULL);
    ''',
    '''
    DROP TABLE IF EXISTS "V1_WHO_FOR" CASCADE;
CREATE TABLE "V1_WHO_FOR" ("id" INTEGER PRIMARY KEY,
        "target" VARCHAR(120) NOT NULL);
    ''',
    '''
    DROP TABLE IF EXISTS "V1_WHO_NOT_FOR" CASCADE;
CREATE TABLE "V1_WHO_NOT_FOR" ("id" INTEGER PRIMARY KEY,
        "target" VARCHAR(120) NOT NULL);
    ''',
    '''
    DROP TABLE IF EXISTS "V1_MITIGATIONS" CASCADE;
CREATE TABLE "V1_MITIGATIONS" ("id" INTEGER PRIMARY KEY,
        "type" VARCHAR(120) NOT NULL);
    ''',
    '''
    DROP TABLE IF EXISTS "V1_TIME_REQUIRED" CASCADE;
CREATE TABLE "V1_TIME_REQUIRED" ("id" INTEGER PRIMARY KEY,
        "required" VARCHAR(120) NOT NULL);
    ''',
    '''
    DROP TABLE IF EXISTS "V1_ACCESS" CASCADE;
CREATE TABLE "V1_ACCESS" ("id" INTEGER PRIMARY KEY,
        "type" VARCHAR(120) NOT NULL);
    ''',
    '''
    DROP TABLE IF EXISTS "V1_COSTS" CASCADE;
CREATE TABLE "V1_COSTS" ("id" INTEGER PRIMARY KEY,
        "name" VARCHAR(120) NOT NULL);
    ''',
    '''
    DROP TABLE IF EXISTS "V1_TAXONOMY" CASCADE;
CREATE TABLE "V1_TAXONOMY" ("id" INTEGER PRIMARY KEY,
        "term" VARCHAR(120) NOT NULL);
    ''',

    # --- Service table ---
    '''
    DROP TABLE IF EXISTS "V1_SERVICE" CASCADE;
CREATE TABLE "V1_SERVICE" ("id" INTEGER PRIMARY KEY,
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
        CONSTRAINT "v1_service_action_fk"
            FOREIGN KEY ("action_id") REFERENCES "V1_ACTION_TYPE"("id")
            ON UPDATE NO ACTION ON DELETE SET NULL,
        CONSTRAINT "v1_service_servicetype_fk"
            FOREIGN KEY ("service_type_id") REFERENCES "V1_SERVICE_TYPE"("id")
            ON UPDATE NO ACTION ON DELETE SET NULL);
    ''',

    # --- M2M (through) tables ---
    '''
    DROP TABLE IF EXISTS "V1_SERVICE_HELPS_WITH" CASCADE;
CREATE TABLE "V1_SERVICE_HELPS_WITH" ("id" BIGSERIAL PRIMARY KEY,
    "service_id" INTEGER NOT NULL,
        "helpswith_id" INTEGER NOT NULL,
        UNIQUE ("service_id","helpswith_id"),
        FOREIGN KEY ("service_id") REFERENCES "V1_SERVICE"("id") ON DELETE CASCADE,
        FOREIGN KEY ("helpswith_id") REFERENCES "V1_HELPS_WITH"("id") ON DELETE CASCADE);
    ''',
    '''
    DROP TABLE IF EXISTS "V1_SERVICE_WHO_FOR" CASCADE;
CREATE TABLE "V1_SERVICE_WHO_FOR" ("id" BIGSERIAL PRIMARY KEY,
    "service_id" INTEGER NOT NULL,
        "who_for_id" INTEGER NOT NULL,
        UNIQUE ("service_id","who_for_id"),
        FOREIGN KEY ("service_id") REFERENCES "V1_SERVICE"("id") ON DELETE CASCADE,
        FOREIGN KEY ("who_for_id") REFERENCES "V1_WHO_FOR"("id") ON DELETE CASCADE);
    ''',
    '''
    DROP TABLE IF EXISTS "V1_SERVICE_WHO_NOT_FOR" CASCADE;
CREATE TABLE "V1_SERVICE_WHO_NOT_FOR" ("id" BIGSERIAL PRIMARY KEY,
    "service_id" INTEGER NOT NULL,
        "who_not_for_id" INTEGER NOT NULL,
        UNIQUE ("service_id","who_not_for_id"),
        FOREIGN KEY ("service_id") REFERENCES "V1_SERVICE"("id") ON DELETE CASCADE,
        FOREIGN KEY ("who_not_for_id") REFERENCES "V1_WHO_NOT_FOR"("id") ON DELETE CASCADE);
    ''',
    '''
    DROP TABLE IF EXISTS "V1_SERVICE_MITIGATIONS" CASCADE;
CREATE TABLE "V1_SERVICE_MITIGATIONS" ("id" BIGSERIAL PRIMARY KEY,
    "service_id" INTEGER NOT NULL,
        "mitigation_id" INTEGER NOT NULL,
        UNIQUE ("service_id","mitigation_id"),
        FOREIGN KEY ("service_id") REFERENCES "V1_SERVICE"("id") ON DELETE CASCADE,
        FOREIGN KEY ("mitigation_id") REFERENCES "V1_MITIGATIONS"("id") ON DELETE CASCADE);
    ''',
    '''
    DROP TABLE IF EXISTS "V1_SERVICE_TIME_REQUIRED" CASCADE;
CREATE TABLE "V1_SERVICE_TIME_REQUIRED" ("id" BIGSERIAL PRIMARY KEY,
    "service_id" INTEGER NOT NULL,
        "time_id" INTEGER NOT NULL,
        UNIQUE ("service_id","time_id"),
        FOREIGN KEY ("service_id") REFERENCES "V1_SERVICE"("id") ON DELETE CASCADE,
        FOREIGN KEY ("time_id") REFERENCES "V1_TIME_REQUIRED"("id") ON DELETE CASCADE);
    ''',
    '''
    DROP TABLE IF EXISTS "V1_SERVICE_ACCESS" CASCADE;
CREATE TABLE "V1_SERVICE_ACCESS" ("id" BIGSERIAL PRIMARY KEY,
    "service_id" INTEGER NOT NULL,
        "access_id" INTEGER NOT NULL,
        UNIQUE ("service_id","access_id"),
        FOREIGN KEY ("service_id") REFERENCES "V1_SERVICE"("id") ON DELETE CASCADE,
        FOREIGN KEY ("access_id") REFERENCES "V1_ACCESS"("id") ON DELETE CASCADE);
    ''',
    '''
    DROP TABLE IF EXISTS "V1_SERVICE_COSTS" CASCADE;
CREATE TABLE "V1_SERVICE_COSTS" ("id" BIGSERIAL PRIMARY KEY,
    "service_id" INTEGER NOT NULL,
        "cost_id" INTEGER NOT NULL,
        UNIQUE ("service_id","cost_id"),
        FOREIGN KEY ("service_id") REFERENCES "V1_SERVICE"("id") ON DELETE CASCADE,
        FOREIGN KEY ("cost_id") REFERENCES "V1_COSTS"("id") ON DELETE CASCADE);
    ''',
    '''
    DROP TABLE IF EXISTS "V1_SERVICE_TAXONOMY" CASCADE;
CREATE TABLE "V1_SERVICE_TAXONOMY" ("id" BIGSERIAL PRIMARY KEY,
    "service_id" INTEGER NOT NULL,
        "taxonomy_id" INTEGER NOT NULL,
        UNIQUE ("service_id","taxonomy_id"),
        FOREIGN KEY ("service_id") REFERENCES "V1_SERVICE"("id") ON DELETE CASCADE,
        FOREIGN KEY ("taxonomy_id") REFERENCES "V1_TAXONOMY"("id") ON DELETE CASCADE);
    ''',

    # --- Helpful indexes (optional) ---
    'CREATE INDEX IF NOT EXISTS "v1_service_idx_sort" ON "V1_SERVICE" ("sort_order","name");',
    'CREATE INDEX IF NOT EXISTS "v1_service_action_idx" ON "V1_SERVICE" ("action_id");',
    'CREATE INDEX IF NOT EXISTS "v1_service_type_idx" ON "V1_SERVICE" ("service_type_id");',
]

class Command(BaseCommand):
    help = "Creates all V1_* tables (lookup, service, and through) if they do not exist."

    def handle(self, *args, **options):
        with transaction.atomic():
            with connection.cursor() as cur:
                for stmt in SQL:
                    cur.execute(stmt)
        self.stdout.write(self.style.SUCCESS("V1_* tables ensured."))
