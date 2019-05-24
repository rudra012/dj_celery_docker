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

DATE_FORMAT = "%d-%m-%Y"
DATETIME_FORMAT = "%d-%m-%YT%H:%M:%SZ"

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
        # Here write checks to be execute before calling scheduler
        print('\n\n\nself.app.now: ', self.app.now())
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
        last_executed_at = self.model.last_executed_at
        print('last_executed_at', last_executed_at)
        today = self.app.now()
        if self.model.scheduler_type == 'monthly':
            month_last_date = datetime.datetime(today.year, today.month, 1) + relativedelta(months=1, days=-1)
            month_first_date = today.replace(day=1)
            today_week_no = today.isocalendar()[1]
            print('today_week_no:', today_week_no)

            if self.model.monthly_type == 'monthly_last_day':
                # Get this month's last date
                # month_last_date = datetime.datetime.now()
                if month_last_date.date() != today.date():
                    print('Not today so execute after {} seconds'.format(self.max_interval))
                    return schedules.schedstate(False, self.max_interval)
                elif last_executed_at and month_last_date.date() == last_executed_at.date():
                    print('Executed today so execute after {} seconds'.format(self.max_interval))
                    return schedules.schedstate(False, self.max_interval)
            elif self.model.scheduler_type in ['monthly_first_week', 'monthly_second_week',
                                               'monthly_third_week', 'monthly_fourth_week']:
                first_week_no = month_first_date.isocalendar()[1]
                print('first_week_no:', first_week_no)
                week_diff = 0
                if self.model.scheduler_type == 'monthly_second_week':
                    week_diff = 1
                elif self.model.scheduler_type == 'monthly_third_week':
                    week_diff = 2
                elif self.model.scheduler_type == 'monthly_fourth_week':
                    week_diff = 3
                if today_week_no - first_week_no == week_diff:
                    pass
                return schedules.schedstate(False, self.max_interval)
            elif self.model.scheduler_type == 'monthly_last_week':
                last_week_no = month_last_date.isocalendar()[1]
                print('last_week_no:', last_week_no)
                if today_week_no == last_week_no:
                    pass
                return schedules.schedstate(False, self.max_interval)
        elif self.model.scheduler_type == 'weekly':
            day_number = today.strftime("%w")
            day_last_executed_at = self.model.last_executed_days.get(
                day_number) if self.model.last_executed_days else None
            print('day_last_executed_at: ', day_last_executed_at)
            if day_last_executed_at:
                day_last_executed_at = datetime.datetime.strptime(day_last_executed_at, DATETIME_FORMAT)
                print('day_last_executed_at: ', day_last_executed_at)
                if today.isocalendar()[1] - day_last_executed_at.isocalendar()[1] != self.model.every:
                    print("Already executed on day_last_executed_at")
                    return schedules.schedstate(False, self.max_interval)
            elif last_executed_at:
                if today.isocalendar()[1] - last_executed_at.isocalendar()[1] != self.model.every:
                    print("Already executed on last_executed_at")
                    return schedules.schedstate(False, self.max_interval)

        print('Calling scheduler function: ', self.schedule, '####')
        return self.schedule.is_due(make_aware(self.last_run_at))

    def __next__(self):
        cls_obj = super(CustomModelEntry, self).__next__()

        # Changes on execution of task
        last_executed_days = self.model.last_executed_days or {}
        if self.model.scheduler_type == 'weekly':
            today = self.app.now()
            last_executed_days[today.strftime("%w")] = today.strftime(DATETIME_FORMAT)
        elif self.model.scheduler_type == 'monthly':
            today = self.app.now()
            last_executed_days[today.strftime(DATE_FORMAT)] = {
                today.strftime("%w"): today.strftime(DATETIME_FORMAT)}
        print(last_executed_days)
        self.model.last_executed_days = last_executed_days
        self.model.last_executed_at = self.app.now()
        self.model.save()
        # self.model.save(update_fields=["last_run_at", "total_run_count"])
        return cls_obj


class CustomDatabaseScheduler(DatabaseScheduler):
    Entry = CustomModelEntry
    Model = CustomPeriodicTask
