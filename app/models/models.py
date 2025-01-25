from django.db import models
from django.utils import timezone

class Chat(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'models'

class Message(models.Model):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages')
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_user = models.BooleanField(default=True)
    
    class Meta:
        app_label = 'models'
        ordering = ['timestamp'] 

class Scheduler(models.Model):
    SCHEDULE_STATUS = (
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    schedule_time = models.DateTimeField()
    schedule_type = models.CharField(max_length=100)
    schedule_message = models.TextField()
    recipient = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=SCHEDULE_STATUS, default='active')
    cron_expression = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'schedulers'
        ordering = ['-created_at']

    def __str__(self):
        return f"Schedule for {self.recipient} at {self.schedule_time}" 