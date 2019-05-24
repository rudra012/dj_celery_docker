from __future__ import absolute_import, unicode_literals

import datetime
import math

from celery import schedules
from celery.utils.time import maybe_make_aware
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django_celery_beat.schedulers import ModelEntry, DatabaseScheduler
from django_celery_beat.utils import make_aware

from .models import (
    CustomPeriodicTask)

try:
    from celery.utils.time import is_naive
except ImportError:  # pragma: no cover
    pass

MONTH_FORMAT = "%m-%Y"
DATETIME_FORMAT = "%d-%m-%YT%H:%M:%SZ"


def months_difference(date1, date2):
    return date1.month - date2.month + 12 * (date1.year - date2.year)


class CustomModelEntry(ModelEntry):
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

        print('self.model.__class__.__name__: ', self.model.__class__.__name__)
        if self.model.__class__.__name__ == 'CustomPeriodicTask':
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
            if self.model.scheduler_type == 'MONTHLY':
                month_last_date = datetime.datetime(today.year, today.month, 1) + relativedelta(months=1, days=-1)
                month_first_date = today.replace(day=1)
                today_week_no = today.isocalendar()[1]
                print('today_week_no:', today_week_no)

                if last_executed_at and last_executed_at.date() == today.date():
                    # If task executed today then skip for today
                    print('Executed today')
                    return schedules.schedstate(False, self.max_interval)

                if self.model.monthly_type == 'LASTDAY':
                    # Get this month's last date
                    # month_last_date = datetime.datetime.now()
                    if month_last_date.date() != today.date():
                        print('Not today so execute after {} seconds'.format(self.max_interval))
                        return schedules.schedstate(False, self.max_interval)
                    elif last_executed_at and month_last_date.date() == last_executed_at.date():
                        print('Executed today so execute after {} seconds'.format(self.max_interval))
                        return schedules.schedstate(False, self.max_interval)
                elif self.model.monthly_type in ['FIRSTWEEK', 'SECONDWEEK', 'THIRDWEEK', 'FOURTHWEEK']:
                    first_week_no = month_first_date.isocalendar()[1]
                    print('first_week_no:', first_week_no)
                    week_diff = 0
                    if self.model.monthly_type == 'SECONDWEEK':
                        week_diff = 1
                    elif self.model.monthly_type == 'THIRDWEEK':
                        week_diff = 2
                    elif self.model.monthly_type == 'FOURTHWEEK':
                        week_diff = 3

                    if today_week_no - first_week_no == week_diff:
                        print('Week number pass')
                        last_executed_days = self.model.last_executed_days
                        print('last_executed_days: ', last_executed_days)
                        if last_executed_days:
                            last_executed_month_str = list(last_executed_days)[0]
                            print('last_executed_month_str: ', last_executed_month_str)
                            if len(last_executed_month_str.split('-')) == 2:
                                last_executed_month = datetime.datetime.strptime(
                                    last_executed_month_str, MONTH_FORMAT)
                                print('last_executed_month: ', last_executed_month)
                                print('months_difference(last_executed_month, today)',
                                      months_difference(today, last_executed_month))
                                if months_difference(today, last_executed_month) not in [0, self.model.every]:
                                    return schedules.schedstate(False, self.max_interval)

                elif self.model.monthly_type == 'LASTWEEK':
                    last_week_no = month_last_date.isocalendar()[1]
                    print('last_week_no:', last_week_no)
                    if today_week_no == last_week_no:
                        pass

                    return schedules.schedstate(False, self.max_interval)
            elif self.model.scheduler_type == 'WEEKLY':
                day_number = today.strftime("%w")
                day_last_executed_at = self.model.last_executed_days.get(
                    day_number) if self.model.last_executed_days else None
                print('day_last_executed_at: ', day_last_executed_at)
                if day_last_executed_at:
                    day_last_executed_at = datetime.datetime.strptime(day_last_executed_at, DATETIME_FORMAT)
                    print('day_last_executed_at: ', day_last_executed_at)
                    if today.isocalendar()[1] - day_last_executed_at.isocalendar()[1] != self.model.every:
                        print("Already executed on last week on the same day")
                        return schedules.schedstate(False, self.max_interval)
                elif last_executed_at:
                    if today.isocalendar()[1] - last_executed_at.isocalendar()[1] != self.model.every:
                        print("Already executed on last week on some day")
                        return schedules.schedstate(False, self.max_interval)

        print('Calling scheduler function: ', self.schedule, '####')
        return self.schedule.is_due(make_aware(self.last_run_at))

    def __next__(self):
        cls_obj = super(CustomModelEntry, self).__next__()

        # Changes on execution of task
        last_executed_days = self.model.last_executed_days or {}
        if self.model.scheduler_type == 'WEEKLY':
            today = self.app.now()
            last_executed_days[today.strftime("%w")] = today.strftime(DATETIME_FORMAT)
        elif self.model.scheduler_type == 'MONTHLY':
            today = self.app.now()
            print(last_executed_days, list(last_executed_days)[0] == today.strftime(MONTH_FORMAT))
            if last_executed_days and list(last_executed_days)[0] == today.strftime(MONTH_FORMAT):
                print('Same month')
                month_dict = last_executed_days[today.strftime(MONTH_FORMAT)]
                month_dict[today.strftime("%w")] = today.strftime(DATETIME_FORMAT)
                last_executed_days[today.strftime(MONTH_FORMAT)] = month_dict
            else:
                print('Different month')
                last_executed_days = {today.strftime(MONTH_FORMAT): {
                    today.strftime("%w"): today.strftime(DATETIME_FORMAT)}}
        print('last_executed_days: ', last_executed_days)
        self.model.last_executed_days = last_executed_days
        self.model.last_executed_at = self.app.now()
        self.model.save()
        # self.model.save(update_fields=["last_run_at", "total_run_count"])
        return cls_obj


class CustomDatabaseScheduler(DatabaseScheduler):
    Entry = CustomModelEntry
    Model = CustomPeriodicTask
