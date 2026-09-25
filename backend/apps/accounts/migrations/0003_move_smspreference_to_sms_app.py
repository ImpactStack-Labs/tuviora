# Generated manually: removes SMSPreference from apps.accounts's migration
# state without touching the database. The model and its table now live in
# apps.sms — see apps.sms.migrations.0001_initial.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_smspreference"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name="SMSPreference"),
            ],
            database_operations=[],
        ),
    ]
