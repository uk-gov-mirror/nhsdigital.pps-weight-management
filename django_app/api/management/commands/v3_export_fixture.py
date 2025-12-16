# api/management/commands/v3_export_fixture.py
#
# Usage: python manage.py v3_export_fixture
#      
# Usage Local Docker Desktopn:       
#      docker compose -f local/docker-compose.local.yml exec web python manage.py v3_export_fixture --output /tmp/v3_seed.json
#      docker compose -f local/docker-compose.local.yml cp web:/tmp/v3_seed.json ./api/fixtures/v3_seed.json

from pathlib import Path

from django.core.management.base import BaseCommand
from django.core import serializers

from api.models_v3 import (
    V3_ActionType,
    V3_ServiceType,
    V3_HelpsWith,
    V3_WhoFor,
    V3_WhoNotFor,
    V3_Mitigations,
    V3_TimeRequired,
    V3_Access,
    V3_Costs,
    V3_Taxonomy,
    V3_Category,
    V3_Service,
    V3_Contact,
    V3_Location,
    V3_Service_Category,
    V3_Service_HelpsWith,
    V3_Service_WhoFor,
    V3_Service_WhoNotFor,
    V3_Service_Mitigation,
    V3_Service_TimeRequired,
    V3_Service_Access,
    V3_Service_Cost,
    V3_Service_Taxonomy,
    V3_Service_Contact,
    V3_Service_Location,
)


class Command(BaseCommand):
    help = "Export ALL V3_* data to a JSON fixture suitable for loaddata."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            "-o",
            dest="output",
            default="api/fixtures/v3_seed.json",
            help="Path to write the JSON fixture (default: api/fixtures/v3_seed.json)",
        )

    def handle(self, *args, **options):
        output_path = Path(options["output"])
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Order: lookups first, then core entities, then through tables.
        model_order = [
            # Lookup tables
            V3_ActionType,
            V3_ServiceType,
            V3_HelpsWith,
            V3_WhoFor,
            V3_WhoNotFor,
            V3_Mitigations,
            V3_TimeRequired,
            V3_Access,
            V3_Costs,
            V3_Taxonomy,
            V3_Category,
            # Core entities
            V3_Contact,
            V3_Location,
            V3_Service,
            # Through tables
            V3_Service_Category,
            V3_Service_HelpsWith,
            V3_Service_WhoFor,
            V3_Service_WhoNotFor,
            V3_Service_Mitigation,
            V3_Service_TimeRequired,
            V3_Service_Access,
            V3_Service_Cost,
            V3_Service_Taxonomy,
            V3_Service_Contact,
            V3_Service_Location,
        ]

        all_objects = []
        for model in model_order:
            qs = model.objects.all().order_by("id")
            all_objects.extend(qs)

        self.stdout.write(
            f"Exporting {len(all_objects)} objects from all V3_* tables to {output_path}..."
        )

        data = serializers.serialize("json", all_objects)

        output_path.write_text(data, encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Wrote V3 fixture to {output_path}"))
