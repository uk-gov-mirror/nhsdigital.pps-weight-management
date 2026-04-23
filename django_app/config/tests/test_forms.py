"""Unit tests for htsh forms with real validation logic."""

from django.test import TestCase

from htsh.forms import (
    EmailInputForm,
    OTPForm,
    PhoneInputForm,
)


class EmailInputFormTests(TestCase):

    def test_valid_email(self):
        form = EmailInputForm(data={"email": "user@example.com"})
        self.assertTrue(form.is_valid())

    def test_invalid_email(self):
        form = EmailInputForm(data={"email": "not-an-email"})
        self.assertFalse(form.is_valid())


class PhoneInputFormTests(TestCase):

    def test_valid_phone(self):
        form = PhoneInputForm(data={"phone": "07700900000"})
        self.assertTrue(form.is_valid())

    def test_invalid_phone(self):
        form = PhoneInputForm(data={"phone": "123"})
        self.assertFalse(form.is_valid())


class OTPFormTests(TestCase):
    databases = set()

    def test_valid_otp(self):
        form = OTPForm(data={"otp": "123456"})
        self.assertTrue(form.is_valid())

    def test_invalid_non_digit(self):
        form = OTPForm(data={"otp": "abcdef"})
        self.assertFalse(form.is_valid())
