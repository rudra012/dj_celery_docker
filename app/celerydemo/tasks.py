from celery import shared_task

from .models import TaskLog


@shared_task
def logging_task():
    print('Logging task invoked...........')
    TaskLog.objects.create(task_name='test')
