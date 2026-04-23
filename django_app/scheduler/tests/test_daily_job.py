"""Tests for scheduler management commands."""

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase


class DailyJobCommandTests(TestCase):
    """Tests for the daily_job management command."""

    def test_daily_job_runs_without_error(self):
        """call_command('daily_job') executes without raising."""
        call_command("daily_job", stdout=StringIO())


class DailyJobClearSessionsTests(TestCase):
    """Tests that daily_job calls clearsessions."""

    @patch("scheduler.management.commands.daily_job.call_command")
    def test_daily_job_calls_clearsessions(self, mock_call_command):
        """daily_job invokes clearsessions management command."""
        call_command("daily_job", stdout=StringIO())
        mock_call_command.assert_any_call("clearsessions")
