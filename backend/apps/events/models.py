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