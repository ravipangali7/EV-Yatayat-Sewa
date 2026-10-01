from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0004_seatbooking_origin_place'),
    ]

    operations = [
        migrations.AddField(
            model_name='vehicleschedule',
            name='price_per_km',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
    ]
