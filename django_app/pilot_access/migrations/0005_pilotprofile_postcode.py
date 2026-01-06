from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pilot_access", "0004_pilotprofile_preferred_contact_method_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="pilotprofile",
            name="postcode",
            field=models.CharField(blank=True, default="", max_length=16),
        ),
    ]
