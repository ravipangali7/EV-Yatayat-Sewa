from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_supersetting_luna_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='supersetting',
            name='default_price_per_km',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
    ]
