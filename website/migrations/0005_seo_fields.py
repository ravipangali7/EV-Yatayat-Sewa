from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0004_convert_values_to_textfield'),
    ]

    operations = [
        migrations.AddField(
            model_name='blog',
            name='canonical_path',
            field=models.CharField(blank=True, default='', max_length=500),
        ),
        migrations.AddField(
            model_name='blog',
            name='meta_description',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='blog',
            name='meta_title',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='blog',
            name='og_image',
            field=models.ImageField(blank=True, null=True, upload_to='uploads/website/blog/og/'),
        ),
        migrations.AddField(
            model_name='blog',
            name='og_image_alt',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='blog',
            name='robots_noindex',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='cmspage',
            name='canonical_path',
            field=models.CharField(blank=True, default='', max_length=500),
        ),
        migrations.AddField(
            model_name='cmspage',
            name='meta_description',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='cmspage',
            name='meta_title',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='cmspage',
            name='og_image',
            field=models.ImageField(blank=True, null=True, upload_to='uploads/website/cms/og/'),
        ),
        migrations.AddField(
            model_name='cmspage',
            name='og_image_alt',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='cmspage',
            name='robots_noindex',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='service',
            name='canonical_path',
            field=models.CharField(blank=True, default='', max_length=500),
        ),
        migrations.AddField(
            model_name='service',
            name='meta_description',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='service',
            name='meta_title',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='service',
            name='og_image',
            field=models.ImageField(blank=True, null=True, upload_to='uploads/website/services/og/'),
        ),
        migrations.AddField(
            model_name='service',
            name='og_image_alt',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='service',
            name='robots_noindex',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='sitesetting',
            name='default_og_image',
            field=models.ImageField(blank=True, null=True, upload_to='uploads/website/site/'),
        ),
        migrations.AddField(
            model_name='sitesetting',
            name='facebook_app_id',
            field=models.CharField(blank=True, default='', max_length=32),
        ),
        migrations.AddField(
            model_name='sitesetting',
            name='favicon',
            field=models.ImageField(blank=True, null=True, upload_to='uploads/website/site/'),
        ),
        migrations.AddField(
            model_name='sitesetting',
            name='google_site_verification',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='sitesetting',
            name='meta_description',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='sitesetting',
            name='meta_title',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='sitesetting',
            name='og_locale',
            field=models.CharField(blank=True, default='en_US', max_length=20),
        ),
        migrations.AddField(
            model_name='sitesetting',
            name='twitter_handle',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
    ]
