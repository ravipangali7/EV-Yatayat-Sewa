from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='supersetting',
            name='luna_api_token',
            field=models.CharField(blank=True, default='', max_length=1024),
        ),
        migrations.AddField(
            model_name='supersetting',
            name='luna_web_origin',
            field=models.CharField(blank=True, default='', max_length=512),
        ),
    ]
