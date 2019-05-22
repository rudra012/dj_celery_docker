from __future__ import absolute_import, unicode_literals

from django.core.exceptions import MultipleObjectsReturned, ValidationError
from django.db import models
from django.db.models import signals
from django.utils.translation import ugettext_lazy as _
from django_celery_beat.models import PeriodicTask, PeriodicTasks

from . import schedules
from .clockedschedule import clocked


class TaskLog(models.Model):
    task_name = models.CharField(max_length=255)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True)


class ClockedSchedule(models.Model):
    """clocked schedule."""

    clocked_time = models.DateTimeField(
        verbose_name=_('Clock Time'),
        help_text=_('Run the task at clocked time'),
    )
    enabled = models.BooleanField(
        default=True,
        # editable=False,
        verbose_name=_('Enabled'),
        help_text=_('Set to False to disable the schedule'),
    )

    class Meta:
        """Table information."""

        verbose_name = _('clocked')
        verbose_name_plural = _('clocked')
        ordering = ['clocked_time']

    def __str__(self):
        return '{} {}'.format(self.clocked_time, self.enabled)

    @property
    def schedule(self):
        c = clocked(clocked_time=self.clocked_time,
                    enabled=self.enabled, model=self)
        return c

    @classmethod
    def from_schedule(cls, schedule):
        spec = {'clocked_time': schedule.clocked_time,
                'enabled': schedule.enabled}
        try:
            return cls.objects.get(**spec)
        except cls.DoesNotExist:
            return cls(**spec)
        except MultipleObjectsReturned:
            cls.objects.filter(**spec).delete()
            return cls(**spec)


class CustomPeriodicTask(PeriodicTask):
    PERIOD_CHOICES = (
        ('once', _('Once')),
        ('daily', _('Daily')),
        ('weekly', _('Weekly')),
        ('monthly', _('Monthly')),
        ('monthly_last_day', _('Monthly last day')),
    )
    clocked = models.ForeignKey(
        ClockedSchedule, on_delete=models.CASCADE, null=True, blank=True,
        verbose_name=_('Clocked Schedule'),
        help_text=_('Clocked Schedule to run the task on.  '
                    'Set only one schedule type, leave the others null.'),
    )
    end_time = models.DateTimeField(
        _('end_time'), blank=True, null=True,
    )
    every = models.IntegerField(_('every'), null=False, default=1)
    scheduler_type = models.CharField(
        _('scheduler_type'), max_length=24, choices=PERIOD_CHOICES, null=True, blank=True
    )
    max_run_count = models.PositiveIntegerField(null=True, blank=True)
    last_executed_at = models.DateTimeField(null=True, blank=True)
    schedule_types = ['interval', 'crontab', 'solar', 'clocked']

    def validate_unique(self, *args, **kwargs):
        super(PeriodicTask, self).validate_unique(*args, **kwargs)

        schedule_types = ['interval', 'crontab', 'solar', 'clocked']
        selected_schedule_types = [s for s in schedule_types
                                   if getattr(self, s)]

        if len(selected_schedule_types) == 0:
            raise ValidationError({
                'interval': [
                    'One of clocked, interval, crontab, or solar must be set.'
                ]
            })

        err_msg = 'Only one of clocked, interval, crontab, ' \
                  'or solar must be set'
        if len(selected_schedule_types) > 1:
            error_info = {}
            for selected_schedule_type in selected_schedule_types:
                error_info[selected_schedule_type] = [err_msg]
            raise ValidationError(error_info)

        # clocked must be one off task
        if self.clocked and not self.one_off:
            err_msg = 'clocked must be one off, one_off must set True'
            raise ValidationError(err_msg)

    def __str__(self):
        fmt = '{0.name}: {{no schedule}}'
        if self.interval:
            fmt = '{0.name}: {0.interval}'
        if self.crontab:
            fmt = '{0.name}: {0.crontab}'
        if self.solar:
            fmt = '{0.name}: {0.solar}'
        if self.clocked:
            fmt = '{0.name}: {0.clocked}'
        return fmt.format(self)

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
signals.post_delete.connect(PeriodicTasks.update_changed, sender=ClockedSchedule)
signals.post_save.connect(PeriodicTasks.update_changed, sender=ClockedSchedule)
