"""Custom test runner that enables SQLite table creation for unmanaged models."""

from django.apps import apps
from django.test.runner import DiscoverRunner


class UnmanagedModelTestRunner(DiscoverRunner):
    """Test runner that sets managed=True on all unmanaged models before DB creation."""

    def setup_databases(self, **kwargs):
        for model in apps.get_models():
            if not model._meta.managed:
                model._meta.managed = True
        return super().setup_databases(**kwargs)
