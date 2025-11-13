from django.core.management.base import BaseCommand
from django.core.management import call_command

class Command(BaseCommand):
    help = (
        "Creates/updates and seeds V1_ and V2_ tables in order "
        "(V1 first, then V2)."
    )

    def handle(self, *args, **options):
        # --- V1 ---
        self.stdout.write(self.style.HTTP_INFO("Running V1_update_db..."))
        call_command("v1_update_db")
        self.stdout.write(self.style.SUCCESS("V1_update_db completed."))

        self.stdout.write(self.style.HTTP_INFO("Running V1_seed_data..."))
        try:
            call_command("v1_seed_data")
            self.stdout.write(self.style.SUCCESS("V1_seed_data completed."))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"V1_seed_data failed: {e}"))
            raise

        # --- V2 ---
        self.stdout.write(self.style.HTTP_INFO("Running V2_update_db..."))
        call_command("v2_update_db")
        self.stdout.write(self.style.SUCCESS("V2_update_db completed."))

        self.stdout.write(self.style.HTTP_INFO("Running V2_seed_data..."))
        try:
            call_command("v2_seed_data")
            self.stdout.write(self.style.SUCCESS("V2_seed_data completed."))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"V2_seed_data failed: {e}"))
            raise
        
        self.stdout.write(self.style.SUCCESS("All update and seed operations completed successfully."))
