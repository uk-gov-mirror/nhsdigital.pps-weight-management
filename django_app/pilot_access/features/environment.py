"""
Environment setup for BDD tests using behave.
Handles Django test database setup and teardown.
"""
import os
import sys
import django

# Ensure the Django app directory is in the path
django_app_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if django_app_path not in sys.path:
    sys.path.insert(0, django_app_path)

# Set Django settings module to use test settings
os.environ['DJANGO_SETTINGS_MODULE'] = 'wm_django.settings.test'

# Setup Django
django.setup()


def before_all(context):
    """Set up Django test environment before all tests."""
    from django.test.utils import setup_test_environment
    
    setup_test_environment()


def after_all(context):
    """Tear down Django test environment after all tests."""
    from django.test.utils import teardown_test_environment
    teardown_test_environment()


def before_scenario(context, scenario):
    """Set up test database and client before each scenario."""
    from django.test import Client
    from django.core.management import call_command
    
    # Run migrations to create tables in the test database
    try:
        call_command('migrate', verbosity=0, interactive=False)
    except Exception as e:
        # Migrations might fail if they're not properly set up, but that's OK for basic tests
        pass
    
    # Clear cache
    from django.core.cache import cache
    cache.clear()
    
    # Initialize client for the scenario
    context.client = Client()


def after_scenario(context, scenario):
    """Clean up test database after each scenario."""
    # Flush the database between scenarios to ensure clean state
    try:
        from django.core.management import call_command
        call_command('flush', verbosity=0, interactive=False)
    except Exception:
        pass
