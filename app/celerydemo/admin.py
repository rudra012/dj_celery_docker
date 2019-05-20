from django.contrib import admin
from django_celery_beat.admin import PeriodicTaskAdmin
from django_celery_beat.models import PeriodicTask, SolarSchedule

from .models import TaskLog, ClockedSchedule, CustomPeriodicTask


class CustomPeriodicTaskAdmin(PeriodicTaskAdmin):
    fieldsets = (
        (None, {
            'fields': ('name', 'regtask', 'task', 'enabled', 'description',),
            'classes': ('extrapretty', 'wide'),
        }),
        ('Schedule', {
            'fields': ('interval', 'crontab', 'solar', 'clocked',
                       'start_time', 'one_off'),
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

    def get_queryset(self, request):
        qs = super(PeriodicTaskAdmin, self).get_queryset(request)
        return qs.select_related('interval', 'crontab', 'solar', 'clocked')


admin.site.register(TaskLog)
admin.site.register(ClockedSchedule)
admin.site.register(CustomPeriodicTask, CustomPeriodicTaskAdmin)
admin.site.unregister(PeriodicTask)
admin.site.unregister(SolarSchedule)
