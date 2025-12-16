from django.core.management.base import BaseCommand
from django.core.management import call_command

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
    V3_Contact,
    V3_Location,
    V3_Service,
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
    help = "Replace all V3_* data with deterministic test fixture data."

    def handle(self, *args, **options):
        # 1) Delete through-tables first (FKs -> service / lookups)
        through_models = [
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

        for model in through_models:
            model.objects.all().delete()

        # 2) Delete core entities + lookups
        core_models = [
            V3_Service,
            V3_Contact,
            V3_Location,
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
        ]

        for model in core_models:
            model.objects.all().delete()

        # 3) Load the fixture
        call_command("loaddata", "v3_testdata")

        self.stdout.write(
            self.style.SUCCESS("Loaded V3_* test data from api/fixtures/v3_testdata.json")
        )
