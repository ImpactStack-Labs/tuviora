# Generated manually: brings SMSPreference into apps.sms's migration state
# without touching the database. The table was created by
# apps.accounts.migrations.0002_smspreference and is kept in place — see
# apps.sms.models.SMSPreference.Meta.db_table.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0003_move_smspreference_to_sms_app"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="SMSPreference",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        (
                            "phone_number",
                            models.CharField(blank=True, max_length=16),
                        ),
                        ("sms_enabled", models.BooleanField(default=False)),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        ("updated_at", models.DateTimeField(auto_now=True)),
                        (
                            "user",
                            models.OneToOneField(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="sms_preference",
                                to=settings.AUTH_USER_MODEL,
                            ),
                        ),
                    ],
                    options={
                        "db_table": "accounts_smspreference",
                    },
                ),
            ],
            database_operations=[],
        ),
    ]
