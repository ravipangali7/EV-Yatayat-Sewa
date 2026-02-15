# Generated manually for plan: rename gps_threshold -> gps_threshold_second, add point_cover_radius, minute_coverage_schedule

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_add_transaction_card_fk'),
    ]

    operations = [
        migrations.RenameField(
            model_name='supersetting',
            old_name='gps_threshold',
            new_name='gps_threshold_second',
        ),
        migrations.AddField(
            model_name='supersetting',
            name='point_cover_radius',
            field=models.DecimalField(blank=True, decimal_places=4, default=0.5, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='supersetting',
            name='minute_coverage_schedule',
            field=models.IntegerField(blank=True, default=60, null=True),
        ),
    ]
