from django.core.management.base import BaseCommand
import datetime
import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Runs the daily job. This is the entrypoint invoked by the ECS scheduled task."

    def handle(self, *args, **options):
        now = datetime.datetime.utcnow().isoformat()
        message = f"[daily_job] Ran at {now} UTC"
        print(message)
        logger.info(message)
