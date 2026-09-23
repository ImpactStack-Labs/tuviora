from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Event(models.Model):
    class Category(models.TextChoices):
        CONFERENCE = "conference", "Conference"
        HACKATHON = "hackathon", "Hackathon"
        WORKSHOP = "workshop", "Workshop"
        WEDDING = "wedding", "Wedding"
        CONCERT = "concert", "Concert"
        FUNDRAISER = "fundraiser", "Fundraiser"
        COMMUNITY = "community", "Community"
        CORPORATE = "corporate", "Corporate"
        OTHER = "other", "Other"

    class EventFormat(models.TextChoices):
        PHYSICAL = "physical", "Physical"
        VIRTUAL = "virtual", "Virtual"
        HYBRID = "hybrid", "Hybrid"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"

    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="events",
    )

    name = models.CharField(max_length=255)

    category = models.CharField(
        max_length=30,
        choices=Category.choices,
    )

    description = models.TextField(blank=True)

    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    event_format = models.CharField(
        max_length=20,
        choices=EventFormat.choices,
        default=EventFormat.PHYSICAL,
    )

    venue = models.CharField(
        max_length=255,
        blank=True,
    )

    landmark = models.CharField(
        max_length=255,
        blank=True,
    )

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(-90),
            MaxValueValidator(90),
        ],
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(-180),
            MaxValueValidator(180),
        ],
    )

    online_platform = models.CharField(
        max_length=100,
        blank=True,
    )

    online_url = models.URLField(
        blank=True,
    )

    joining_instructions = models.TextField(
        blank=True,
    )

    capacity = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(1),
        ],
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class ReadinessTask(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="readiness_tasks",
    )

    title = models.CharField(max_length=255)

    description = models.TextField(blank=True)

    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_readiness_tasks",
    )

    deadline = models.DateTimeField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["deadline", "-created_at"]

    def __str__(self):
        return self.title


class Incident(models.Model):
    class Category(models.TextChoices):
        NETWORK = "network", "Network"
        POWER = "power", "Power"
        VENUE = "venue", "Venue"
        SECURITY = "security", "Security"
        ATTENDANCE = "attendance", "Attendance"
        PAYMENT = "payment", "Payment"
        TECHNICAL = "technical", "Technical"
        OTHER = "other", "Other"

    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In Progress"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="incidents",
    )

    title = models.CharField(max_length=255)

    description = models.TextField()

    category = models.CharField(
        max_length=30,
        choices=Category.choices,
    )

    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        default=Severity.MEDIUM,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )

    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reported_incidents",
    )

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class AIIncidentAnalysis(models.Model):
    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    class ApprovalStatus(models.TextChoices):
        PENDING = "pending", "Pending Approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        FAILED = "failed", "Failed"

    incident = models.OneToOneField(
        Incident,
        on_delete=models.CASCADE,
        related_name="ai_analysis",
    )

    classification = models.CharField(max_length=30)

    suggested_severity = models.CharField(
        max_length=20,
        choices=Incident.Severity.choices,
    )

    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
    )

    recommended_actions = models.JSONField(
        default=list,
    )

    draft_message = models.TextField()

    approval_status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_ai_incident_analyses",
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"AI analysis for incident #{self.incident_id}"


class Feedback(models.Model):
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="feedback",
    )

    attendee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_feedback",
    )

    rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ],
    )

    comment = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Feedback for {self.event.name}"


class AIFeedbackAnalysis(models.Model):
    event = models.OneToOneField(
        Event,
        on_delete=models.CASCADE,
        related_name="ai_feedback_analysis",
    )

    themes = models.JSONField(
        default=list,
    )

    concerns_summary = models.TextField(
        blank=True,
    )

    suggested_improvements = models.JSONField(
        default=list,
    )

    analysis_type = models.CharField(
        max_length=100,
        default="AI-generated analysis",
    )

    error_message = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"AI feedback analysis for {self.event.name}"
