from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth import get_user_model

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

from htsh.models import (
    Campaign,
    UserProfile,
    MagicLink,
    UserFilter,
)


class Command(BaseCommand):
    help = "Replace all V3_* data and htsh test data with deterministic test fixture data."

    # Test campaign code - must match the value in v3_testdata.json
    TEST_CAMPAIGN_CODE = "999999"

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-htsh-cleanup',
            action='store_true',
            help='Skip cleanup of test HTSH users (useful for debugging)',
        )

    def handle(self, *args, **options):
        User = get_user_model()
        skip_htsh_cleanup = options.get('skip_htsh_cleanup', False)

        # =====================================================================
        # 1) Clean up htsh test data
        # =====================================================================
        if not skip_htsh_cleanup:
            self.stdout.write("Cleaning up htsh test data...")
            
            # Delete test users created by E2E tests (identified by email pattern)
            # E2E tests create users with emails like: test_<timestamp>@example.com
            test_email_patterns = [
                'test_%@example.com',
                'signup_%@example.com',
                'auth_%@example.com',
                'sms_%@example.com',
                'updated_%@example.com',
                'account_%@example.com',
                'delete_%@example.com',
                'logout_%@example.com',
                'journey_%@example.com',
                'csrf_%@example.com',
                'dupe_%@example.com',
                'dupe1_%@example.com',
                'dupe2_%@example.com',
                'home_%@example.com',
                'fake_%@example.com',
                'nonexistent_%@example.com',
            ]
            
            # Delete UserProfiles and their associated users for test emails
            for pattern in test_email_patterns:
                # Get profiles matching the pattern
                profiles = UserProfile.objects.filter(email__regex=pattern.replace('%', '.*'))
                user_ids = list(profiles.values_list('user_id', flat=True))
                
                # Delete the profiles first (due to FK constraints)
                deleted_profiles = profiles.delete()[0]
                
                # Delete the associated users
                if user_ids:
                    deleted_users = User.objects.filter(id__in=user_ids).delete()[0]
                    if deleted_profiles > 0 or deleted_users > 0:
                        self.stdout.write(f"  Deleted {deleted_profiles} profiles and {deleted_users} users matching {pattern}")
            
            # Also clean up MagicLinks and UserFilters for deleted users
            # (should cascade, but just in case)
            orphan_links = MagicLink.objects.filter(user__isnull=True).delete()[0]
            orphan_filters = UserFilter.objects.filter(user__isnull=True).delete()[0]
            if orphan_links > 0 or orphan_filters > 0:
                self.stdout.write(f"  Cleaned up {orphan_links} orphan MagicLinks, {orphan_filters} orphan UserFilters")
            
            # Delete the test campaign if it exists (will be recreated by fixture)
            deleted_campaigns = Campaign.objects.filter(campaign_code=self.TEST_CAMPAIGN_CODE).delete()[0]
            if deleted_campaigns > 0:
                self.stdout.write(f"  Deleted {deleted_campaigns} test campaign(s)")

        # =====================================================================
        # 2) Delete V3_* through-tables first (FKs -> service / lookups)
        # =====================================================================
        self.stdout.write("Cleaning up V3_* data...")
        
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

        # =====================================================================
        # 3) Delete core entities + lookups
        # =====================================================================
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

        # =====================================================================
        # 4) Load the fixture (includes Campaign + V3_* data)
        # =====================================================================
        call_command("loaddata", "v3_testdata")

        self.stdout.write(
            self.style.SUCCESS(
                f"Loaded test data from api/fixtures/v3_testdata.json\n"
                f"Test campaign code: {self.TEST_CAMPAIGN_CODE}"
            )
        )
