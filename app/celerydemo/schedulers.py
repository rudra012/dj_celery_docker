from __future__ import absolute_import, unicode_literals

import datetime
import math

from celery import schedules
from celery.utils.time import maybe_make_aware
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django_celery_beat.models import IntervalSchedule, CrontabSchedule, SolarSchedule
from django_celery_beat.schedulers import ModelEntry, DatabaseScheduler
from django_celery_beat.utils import make_aware

from .clockedschedule import clocked
from .models import (
    ClockedSchedule,
    CustomPeriodicTask)
from .schedules import my_crontab

try:
    from celery.utils.time import is_naive
except ImportError:  # pragma: no cover
    pass


class CustomModelEntry(ModelEntry):
    model_schedules = (
        (my_crontab, CrontabSchedule, 'crontab'),
        (schedules.schedule, IntervalSchedule, 'interval'),
        (schedules.solar, SolarSchedule, 'solar'),
        (clocked, ClockedSchedule, 'clocked')
    )
    max_interval = 60

    def is_due(self):
        # return super(CustomModelEntry, self).is_due()
        print('\n\n\nself.max_interval: ', self.kwargs)
        print('******', self.schedule, self.model._meta.model_name, '******', )
        print('******', self.model.name, self.model.task, self.model.enabled, '******', )
        if not self.model.enabled:
            # max interval second delay for re-enable.
            return schedules.schedstate(False, self.max_interval)

        # START DATE: only run after the `start_time`, if one exists.
        if self.model.start_time is not None:
            now = self._default_now()
            if getattr(settings, 'DJANGO_CELERY_BEAT_TZ_AWARE', True):
                now = maybe_make_aware(self._default_now())

            if now < self.model.start_time:
                # The datetime is before the start date - don't run.
                # send a delay to retry on start_time
                delay = math.ceil(
                    (self.model.start_time - now).total_seconds()
                )
                print('Call function after {} seconds'.format(delay))
                return schedules.schedstate(False, delay)

        # ONE OFF TASK: Disable one off tasks after they've ran once
        def disable_task():
            self.model.enabled = False
            # self.model.total_run_count = 0  # Reset
            self.model.no_changes = False  # Mark the model entry as changed
            self.model.save()
            # self.model.save(update_fields=["enabled", ])
            print('Disable the periodic task', self.model)
            return schedules.schedstate(False, None)  # Don't recheck

        print('self.model.max_run_count, self.model.total_run_count')
        print(self.model.max_run_count, self.model.total_run_count)
        if self.model.one_off and self.model.enabled and self.model.total_run_count > 0:
            return disable_task()

        # if task executed max_run_count times then disable task
        if self.model.max_run_count and self.model.max_run_count <= self.model.total_run_count:
            return disable_task()

        if self.model.end_time is not None:
            now = self._default_now()
            if getattr(settings, 'DJANGO_CELERY_BEAT_TZ_AWARE', True):
                now = maybe_make_aware(self._default_now())

            if now >= self.model.end_time:
                # disable task if end date is passed
                return disable_task()

        print('self.model.scheduler_type: ', self.model.scheduler_type)
        print('last_run_at', self.last_run_at, self.model.last_run_at)
        print('last_executed_at', self.model.last_executed_at)
        if self.model.scheduler_type == 'monthly_last_day':
            last_executed_at = self.model.last_executed_at
            # Get this month's last date
            today = datetime.datetime.now()
            month_last_date = datetime.datetime.now()
            # month_last_date = datetime.datetime(today.year, today.month, 1) + relativedelta(months=1, days=-1)
            if month_last_date.date() != today.date():
                print('Not today so execute after {} seconds'.format(self.max_interval))
                return schedules.schedstate(False, self.max_interval)
            elif last_executed_at and month_last_date.date() == last_executed_at.date():
                print('Executed today so execute after {} seconds'.format(self.max_interval))
                return schedules.schedstate(False, self.max_interval)

        print('Calling scheduler function: ', self.schedule, '####')
        return self.schedule.is_due(make_aware(self.last_run_at))

    def __next__(self):
        cls_obj = super(CustomModelEntry, self).__next__()
        self.model.last_executed_at = self.app.now()
        self.model.save()
        # self.model.save(update_fields=["last_run_at", "total_run_count"])
        return cls_obj


class CustomDatabaseScheduler(DatabaseScheduler):
    Entry = CustomModelEntry
    Model = CustomPeriodicTask
