import datetime
import logging

from django.core.management import call_command
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Runs the daily job. This is the entrypoint invoked by the ECS scheduled task."

    def handle(self, *args, **options):
        now = datetime.datetime.utcnow().isoformat()
        message = f"[daily_job] Ran at {now} UTC"
        print(message)
        logger.info(message)

        # Clear expired sessions to prevent django_session table bloat (MID-04)
        call_command("clearsessions")
        logger.info("[daily_job] Cleared expired sessions")
