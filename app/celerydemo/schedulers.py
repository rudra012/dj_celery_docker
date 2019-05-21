from __future__ import absolute_import, unicode_literals

import math

from celery import schedules
from celery.utils.time import maybe_make_aware
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

    def is_due(self):
        return super(CustomModelEntry, self).is_due()
        print('******', self.schedule, self.model._meta.model_name, '******', )
        print('******', self.model.name, self.model.task, self.model.enabled, '******', )
        if not self.model.enabled:
            # 5 second delay for re-enable.
            return schedules.schedstate(False, 5.0)

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
            self.model.total_run_count = 0  # Reset
            self.model.no_changes = False  # Mark the model entry as changed
            self.model.save()
            print('Disable the periodic task', self.model)
            return schedules.schedstate(False, None)  # Don't recheck

        print('self.model.max_run_count, self.model.total_run_count')
        print(self.model.max_run_count, self.model.total_run_count)
        if self.model.one_off and self.model.enabled and self.model.total_run_count > 0:
            disable_task()

        if self.model.max_run_count and self.model.max_run_count <= self.model.total_run_count:
            disable_task()

        print('Calling scheduler function: ', self.schedule, self.last_run_at, '####')
        return self.schedule.is_due(make_aware(self.last_run_at))

    def __next__(self):
        cls_obj = super(CustomModelEntry, self).__next__()
        self.model.save()
        return cls_obj


class CustomDatabaseScheduler(DatabaseScheduler):
    Entry = CustomModelEntry
    Model = CustomPeriodicTask
