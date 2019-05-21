from celery import schedules


class my_crontab(schedules.crontab):
    def is_due(self, last_run_at):
        print('cron is_due: ', last_run_at)
        # if last_run_at - date
        # if True:
        #     return schedules.schedstate(False, 5.0)
        rem_delta = self.remaining_estimate(last_run_at)
        rem = max(rem_delta.total_seconds(), 0)
        print('rem', rem)
        due = rem == 0
        if due:
            rem_delta = self.remaining_estimate(self.now())
            rem = max(rem_delta.total_seconds(), 0)
        print('due, rem', due, rem)
        return schedules.schedstate(due, rem)
        # return super(my_crontab, self).is_due(last_run_at)
