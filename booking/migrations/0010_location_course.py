# Generated for course (direction) on Location

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0009_routestoppoint_announcement_text'),
    ]

    operations = [
        migrations.AddField(
            model_name='location',
            name='course',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True),
        ),
    ]
