import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.sms.services.event_sms_notifications import send_team_sms

from .models import Event, EventInvitation, EventMembership
from .views import task_access_for_user


class InvitationCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(
        choices=EventInvitation.Role.choices,
    )


class TeamMessageSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=480, trim_whitespace=True)


class EventTeamView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, event_id):
        event = get_object_or_404(
            Event,
            pk=event_id,
            organizer=request.user,
        )

        memberships = (
            EventMembership.objects
            .filter(event=event)
            .select_related("user")
        )

        members = [
            {
                "user_id": event.organizer_id,
                "username": event.organizer.username,
                "email": event.organizer.email,
                "role": "organizer",
            }
        ]

        members.extend(
            {
                "user_id": membership.user_id,
                "username": membership.user.username,
                "email": membership.user.email,
                "role": membership.role,
                "joined_at": membership.joined_at,
            }
            for membership in memberships
        )

        return Response(members)


class EventInvitationView(APIView):
    permission_classes = [IsAuthenticated]

    def get_event(self, request, event_id):
        return get_object_or_404(
            Event,
            pk=event_id,
            organizer=request.user,
        )

    def get(self, request, event_id):
        event = self.get_event(request, event_id)

        invitations = EventInvitation.objects.filter(event=event)

        return Response([
            {
                "id": invitation.id,
                "email": invitation.email,
                "role": invitation.role,
                "expires_at": invitation.expires_at,
                "accepted_at": invitation.accepted_at,
                "revoked_at": invitation.revoked_at,
                "created_at": invitation.created_at,
            }
            for invitation in invitations
        ])

    @transaction.atomic
    def post(self, request, event_id):
        event = self.get_event(request, event_id)

        serializer = InvitationCreateSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"].strip().lower()
        role = serializer.validated_data["role"]

        if email == event.organizer.email.strip().lower():
            return Response(
                {"email": ["The organizer already owns this event."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if EventMembership.objects.filter(
            event=event,
            user__email__iexact=email,
        ).exists():
            return Response(
                {"email": ["This person is already on the event team."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if EventInvitation.objects.filter(
            event=event,
            email__iexact=email,
            accepted_at__isnull=True,
            revoked_at__isnull=True,
            expires_at__gt=timezone.now(),
        ).exists():
            return Response(
                {"email": ["An active invitation already exists."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token = secrets.token_urlsafe(32)

        invitation = EventInvitation.objects.create(
            event=event,
            email=email,
            role=role,
            token_hash=hashlib.sha256(
                token.encode("utf-8")
            ).hexdigest(),
            invited_by=request.user,
            expires_at=timezone.now() + timedelta(days=7),
        )

        invitation_url = (
            f"{settings.FRONTEND_BASE_URL.rstrip('/')}"
            f"/invite#token={token}"
        )

        organizer_name = (
            request.user.get_full_name()
            or request.user.username
        )

        try:
            send_mail(
                subject=f"You're invited to {event.name} on Tuviora",
                message=(
                    f"Hello!\n\n"
                    f"{organizer_name} has invited you to help manage "
                    f"{event.name} on Tuviora.\n\n"
                    f"Your role: {invitation.get_role_display()}\n\n"
                    f"Accept your invitation here:\n"
                    f"{invitation_url}\n\n"
                    f"This invitation expires in seven days. "
                    f"If you do not have an account, register using "
                    f"the email address that received this message.\n\n"
                    f"Tuviora Team"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[invitation.email],
                fail_silently=False,
            )
        except Exception:
            # Roll back invitation creation so the organizer can retry.
            transaction.set_rollback(True)
            return Response(
                {
                    "detail": (
                        "The invitation email could not be sent. "
                        "Please try again."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Returned once so the organizer can privately share the link.
        # Never include tokens in the invitation listing.
        return Response(
            {
                "id": invitation.id,
                "email": invitation.email,
                "role": invitation.role,
                "expires_at": invitation.expires_at,
                "invitation_token": token,
            },
            status=status.HTTP_201_CREATED,
        )


class EventInvitationRevokeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, event_id, invitation_id):
        invitation = get_object_or_404(
            EventInvitation,
            pk=invitation_id,
            event_id=event_id,
            event__organizer=request.user,
        )

        if invitation.accepted_at is not None:
            return Response(
                {"detail": "Accepted invitations cannot be revoked."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if invitation.revoked_at is not None:
            return Response(
                {"detail": "Invitation already revoked."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        invitation.revoked_at = timezone.now()
        invitation.save(update_fields=["revoked_at"])

        return Response({"detail": "Invitation revoked."})


class InvitationAcceptView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        token = request.data.get("token", "")

        if not isinstance(token, str) or not token:
            return Response(
                {"token": ["An invitation token is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(token) > 256:
            return Response(
                {"detail": "Invalid invitation."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token_hash = hashlib.sha256(
            token.encode("utf-8")
        ).hexdigest()

        invitation = (
            EventInvitation.objects
            .select_for_update()
            .filter(token_hash=token_hash)
            .first()
        )

        if invitation is None:
            return Response(
                {"detail": "Invalid invitation."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if invitation.revoked_at is not None:
            return Response(
                {"detail": "This invitation has been revoked."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if invitation.accepted_at is not None:
            return Response(
                {"detail": "This invitation has already been used."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if invitation.expires_at <= timezone.now():
            return Response(
                {"detail": "This invitation has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        account_email = (request.user.email or "").strip().lower()

        if not account_email or account_email != invitation.email.lower():
            return Response(
                {
                    "detail": (
                        "Sign in with the email address "
                        "this invitation was sent to."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if invitation.event.organizer_id == request.user.pk:
            return Response(
                {"detail": "You already organize this event."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        membership, created = EventMembership.objects.get_or_create(
            event=invitation.event,
            user=request.user,
            defaults={"role": invitation.role},
        )

        if not created:
            return Response(
                {"detail": "You are already a member of this event."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        invitation.accepted_at = timezone.now()
        invitation.save(update_fields=["accepted_at"])

        return Response(
            {
                "detail": "Invitation accepted.",
                "event_id": invitation.event_id,
                "event_name": invitation.event.name,
                "role": membership.role,
                "membership_id": membership.id,
            },
            status=status.HTTP_200_OK,
        )


class MessageTeamView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, event_id):
        event = get_object_or_404(Event, pk=event_id)
        role = task_access_for_user(event, request.user)

        if role is None:
            raise Http404

        if role not in ("organizer", EventMembership.Role.MANAGER):
            return Response(
                {
                    "detail": (
                        "Only the organizer or event managers "
                        "can message the team."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = TeamMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.validated_data["message"]

        return Response(send_team_sms(event, message))
