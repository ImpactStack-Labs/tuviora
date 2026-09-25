"""Tests for the MarzPay payment service."""

import hashlib
import hmac
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from apps.events.services.marzpay_service import (
    MarzPayError,
    get_transaction,
    initiate_collection,
    verify_webhook_signature,
)


@override_settings(
    MARZPAY_BASE_URL="https://wallet.wearemarz.com/api/v1",
    MARZPAY_API_KEY="test-key",
    MARZPAY_API_SECRET="test-secret",
    MARZPAY_DEFAULT_COUNTRY="UG",
)
class MarzPayCollectionTests(SimpleTestCase):
    @patch("apps.events.services.marzpay_service.requests")
    def test_initiate_mobile_money_collection(self, mock_requests):
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {
            "status": "success",
            "message": "Collection initiated successfully.",
            "data": {
                "transaction": {
                    "uuid": "4e7fb3fa-c13a-4b05-8acd-cf60ff68cb94",
                    "reference": "ref-123",
                    "status": "processing",
                },
                "collection": {"provider": "mtn"},
            },
        }
        mock_requests.post.return_value = mock_response

        result = initiate_collection(
            amount="1000",
            currency="UGX",
            reference="ref-123",
            method="mobile_money",
            phone_number="+256700000000",
        )

        self.assertEqual(
            result["transaction"]["status"], "processing"
        )

        _, kwargs = mock_requests.post.call_args
        self.assertEqual(
            kwargs["headers"]["Authorization"],
            "Basic dGVzdC1rZXk6dGVzdC1zZWNyZXQ=",
        )
        sent_fields = {k: v[1] for k, v in kwargs["files"].items()}
        self.assertEqual(sent_fields["phone_number"], "+256700000000")
        self.assertEqual(sent_fields["country"], "UG")

    @patch("apps.events.services.marzpay_service.requests")
    def test_mobile_money_requires_phone_number(self, mock_requests):
        with self.assertRaises(MarzPayError):
            initiate_collection(
                amount="1000",
                currency="UGX",
                reference="ref-124",
                method="mobile_money",
            )
        mock_requests.post.assert_not_called()

    @patch("apps.events.services.marzpay_service.requests")
    def test_provider_error_raises_marzpay_error(self, mock_requests):
        mock_response = Mock(status_code=400)
        mock_response.json.return_value = {
            "status": "error",
            "message": "Insufficient collection limit.",
        }
        mock_requests.post.return_value = mock_response

        with self.assertRaises(MarzPayError):
            initiate_collection(
                amount="1000",
                currency="UGX",
                reference="ref-125",
                method="mobile_money",
                phone_number="+256700000000",
            )

    @patch("apps.events.services.marzpay_service.requests")
    def test_network_failure_raises_marzpay_error(self, mock_requests):
        import requests as real_requests

        mock_requests.RequestException = real_requests.RequestException
        mock_requests.post.side_effect = real_requests.RequestException(
            "boom"
        )

        with self.assertRaises(MarzPayError):
            initiate_collection(
                amount="1000",
                currency="UGX",
                reference="ref-126",
                method="mobile_money",
                phone_number="+256700000000",
            )

    @patch("apps.events.services.marzpay_service.requests")
    def test_get_transaction(self, mock_requests):
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {"transaction": {"status": "completed"}}
        mock_requests.get.return_value = mock_response

        result = get_transaction("ref-123")

        self.assertEqual(result["transaction"]["status"], "completed")
        mock_requests.get.assert_called_once()


class MarzPayWebhookSignatureTests(SimpleTestCase):
    def test_valid_signature_is_accepted(self):
        secret = "webhook-secret"
        timestamp = "1700000000"
        body = b'{"event_type":"collection.completed"}'
        digest = hmac.new(
            secret.encode(),
            f"{timestamp}.".encode() + body,
            hashlib.sha256,
        ).hexdigest()

        self.assertTrue(
            verify_webhook_signature(
                body, timestamp, f"t={timestamp},v1={digest}", secret
            )
        )

    def test_tampered_signature_is_rejected(self):
        self.assertFalse(
            verify_webhook_signature(
                b'{"event_type":"collection.completed"}',
                "1700000000",
                "t=1700000000,v1=deadbeef",
                "webhook-secret",
            )
        )

    def test_missing_secret_is_rejected(self):
        self.assertFalse(
            verify_webhook_signature(
                b"{}", "1700000000", "t=1700000000,v1=abc", ""
            )
        )

    def test_malformed_signature_with_non_ascii_returns_false(self):
        # Regression test: ensure non-ASCII characters in v1 signature
        # return False instead of raising TypeError
        self.assertFalse(
            verify_webhook_signature(
                b'{"event_type":"collection.completed"}',
                "1700000000",
                "t=1700000000,v1=💥",
                "webhook-secret",
            )
        )
