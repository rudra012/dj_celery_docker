from django.contrib import admin
from django_celery_beat.admin import PeriodicTaskAdmin
from django_celery_beat.models import SolarSchedule

from .models import TaskLog, CustomPeriodicTask


class CustomPeriodicTaskAdmin(PeriodicTaskAdmin):
    fieldsets = (
        (None, {
            'fields': ('name', 'description', ('regtask', 'task'), 'enabled',),
            'classes': ('extrapretty', 'wide'),
        }),
        ('Schedule', {
            'fields': (
                ('scheduler_type', 'monthly_type'), ('start_time', 'end_time'),
                ('every', 'max_run_count'), 'one_off', 'crontab', 'interval', 'clocked'),
            'classes': ('extrapretty', 'wide'),
        }),
        ('Schedule Run Details', {
            'fields': ('total_run_count', 'last_run_at', 'last_executed_at',
                       'last_executed_days'),
            'classes': ('extrapretty', 'wide'),
        }),
        ('Arguments', {
            'fields': ('args', 'kwargs'),
            'classes': ('extrapretty', 'wide', 'collapse', 'in'),
        }),
        ('Execution Options', {
            'fields': ('expires', 'queue', 'exchange', 'routing_key',
                       'priority'),
            'classes': ('extrapretty', 'wide', 'collapse', 'in'),
        }),
    )
    readonly_fields = ('total_run_count', 'last_run_at')

    def get_queryset(self, request):
        qs = super(PeriodicTaskAdmin, self).get_queryset(request)
        return qs.select_related('interval', 'crontab', 'solar', 'clocked')


admin.site.register(TaskLog)
admin.site.register(CustomPeriodicTask, CustomPeriodicTaskAdmin)
# admin.site.unregister(PeriodicTask)
admin.site.unregister(SolarSchedule)
# admin.site.unregister(IntervalSchedule)
# admin.site.unregister(CrontabSchedule)
# admin.site.register(IntervalSchedule)
# admin.site.register(CrontabSchedule)
