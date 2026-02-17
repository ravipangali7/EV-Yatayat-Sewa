# Generated for announcement_text on RouteStopPoint

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0008_add_seatbooking_destination_place'),
    ]

    operations = [
        migrations.AddField(
            model_name='routestoppoint',
            name='announcement_text',
            field=models.CharField(blank=True, default='', max_length=500),
        ),
    ]
