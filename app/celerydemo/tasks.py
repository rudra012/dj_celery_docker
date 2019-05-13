from celery import shared_task
from .models import TaskLog

@shared_task
def loggin_task():
    print('Loggin task invoked...........')
    TaskLog.objects.create(task_name='test')
