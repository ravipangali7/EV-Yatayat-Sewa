# Convert SiteSetting.values from JSONField to TextField

from django.db import migrations, models


def values_json_to_text(apps, schema_editor):
    SiteSetting = apps.get_model('website', 'SiteSetting')
    for obj in SiteSetting.objects.all():
        old = obj.values_old
        if isinstance(old, list):
            parts = []
            for item in old:
                if isinstance(item, dict) and 'text' in item:
                    parts.append(str(item['text']))
                elif isinstance(item, str):
                    parts.append(item)
            obj.values_text = '\n'.join(parts)
        else:
            obj.values_text = ''
        obj.save()


def reverse_values_text_to_json(apps, schema_editor):
    SiteSetting = apps.get_model('website', 'SiteSetting')
    for obj in SiteSetting.objects.all():
        text = getattr(obj, 'values_text', '') or ''
        obj.values_old = [{'text': line} for line in text.splitlines() if line.strip()]
        obj.save()


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0003_add_about_fields_to_site_setting'),
    ]

    operations = [
        migrations.RenameField(
            model_name='sitesetting',
            old_name='values',
            new_name='values_old',
        ),
        migrations.AddField(
            model_name='sitesetting',
            name='values_text',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.RunPython(values_json_to_text, reverse_values_text_to_json),
        migrations.RemoveField(
            model_name='sitesetting',
            name='values_old',
        ),
        migrations.RenameField(
            model_name='sitesetting',
            old_name='values_text',
            new_name='values',
        ),
    ]
