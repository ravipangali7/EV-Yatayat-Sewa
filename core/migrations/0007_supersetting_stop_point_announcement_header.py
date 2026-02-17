# Generated for stop_point_announcement_header

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_supersetting_gps_rename_and_new_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='supersetting',
            name='stop_point_announcement_header',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
    ]
