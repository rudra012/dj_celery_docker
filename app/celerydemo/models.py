from django.db import models

class TaskLog(models.Model):
    task_name = models.CharField(max_length=255)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True)

