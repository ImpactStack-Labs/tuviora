"""Tests for SMS preferences during account registration."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import SMSPreference


@override_settings(
    MAILERS={
        "default": {
            "BACKEND": "django.core.mail.backends.locmem.EmailBackend",
        }
    },
    DEFAULT_FROM_EMAIL="Tuviora <test@example.com>",
    FRONTEND_BASE_URL="http://localhost:5173",
)
class RegistrationSMSTests(TestCase):
    def setUp(self):
        self.url = reverse("auth-register")
        self.payload = {
            "first_name": "Grace",
            "last_name": "Demo",
            "username": "grace_sms",
            "email": "gracesms@example.com",
            "password": "StrongDemoPassword2026!",
            "confirm_password": "StrongDemoPassword2026!",
        }

    def register(self, **changes):
        return self.client.post(
            self.url,
            {**self.payload, **changes},
            content_type="application/json",
        )

    def test_registration_without_phone_remains_supported(self):
        response = self.register()

        self.assertEqual(response.status_code, 201)
        self.assertFalse(SMSPreference.objects.exists())

    def test_phone_without_consent_is_saved_but_not_subscribed(self):
        response = self.register(
            phone_number="+256700123456",
            sms_enabled=False,
        )

        self.assertEqual(response.status_code, 201)

        preference = SMSPreference.objects.get(
            user__username="grace_sms"
        )

        self.assertEqual(
            preference.phone_number,
            "+256700123456",
        )
        self.assertFalse(preference.sms_enabled)

    @patch("apps.accounts.views.send_registration_sms")
    def test_opted_in_registration_sends_sms_after_commit(
        self,
        mock_send,
    ):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.register(
                phone_number="+256700123456",
                sms_enabled=True,
            )

        self.assertEqual(response.status_code, 201)

        preference = SMSPreference.objects.get(
            user__username="grace_sms"
        )
        self.assertTrue(preference.sms_enabled)

        mock_send.assert_called_once_with(
            "+256700123456",
            "Grace",
        )

    @patch("apps.accounts.views.send_registration_sms")
    def test_registration_without_consent_does_not_send_sms(
        self,
        mock_send,
    ):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.register(
                phone_number="+256700123456",
                sms_enabled=False,
            )

        self.assertEqual(response.status_code, 201)
        mock_send.assert_not_called()

    def test_invalid_phone_is_rejected(self):
        response = self.register(
            phone_number="0700123456",
            sms_enabled=True,
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("phone_number", response.json())
        self.assertFalse(get_user_model().objects.exists())

    def test_consent_requires_phone_number(self):
        response = self.register(sms_enabled=True)

        self.assertEqual(response.status_code, 400)
        self.assertIn("phone_number", response.json())
        self.assertFalse(get_user_model().objects.exists())

    def test_consent_must_be_boolean(self):
        response = self.register(
            phone_number="+256700123456",
            sms_enabled="true",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("sms_enabled", response.json())

    @patch(
        "apps.accounts.views.send_sms",
        side_effect=ConnectionError("Simulated failure"),
    )
    def test_registration_survives_provider_failure(
        self,
        mock_send,
    ):
        # Test the actual registration wrapper with a provider
        # failure type that the SMS service normally converts.
        from apps.accounts.views import send_registration_sms
        from apps.events.services.sms_service import SMSServiceError

        mock_send.side_effect = SMSServiceError(
            "Simulated provider failure"
        )

        with self.captureOnCommitCallbacks(execute=True):
            response = self.register(
                phone_number="+256700123456",
                sms_enabled=True,
            )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            get_user_model().objects.filter(
                username="grace_sms",
                is_active=False,
            ).exists()
        )
