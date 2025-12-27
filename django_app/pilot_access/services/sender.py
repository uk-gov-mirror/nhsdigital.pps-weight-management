import logging
from dataclasses import dataclass

from django.conf import settings

logger = logging.getLogger(__name__)


class EmailSender:
    """
    Interface for sending pilot emails.
    """
    def send_invite(self, *, email: str, link_or_code: str) -> None:
        raise NotImplementedError

    def send_magic_link(self, email: str, link: str) -> None:
        raise NotImplementedError


class SmsSender:
    """
    Interface for sending pilot SMS messages.
    """
    def send_invite(self, *, phone: str, link_or_code: str) -> None:
        raise NotImplementedError


@dataclass(frozen=True)
class MockEmailSender(EmailSender):
    """
    Mock implementation: logs instead of sending.
    """
    def send_invite(self, *, email: str, link_or_code: str) -> None:
        logger.info("[MOCK EMAIL] To=%s Invite=%s", email, link_or_code)

    def send_magic_link(self, email: str, link: str) -> None:
        logger.info("[MOCK EMAIL] To=%s MagicLink=%s", email, link)


@dataclass(frozen=True)
class MockSmsSender(SmsSender):
    """
    Mock implementation: logs instead of sending.
    """
    def send_invite(self, *, phone: str, link_or_code: str) -> None:
        logger.info("[MOCK SMS] To=%s Invite=%s", phone, link_or_code)


def get_email_sender() -> EmailSender:
    """
    Factory so we can switch to a real sender later via settings.
    For now defaults to mock.
    """
    path = getattr(settings, "PILOT_ACCESS_EMAIL_SENDER", "")
    if not path:
        return MockEmailSender()

    # Optional: allow swapping by dotted path later
    module_path, class_name = path.rsplit(".", 1)
    mod = __import__(module_path, fromlist=[class_name])
    cls = getattr(mod, class_name)
    return cls()


def get_sms_sender() -> SmsSender:
    """
    Factory so we can switch to a real sender later via settings.
    For now defaults to mock.
    """
    path = getattr(settings, "PILOT_ACCESS_SMS_SENDER", "")
    if not path:
        return MockSmsSender()

    module_path, class_name = path.rsplit(".", 1)
    mod = __import__(module_path, fromlist=[class_name])
    cls = getattr(mod, class_name)
    return cls()
