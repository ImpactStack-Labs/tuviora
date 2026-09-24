"""Email notifications for readiness task assignments."""

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


def queue_task_assignment_email(task):
    """Send an assignment email after the current transaction commits."""
    assignee = task.assignee

    if assignee is None or not assignee.email:
        return

    recipient = assignee.email
    recipient_name = assignee.get_full_name() or assignee.username
    task_id = task.pk
    event_name = task.event.name
    title = task.title
    description = task.description or "None"

    deadline = (
        timezone.localtime(task.deadline).strftime(
            "%d %B %Y at %H:%M %Z"
        )
        if task.deadline
        else "No deadline set"
    )

    workspace_url = (
        f"{settings.FRONTEND_BASE_URL.rstrip('/')}/operations"
    )

    def deliver():
        try:
            send_mail(
                subject=f"Task assigned: {title} | Tuviora",
                message=(
                    f"Hello {recipient_name},\n\n"
                    f"You have been assigned a task for {event_name}.\n\n"
                    f"Task: {title}\n"
                    f"Description: {description}\n"
                    f"Deadline: {deadline}\n\n"
                    f"Open your workspace: {workspace_url}\n\n"
                    "Tuviora Team"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False,
            )
        except Exception:
            logger.exception(
                "Task assignment email failed for task %s",
                task_id,
            )

    transaction.on_commit(deliver)
