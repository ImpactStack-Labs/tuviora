import hashlib
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import EmailVerification


@override_settings(
    MAILERS={
        "default": {
            "BACKEND": "django.core.mail.backends.locmem.EmailBackend",
        }
    },
    DEFAULT_FROM_EMAIL="Tuviora <test@example.com>",
    FRONTEND_BASE_URL="http://localhost:5173",
)
class RegistrationTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.register_url = reverse("auth-register")
        self.verify_url = reverse("auth-verify-email")
        self.payload = {
            "first_name": "Grace",
            "last_name": "Demo",
            "username": "grace_demo",
            "email": "grace@example.com",
            "password": "StrongDemoPassword2026!",
            "confirm_password": "StrongDemoPassword2026!",
        }

    def register(self, **changes):
        return self.client.post(
            self.register_url,
            {**self.payload, **changes},
            content_type="application/json",
        )

    def verification_token(self):
        message = mail.outbox[-1].body
        return message.split("#token=", 1)[1].split()[0]

    def test_registration_creates_inactive_account(self):
        response = self.register()

        self.assertEqual(response.status_code, 201)

        user = self.User.objects.get(username="grace_demo")
        self.assertFalse(user.is_active)
        self.assertTrue(
            user.check_password("StrongDemoPassword2026!")
        )
        self.assertEqual(user.email, "grace@example.com")

    def test_registration_sends_verification_email(self):
        response = self.register()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].to,
            ["grace@example.com"],
        )
        self.assertIn("/verify-email#token=", mail.outbox[0].body)

    def test_duplicate_email_is_rejected(self):
        self.assertEqual(self.register().status_code, 201)

        response = self.register(
            username="another_user",
            email="GRACE@example.com",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.User.objects.count(), 1)

    def test_duplicate_username_is_rejected(self):
        self.assertEqual(self.register().status_code, 201)

        response = self.register(
            email="another@example.com",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.User.objects.count(), 1)

    def test_password_mismatch_is_rejected(self):
        response = self.register(
            confirm_password="DifferentPassword2026!",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.User.objects.exists())

    def test_weak_password_is_rejected(self):
        response = self.register(
            password="123",
            confirm_password="123",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.User.objects.exists())

    def test_unverified_user_cannot_sign_in(self):
        self.register()

        response = self.client.post(
            reverse("auth-login"),
            {
                "username": "grace_demo",
                "password": "StrongDemoPassword2026!",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("verify your email", response.json()["detail"])

        wrong = self.client.post(
            reverse("auth-login"),
            {"username": "grace_demo", "password": "wrong"},
            content_type="application/json",
        )
        self.assertEqual(
            wrong.json()["detail"], "Invalid username or password.",
        )

    def test_valid_verification_activates_account(self):
        self.register()
        token = self.verification_token()

        response = self.client.post(
            self.verify_url,
            {"token": token},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)

        user = self.User.objects.get(username="grace_demo")
        self.assertTrue(user.is_active)

        verification = EmailVerification.objects.get(user=user)
        self.assertIsNotNone(verification.verified_at)

    def test_verification_token_is_hashed_in_database(self):
        self.register()
        token = self.verification_token()

        verification = EmailVerification.objects.get(
            user__username="grace_demo",
        )

        self.assertNotEqual(verification.token_hash, token)
        self.assertEqual(
            verification.token_hash,
            hashlib.sha256(token.encode()).hexdigest(),
        )

    def test_verification_token_cannot_be_reused(self):
        self.register()
        token = self.verification_token()

        first = self.client.post(
            self.verify_url,
            {"token": token},
            content_type="application/json",
        )
        second = self.client.post(
            self.verify_url,
            {"token": token},
            content_type="application/json",
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 400)

    def test_expired_verification_is_rejected(self):
        self.register()
        token = self.verification_token()

        verification = EmailVerification.objects.get(
            user__username="grace_demo",
        )
        verification.expires_at = timezone.now() - timedelta(minutes=1)
        verification.save(update_fields=["expires_at"])

        response = self.client.post(
            self.verify_url,
            {"token": token},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

        user = self.User.objects.get(username="grace_demo")
        self.assertFalse(user.is_active)

    def test_invalid_verification_token_is_rejected(self):
        response = self.client.post(
            self.verify_url,
            {"token": "invalid-token"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
