from django.core.management.base import BaseCommand
from django.db import connection, transaction

SQL = [
    # --- Lookup + Category ---
    '''
    DROP TABLE IF EXISTS "V3_ACTION_TYPE" CASCADE;
CREATE TABLE "V3_ACTION_TYPE" ("id" BIGSERIAL PRIMARY KEY, "type" VARCHAR(120) NOT NULL);
    ''',
    '''
    DROP TABLE IF EXISTS "V3_SERVICE_TYPE" CASCADE;
CREATE TABLE "V3_SERVICE_TYPE" ("id" BIGSERIAL PRIMARY KEY, "type" VARCHAR(120) NOT NULL);
    ''',
    '''
    DROP TABLE IF EXISTS "V3_HELPS_WITH" CASCADE;
CREATE TABLE "V3_HELPS_WITH" ("id" BIGSERIAL PRIMARY KEY, "benefit" VARCHAR(120) NOT NULL);
    ''',
    '''
    DROP TABLE IF EXISTS "V3_WHO_FOR" CASCADE;
CREATE TABLE "V3_WHO_FOR" ("id" BIGSERIAL PRIMARY KEY, "target" VARCHAR(120) NOT NULL);
    ''',
    '''
    DROP TABLE IF EXISTS "V3_WHO_NOT_FOR" CASCADE;
CREATE TABLE "V3_WHO_NOT_FOR" ("id" BIGSERIAL PRIMARY KEY, "target" VARCHAR(120) NOT NULL);
    ''',
    '''
    DROP TABLE IF EXISTS "V3_MITIGATIONS" CASCADE;
CREATE TABLE "V3_MITIGATIONS" ("id" BIGSERIAL PRIMARY KEY, "type" VARCHAR(120) NOT NULL);
    ''',
    '''
    DROP TABLE IF EXISTS "V3_TIME_REQUIRED" CASCADE;
CREATE TABLE "V3_TIME_REQUIRED" ("id" BIGSERIAL PRIMARY KEY, "required" VARCHAR(120) NOT NULL);
    ''',
    '''
    DROP TABLE IF EXISTS "V3_ACCESS" CASCADE;
CREATE TABLE "V3_ACCESS" ("id" BIGSERIAL PRIMARY KEY, "type" VARCHAR(120) NOT NULL);
    ''',
    '''
    DROP TABLE IF EXISTS "V3_COSTS" CASCADE;
CREATE TABLE "V3_COSTS" ("id" BIGSERIAL PRIMARY KEY, "name" VARCHAR(120) NOT NULL);
    ''',
    '''
    DROP TABLE IF EXISTS "V3_TAXONOMY" CASCADE;
CREATE TABLE "V3_TAXONOMY" ("id" BIGSERIAL PRIMARY KEY, "term" VARCHAR(120) NOT NULL);
    ''',
    '''
    DROP TABLE IF EXISTS "V3_CATEGORY" CASCADE;
CREATE TABLE "V3_CATEGORY" ("id" BIGSERIAL PRIMARY KEY, "goal" VARCHAR(120) NOT NULL);
    ''',

    # --- Service table ---
    '''
    DROP TABLE IF EXISTS "V3_SERVICE" CASCADE;
CREATE TABLE "V3_SERVICE" ("id" BIGSERIAL PRIMARY KEY,
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
        "opening_hours" VARCHAR(255),
        "action_id" INTEGER,
        "service_type_id" INTEGER,
        "sort_order" DOUBLE PRECISION,
        CONSTRAINT "V3_service_action_fk"
            FOREIGN KEY ("action_id") REFERENCES "V3_ACTION_TYPE"("id")
            ON UPDATE NO ACTION ON DELETE SET NULL,
        CONSTRAINT "V3_service_servicetype_fk"
            FOREIGN KEY ("service_type_id") REFERENCES "V3_SERVICE_TYPE"("id")
            ON UPDATE NO ACTION ON DELETE SET NULL);
    ''',

    '''
    DROP TABLE IF EXISTS "V3_CONTACT" CASCADE;
CREATE TABLE "V3_CONTACT" (
    "id" BIGSERIAL PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL,
    "phone" VARCHAR(64),
    "email" VARCHAR(255)
);
    ''',
    '''
    DROP TABLE IF EXISTS "V3_SERVICE_CONTACT" CASCADE;
CREATE TABLE "V3_SERVICE_CONTACT" (
    "id" BIGSERIAL PRIMARY KEY,
    "service_id" INTEGER NOT NULL,
    "contact_id" INTEGER NOT NULL,
    UNIQUE ("service_id"),
    FOREIGN KEY ("service_id") REFERENCES "V3_SERVICE"("id") ON DELETE CASCADE,
    FOREIGN KEY ("contact_id") REFERENCES "V3_CONTACT"("id") ON DELETE CASCADE
);
    ''',
    '''
    DROP TABLE IF EXISTS "V3_LOCATION" CASCADE;
CREATE TABLE "V3_LOCATION" (
    "id" BIGSERIAL PRIMARY KEY,
    "address_1" VARCHAR(255) NOT NULL,
    "address_2" VARCHAR(255),
    "town" VARCHAR(255),
    "postcode" VARCHAR(32),
    "lat" DOUBLE PRECISION,
    "lon" DOUBLE PRECISION,
    "opening_hours" VARCHAR(255),
    "contact_id" INTEGER  -- NEW
);

ALTER TABLE "V3_LOCATION"
    ADD CONSTRAINT "V3_location_contact_fk"
    FOREIGN KEY ("contact_id")
    REFERENCES "V3_CONTACT" ("id")
    ON UPDATE NO ACTION
    ON DELETE SET NULL;
    ''',
    '''
    DROP TABLE IF EXISTS "V3_SERVICE_LOCATION" CASCADE;
CREATE TABLE "V3_SERVICE_LOCATION" (
    "id" BIGSERIAL PRIMARY KEY,
    "service_id" INTEGER NOT NULL,
    "location_id" INTEGER NOT NULL,
    UNIQUE ("service_id", "location_id"),
    FOREIGN KEY ("service_id") REFERENCES "V3_SERVICE"("id") ON DELETE CASCADE,
    FOREIGN KEY ("location_id") REFERENCES "V3_LOCATION"("id") ON DELETE CASCADE
);
    ''',

    # --- M2M (through) tables ---
    '''
    DROP TABLE IF EXISTS "V3_SERVICE_CATEGORY" CASCADE;
CREATE TABLE "V3_SERVICE_CATEGORY" ("id" BIGSERIAL PRIMARY KEY,
    "service_id" INTEGER NOT NULL,
        "category_id" INTEGER NOT NULL,
        UNIQUE ("service_id","category_id"),
        FOREIGN KEY ("service_id") REFERENCES "V3_SERVICE"("id") ON DELETE CASCADE,
        FOREIGN KEY ("category_id") REFERENCES "V3_CATEGORY"("id") ON DELETE CASCADE);
    ''',
    '''
    DROP TABLE IF EXISTS "V3_SERVICE_HELPS_WITH" CASCADE;
CREATE TABLE "V3_SERVICE_HELPS_WITH" ("id" BIGSERIAL PRIMARY KEY,
    "service_id" INTEGER NOT NULL,
        "helpswith_id" INTEGER NOT NULL,
        UNIQUE ("service_id","helpswith_id"),
        FOREIGN KEY ("service_id") REFERENCES "V3_SERVICE"("id") ON DELETE CASCADE,
        FOREIGN KEY ("helpswith_id") REFERENCES "V3_HELPS_WITH"("id") ON DELETE CASCADE);
    ''',
    '''
    DROP TABLE IF EXISTS "V3_SERVICE_WHO_FOR" CASCADE;
CREATE TABLE "V3_SERVICE_WHO_FOR" ("id" BIGSERIAL PRIMARY KEY,
    "service_id" INTEGER NOT NULL,
        "who_for_id" INTEGER NOT NULL,
        UNIQUE ("service_id","who_for_id"),
        FOREIGN KEY ("service_id") REFERENCES "V3_SERVICE"("id") ON DELETE CASCADE,
        FOREIGN KEY ("who_for_id") REFERENCES "V3_WHO_FOR"("id") ON DELETE CASCADE);
    ''',
    '''
    DROP TABLE IF EXISTS "V3_SERVICE_WHO_NOT_FOR" CASCADE;
CREATE TABLE "V3_SERVICE_WHO_NOT_FOR" ("id" BIGSERIAL PRIMARY KEY,
    "service_id" INTEGER NOT NULL,
        "who_not_for_id" INTEGER NOT NULL,
        UNIQUE ("service_id","who_not_for_id"),
        FOREIGN KEY ("service_id") REFERENCES "V3_SERVICE"("id") ON DELETE CASCADE,
        FOREIGN KEY ("who_not_for_id") REFERENCES "V3_WHO_NOT_FOR"("id") ON DELETE CASCADE);
    ''',
    '''
    DROP TABLE IF EXISTS "V3_SERVICE_MITIGATIONS" CASCADE;
CREATE TABLE "V3_SERVICE_MITIGATIONS" ("id" BIGSERIAL PRIMARY KEY,
    "service_id" INTEGER NOT NULL,
        "mitigation_id" INTEGER NOT NULL,
        UNIQUE ("service_id","mitigation_id"),
        FOREIGN KEY ("service_id") REFERENCES "V3_SERVICE"("id") ON DELETE CASCADE,
        FOREIGN KEY ("mitigation_id") REFERENCES "V3_MITIGATIONS"("id") ON DELETE CASCADE);
    ''',
    '''
    DROP TABLE IF EXISTS "V3_SERVICE_TIME_REQUIRED" CASCADE;
CREATE TABLE "V3_SERVICE_TIME_REQUIRED" ("id" BIGSERIAL PRIMARY KEY,
    "service_id" INTEGER NOT NULL,
        "time_id" INTEGER NOT NULL,
        UNIQUE ("service_id","time_id"),
        FOREIGN KEY ("service_id") REFERENCES "V3_SERVICE"("id") ON DELETE CASCADE,
        FOREIGN KEY ("time_id") REFERENCES "V3_TIME_REQUIRED"("id") ON DELETE CASCADE);
    ''',
    '''
    DROP TABLE IF EXISTS "V3_SERVICE_ACCESS" CASCADE;
CREATE TABLE "V3_SERVICE_ACCESS" ("id" BIGSERIAL PRIMARY KEY,
    "service_id" INTEGER NOT NULL,
        "access_id" INTEGER NOT NULL,
        UNIQUE ("service_id","access_id"),
        FOREIGN KEY ("service_id") REFERENCES "V3_SERVICE"("id") ON DELETE CASCADE,
        FOREIGN KEY ("access_id") REFERENCES "V3_ACCESS"("id") ON DELETE CASCADE);
    ''',
    '''
    DROP TABLE IF EXISTS "V3_SERVICE_COSTS" CASCADE;
CREATE TABLE "V3_SERVICE_COSTS" ("id" BIGSERIAL PRIMARY KEY,
    "service_id" INTEGER NOT NULL,
        "cost_id" INTEGER NOT NULL,
        UNIQUE ("service_id","cost_id"),
        FOREIGN KEY ("service_id") REFERENCES "V3_SERVICE"("id") ON DELETE CASCADE,
        FOREIGN KEY ("cost_id") REFERENCES "V3_COSTS"("id") ON DELETE CASCADE);
    ''',
    '''
    DROP TABLE IF EXISTS "V3_SERVICE_TAXONOMY" CASCADE;
CREATE TABLE "V3_SERVICE_TAXONOMY" ("id" BIGSERIAL PRIMARY KEY,
    "service_id" INTEGER NOT NULL,
        "taxonomy_id" INTEGER NOT NULL,
        UNIQUE ("service_id","taxonomy_id"),
        FOREIGN KEY ("service_id") REFERENCES "V3_SERVICE"("id") ON DELETE CASCADE,
        FOREIGN KEY ("taxonomy_id") REFERENCES "V3_TAXONOMY"("id") ON DELETE CASCADE);
    ''',

    # --- Helpful indexes (optional) ---
    'CREATE INDEX IF NOT EXISTS "V3_service_idx_sort" ON "V3_SERVICE" ("sort_order","name");',
    'CREATE INDEX IF NOT EXISTS "V3_service_action_idx" ON "V3_SERVICE" ("action_id");',
    'CREATE INDEX IF NOT EXISTS "V3_service_type_idx" ON "V3_SERVICE" ("service_type_id");',
    'CREATE INDEX IF NOT EXISTS "V3_service_contact_service_idx" ON "V3_SERVICE_CONTACT" ("service_id");',
    'CREATE INDEX IF NOT EXISTS "V3_service_location_service_idx" ON "V3_SERVICE_LOCATION" ("service_id");',
]

class Command(BaseCommand):
    help = "Creates all V3_* tables (lookup, service, category, and through) if they do not exist."

    def handle(self, *args, **options):
        with transaction.atomic():
            with connection.cursor() as cur:
                for stmt in SQL:
                    cur.execute(stmt)
        self.stdout.write(self.style.SUCCESS("V3_* tables ensured."))
