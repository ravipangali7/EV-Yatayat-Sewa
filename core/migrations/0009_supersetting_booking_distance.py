# Generated for short_trip_min/max_distance_for_booking

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_add_payment_transaction'),
    ]

    operations = [
        migrations.AddField(
            model_name='supersetting',
            name='short_trip_min_distance_for_booking',
            field=models.DecimalField(blank=True, decimal_places=2, default=5, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='supersetting',
            name='short_trip_max_distance_for_booking',
            field=models.DecimalField(blank=True, decimal_places=2, default=200, max_digits=10, null=True),
        ),
    ]
