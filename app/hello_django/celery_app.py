import os

from celery import Celery
from django.conf import settings 
# Set default Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hello_django.settings')
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dcs.settings')

app = Celery('hello_django')
app.config_from_object('django.conf:settings')
# app.autodiscover_tasks()
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

# Optional configuration, see the application user guide.
app.conf.update(
    result_expires=3600,
)

#if __name__ == '__main__':
#    app.start()
