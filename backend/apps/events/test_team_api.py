import hashlib

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Event, EventInvitation, EventMembership


@override_settings(
    MAILERS={
        "default": {
            "BACKEND": "django.core.mail.backends.locmem.EmailBackend",
        }
    },
    FRONTEND_BASE_URL="http://localhost:5173",
)
class EventTeamAPITests(APITestCase):
    def setUp(self):
        User = get_user_model()

        self.organizer = User.objects.create_user(
            username="team_organizer",
            email="organizer@example.com",
            password="TestPassword123!",
        )

        self.other_user = User.objects.create_user(
            username="other_organizer",
            email="other@example.com",
            password="TestPassword123!",
        )

        self.event = Event.objects.create(
            organizer=self.organizer,
            name="Tuviora Demo Event",
            category=Event.Category.HACKATHON,
            date=timezone.localdate() + timezone.timedelta(days=7),
            start_time="09:00",
            end_time="17:00",
            event_format=Event.EventFormat.PHYSICAL,
            venue="Kampala",
        )

        self.team_url = f"/api/events/{self.event.id}/team/"
        self.invitation_url = (
            f"/api/events/{self.event.id}/invitations/"
        )

        self.client.force_authenticate(user=self.organizer)

    def invite(self, email="member@example.com", role="member"):
        return self.client.post(
            self.invitation_url,
            {"email": email, "role": role},
            format="json",
        )

    def test_organizer_can_view_event_team(self):
        response = self.client.get(self.team_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["role"], "organizer")
        self.assertEqual(
            response.data[0]["user_id"],
            self.organizer.id,
        )

    def test_organizer_can_create_invitation(self):
        response = self.invite()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        invitation = EventInvitation.objects.get()

        self.assertEqual(invitation.email, "member@example.com")
        self.assertEqual(invitation.role, "member")
        self.assertEqual(invitation.event, self.event)
        self.assertGreater(
            invitation.expires_at,
            timezone.now(),
        )

        token = response.data["invitation_token"]

        self.assertEqual(
            invitation.token_hash,
            hashlib.sha256(token.encode()).hexdigest(),
        )
        self.assertNotEqual(invitation.token_hash, token)

    def test_creating_invitation_sends_email(self):
        response = self.invite(
            email="teammate@example.com",
            role="manager",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(mail.outbox), 1)

        message = mail.outbox[0]

        self.assertEqual(message.to, ["teammate@example.com"])
        self.assertEqual(message.from_email, settings.DEFAULT_FROM_EMAIL)
        self.assertIn(self.event.name, message.subject)
        self.assertIn("manager", message.body.lower())

        expected_link = (
            "http://localhost:5173/invite#token="
            + response.data["invitation_token"]
        )

        self.assertIn(expected_link, message.body)

    def test_duplicate_active_invitation_is_rejected(self):
        self.assertEqual(
            self.invite().status_code,
            status.HTTP_201_CREATED,
        )

        response = self.invite(email="MEMBER@example.com")

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(EventInvitation.objects.count(), 1)

    def test_invitation_listing_never_exposes_token(self):
        create_response = self.invite()
        token = create_response.data["invitation_token"]

        response = self.client.get(self.invitation_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertNotIn("invitation_token", response.data[0])
        self.assertNotIn("token_hash", response.data[0])
        self.assertNotIn(token, str(response.data))

    def test_organizer_cannot_invite_themselves(self):
        response = self.invite(
            email="organizer@example.com",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_organizer_can_revoke_invitation(self):
        invitation_id = self.invite().data["id"]

        response = self.client.post(
            f"/api/events/{self.event.id}/"
            f"invitations/{invitation_id}/revoke/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        invitation = EventInvitation.objects.get(
            id=invitation_id,
        )
        self.assertIsNotNone(invitation.revoked_at)

    def test_revoked_email_can_be_invited_again(self):
        invitation_id = self.invite().data["id"]

        self.client.post(
            f"/api/events/{self.event.id}/"
            f"invitations/{invitation_id}/revoke/",
            {},
            format="json",
        )

        response = self.invite()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(EventInvitation.objects.count(), 2)

    def test_other_user_cannot_view_team(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.get(self.team_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_other_user_cannot_create_invitation(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.invite()

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertFalse(EventInvitation.objects.exists())

    def test_other_user_cannot_revoke_invitation(self):
        invitation_id = self.invite().data["id"]

        self.client.force_authenticate(user=self.other_user)

        response = self.client.post(
            f"/api/events/{self.event.id}/"
            f"invitations/{invitation_id}/revoke/",
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        invitation = EventInvitation.objects.get(
            id=invitation_id,
        )
        self.assertIsNone(invitation.revoked_at)

    def test_unauthenticated_user_cannot_view_team(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.team_url)

        self.assertIn(
            response.status_code,
            [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            ],
        )

    def test_invalid_role_is_rejected(self):
        response = self.invite(role="organizer")

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )


class InvitationAcceptanceTests(APITestCase):
    def setUp(self):
        User = get_user_model()

        self.organizer = User.objects.create_user(
            username="accept_organizer",
            email="accept-organizer@example.com",
            password="TestPassword123!",
        )

        self.member = User.objects.create_user(
            username="accept_member",
            email="accept-member@example.com",
            password="TestPassword123!",
        )

        self.other_user = User.objects.create_user(
            username="accept_other",
            email="someone-else@example.com",
            password="TestPassword123!",
        )

        self.event = Event.objects.create(
            organizer=self.organizer,
            name="Invitation Acceptance Demo",
            category=Event.Category.HACKATHON,
            date=timezone.localdate() + timezone.timedelta(days=7),
            start_time="09:00",
            end_time="17:00",
            event_format=Event.EventFormat.PHYSICAL,
            venue="Kampala",
        )

        self.token = "test-invitation-token-123"

        self.invitation = EventInvitation.objects.create(
            event=self.event,
            email=self.member.email,
            role=EventInvitation.Role.MEMBER,
            token_hash=hashlib.sha256(
                self.token.encode("utf-8")
            ).hexdigest(),
            invited_by=self.organizer,
            expires_at=timezone.now() + timezone.timedelta(days=7),
        )

        self.url = "/api/events/invitations/accept/"
        self.client.force_authenticate(user=self.member)

    def accept(self, token=None):
        return self.client.post(
            self.url,
            {"token": self.token if token is None else token},
            format="json",
        )

    def test_valid_invitation_creates_membership(self):
        response = self.accept()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["role"], "member")

        membership = EventMembership.objects.get(
            event=self.event,
            user=self.member,
        )
        self.assertEqual(membership.role, "member")

        self.invitation.refresh_from_db()
        self.assertIsNotNone(self.invitation.accepted_at)

    def test_invitation_cannot_be_used_twice(self):
        self.assertEqual(
            self.accept().status_code,
            status.HTTP_200_OK,
        )

        response = self.accept()

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(EventMembership.objects.count(), 1)

    def test_expired_invitation_is_rejected(self):
        self.invitation.expires_at = (
            timezone.now() - timezone.timedelta(minutes=1)
        )
        self.invitation.save(update_fields=["expires_at"])

        response = self.accept()

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertFalse(EventMembership.objects.exists())

    def test_revoked_invitation_is_rejected(self):
        self.invitation.revoked_at = timezone.now()
        self.invitation.save(update_fields=["revoked_at"])

        response = self.accept()

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertFalse(EventMembership.objects.exists())

    def test_invalid_token_is_rejected(self):
        response = self.accept(token="not-a-real-token")

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertFalse(EventMembership.objects.exists())

    def test_wrong_account_email_is_rejected(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.accept()

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertFalse(EventMembership.objects.exists())

    def test_unauthenticated_acceptance_is_rejected(self):
        self.client.force_authenticate(user=None)

        response = self.accept()

        self.assertIn(
            response.status_code,
            [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            ],
        )
        self.assertFalse(EventMembership.objects.exists())

    def test_existing_member_cannot_accept_again(self):
        EventMembership.objects.create(
            event=self.event,
            user=self.member,
            role=EventMembership.Role.MEMBER,
        )

        response = self.accept()

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.invitation.refresh_from_db()
        self.assertIsNone(self.invitation.accepted_at)
        self.assertEqual(EventMembership.objects.count(), 1)
