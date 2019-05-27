from __future__ import absolute_import, unicode_literals

from django.contrib.postgres.fields import JSONField
from django.db import models
from django.db.models import signals
from django.utils.translation import ugettext_lazy as _
from django_celery_beat.models import PeriodicTask, PeriodicTasks

from . import schedules


class TaskLog(models.Model):
    task_name = models.CharField(max_length=255)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True)


class CustomPeriodicTask(PeriodicTask):
    PERIOD_CHOICES = (
        ('ONCE', _('Once')),
        ('DAILY', _('Daily')),
        ('WEEKLY', _('Weekly')),
        ('MONTHLY', _('Monthly')),
    )
    MONTHLY_CHOICES = (
        ('DAY', _('Day')),
        ('FIRSTWEEK', _('First Week')),
        ('SECONDWEEK', _('Second Week')),
        ('THIRDWEEK', _('Third Week')),
        ('FOURTHWEEK', _('Fourth Week')),
        ('LASTWEEK', _('Last Week')),
        ('LASTDAY', _('Last Day')),
    )
    end_time = models.DateTimeField(
        _('End Datetime'), blank=True, null=True,
        help_text=_(
            'Datetime when the scheduled task should end')
    )
    every = models.PositiveSmallIntegerField(
        _('every'), null=False, default=1,
        help_text=_('For Weekly and Monthly Repeat')
    )
    scheduler_type = models.CharField(
        _('scheduler_type'), max_length=24, choices=PERIOD_CHOICES,
        null=True, blank=True
    )
    monthly_type = models.CharField(
        _('monthly_type'), max_length=24, choices=MONTHLY_CHOICES,
        null=True, blank=True
    )
    max_run_count = models.PositiveIntegerField(
        null=True, blank=True,
        help_text=_('To end scheduled task after few occurrence')
    )
    last_executed_at = models.DateTimeField(null=True, blank=True)
    last_executed_days = JSONField(null=True, blank=True)

    @property
    def schedule(self):
        if self.interval:
            return self.interval.schedule
        if self.crontab:
            crontab = schedules.my_crontab(
                minute=self.crontab.minute,
                hour=self.crontab.hour,
                day_of_week=self.crontab.day_of_week,
                day_of_month=self.crontab.day_of_month,
                month_of_year=self.crontab.month_of_year,
            )
            return crontab
        if self.solar:
            return self.solar.schedule
        if self.clocked:
            return self.clocked.schedule


signals.pre_delete.connect(PeriodicTasks.changed, sender=CustomPeriodicTask)
signals.pre_save.connect(PeriodicTasks.changed, sender=CustomPeriodicTask)
