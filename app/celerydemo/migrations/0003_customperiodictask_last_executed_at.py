# Generated by Django 2.2.1 on 2019-05-22 06:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('celerydemo', '0002_clockedschedule_customperiodictask'),
    ]

    operations = [
        migrations.AddField(
            model_name='customperiodictask',
            name='last_executed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
