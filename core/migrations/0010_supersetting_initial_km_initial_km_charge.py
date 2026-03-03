# Generated for initial_km and initial_km_charge pricing

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_supersetting_booking_distance'),
    ]

    operations = [
        migrations.AddField(
            model_name='supersetting',
            name='initial_km',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='supersetting',
            name='initial_km_charge',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
    ]
