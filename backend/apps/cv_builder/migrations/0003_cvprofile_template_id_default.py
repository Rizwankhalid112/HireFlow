from django.db import migrations, models

from apps.cv_builder.templates_registry import DEFAULT_TEMPLATE_ID, template_choices


def set_default_on_existing_rows(apps, schema_editor):
    """Rows created before template_id had a default carry NULL. Backfill first
    so the NOT NULL below cannot fail on a populated table."""
    CVProfile = apps.get_model('cv_builder', 'CVProfile')
    CVProfile.objects.filter(template_id__isnull=True).update(template_id=DEFAULT_TEMPLATE_ID)
    CVProfile.objects.filter(template_id='').update(template_id=DEFAULT_TEMPLATE_ID)


class Migration(migrations.Migration):

    dependencies = [
        ('cv_builder', '0002_cvprofile_photo_alter_cvprofile_template_id'),
    ]

    operations = [
        migrations.RunPython(set_default_on_existing_rows, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='cvprofile',
            name='template_id',
            field=models.CharField(
                choices=template_choices(),
                default=DEFAULT_TEMPLATE_ID,
                max_length=50,
            ),
        ),
    ]
