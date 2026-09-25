import hashlib
import json
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import EmailVerification
from apps.sms.models import SMSPreference
from apps.sms.services.sms_service import (
    SMSServiceError,
    send_sms,
    validate_phone_number,
)

logger = logging.getLogger(__name__)


def send_registration_sms(phone_number, first_name):
    """Send a welcome message without disrupting registration."""
    try:
        send_sms(
            phone_number,
            (
                f"Welcome to Tuviora, {first_name}! "
                "Please check your email to verify your account."
            ),
        )
    except (SMSServiceError, ValueError):
        logger.warning(
            "Registration SMS could not be submitted.",
            exc_info=True,
        )



def parse_json(request):
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        return None

    return data if isinstance(data, dict) else None


@require_POST
def register(request):
    data = parse_json(request)

    if data is None:
        return JsonResponse(
            {"detail": "A valid JSON object is required."},
            status=400,
        )

    first_name = str(data.get("first_name", "")).strip()
    last_name = str(data.get("last_name", "")).strip()
    username = str(data.get("username", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = data.get("password", "")
    confirm_password = data.get("confirm_password", "")
    phone_number = data.get("phone_number", "")
    sms_enabled = data.get("sms_enabled", False)

    errors = {}

    if not isinstance(sms_enabled, bool):
        errors["sms_enabled"] = [
            "SMS preference must be true or false."
        ]

    if not isinstance(phone_number, str):
        errors["phone_number"] = [
            "Enter a valid international phone number."
        ]
        phone_number = ""
    elif phone_number.strip():
        try:
            phone_number = validate_phone_number(phone_number)
        except ValueError as exc:
            errors["phone_number"] = [str(exc)]
    else:
        phone_number = ""

    if sms_enabled is True and not phone_number:
        errors["phone_number"] = [
            "A phone number is required to enable SMS."
        ]

    if not first_name:
        errors["first_name"] = ["First name is required."]

    if not last_name:
        errors["last_name"] = ["Last name is required."]

    if not username:
        errors["username"] = ["Username is required."]

    if not email:
        errors["email"] = ["Email address is required."]
    else:
        try:
            validate_email(email)
        except ValidationError:
            errors["email"] = ["Enter a valid email address."]

    if not isinstance(password, str):
        errors["password"] = ["A valid password is required."]
    elif password != confirm_password:
        errors["confirm_password"] = ["Passwords do not match."]

    User = get_user_model()

    if username and User.objects.filter(
        username__iexact=username
    ).exists():
        errors["username"] = ["This username is already taken."]

    if email and User.objects.filter(
        email__iexact=email
    ).exists():
        errors["email"] = ["This email address is already registered."]

    if isinstance(password, str) and password:
        candidate = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
        )

        try:
            validate_password(password, user=candidate)
        except ValidationError as exc:
            errors["password"] = exc.messages
    elif "password" not in errors:
        errors["password"] = ["Password is required."]

    if errors:
        return JsonResponse(errors, status=400)

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_active=False,
            )

            if phone_number:
                SMSPreference.objects.create(
                    user=user,
                    phone_number=phone_number,
                    sms_enabled=sms_enabled,
                )

            _, token = EmailVerification.create_for_user(user)

            frontend_url = settings.FRONTEND_BASE_URL.rstrip("/")
            verification_link = (
                f"{frontend_url}/verify-email#token={token}"
            )

            send_mail(
                subject="Verify your Tuviora email address",
                message=(
                    f"Hello {first_name},\n\n"
                    "Welcome to Tuviora. Verify your email "
                    "address using the link below:\n\n"
                    f"{verification_link}\n\n"
                    "This link expires in 24 hours.\n\n"
                    "If you did not register, ignore this email."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )

            if sms_enabled and phone_number:
                transaction.on_commit(
                    lambda number=phone_number, name=first_name:
                    send_registration_sms(number, name)
                )

    except IntegrityError:
        return JsonResponse(
            {"detail": "This account could not be created. "
                       "Please check your username and email."},
            status=400,
        )

    return JsonResponse(
        {
            "detail": (
                "Registration successful. Check your email "
                "for a verification link."
            )
        },
        status=201,
    )


@require_POST
def verify_email(request):
    data = parse_json(request)

    if data is None:
        return JsonResponse(
            {"detail": "A valid JSON object is required."},
            status=400,
        )

    token = data.get("token", "")

    if not isinstance(token, str) or not token or len(token) > 256:
        return JsonResponse(
            {"detail": "Invalid verification link."},
            status=400,
        )

    token_hash = hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

    with transaction.atomic():
        verification = (
            EmailVerification.objects
            .select_for_update()
            .select_related("user")
            .filter(token_hash=token_hash)
            .first()
        )

        if verification is None:
            return JsonResponse(
                {"detail": "Invalid verification link."},
                status=400,
            )

        if verification.verified_at is not None:
            return JsonResponse(
                {"detail": "This verification link has already been used."},
                status=400,
            )

        if verification.expires_at <= timezone.now():
            return JsonResponse(
                {"detail": "This verification link has expired."},
                status=400,
            )

        user = verification.user
        user.is_active = True
        user.save(update_fields=["is_active"])

        verification.verified_at = timezone.now()
        verification.save(update_fields=["verified_at"])

    return JsonResponse(
        {"detail": "Email verified. You can now sign in."}
    )
