# Generated by Django 2.2.1 on 2019-05-21 08:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('celerydemo', '0004_customperiodictask_max_run_count'),
    ]

    operations = [
        migrations.AddField(
            model_name='customperiodictask',
            name='end_time',
            field=models.DateTimeField(blank=True, null=True, verbose_name='end_time'),
        ),
    ]
