"""Tests for scheduler management commands."""

from io import StringIO

from django.core.management import call_command
from django.test import TestCase


class DailyJobCommandTests(TestCase):
    """Tests for the daily_job management command."""

    def test_daily_job_runs_without_error(self):
        """call_command('daily_job') executes without raising."""
        call_command("daily_job", stdout=StringIO())
