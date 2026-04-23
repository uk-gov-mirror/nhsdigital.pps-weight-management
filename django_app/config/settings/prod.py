"""
Production Django settings.

These override base.py with security-focused defaults.
"""

from .base import *  # noqa
DEBUG = False

ENV_NAME = "Production"