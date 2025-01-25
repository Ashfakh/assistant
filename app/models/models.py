from django.db import models
from django.utils import timezone
from django.contrib.postgres.indexes import GinIndex
from pgvector.django import VectorField, HnswIndex

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

EMBEDDING_DIMENSIONS = 1536


class DataEmbedding(models.Model):
    title = models.CharField(max_length=500, blank=False, null=False)
    url = models.URLField(max_length=1024, blank=False, null=False, default="")
    text_override = models.TextField(null=True)
    text = models.TextField(blank=False, null=False, default="")
    metadata = models.JSONField(blank=True, null=True)
    embedding = VectorField(dimensions=EMBEDDING_DIMENSIONS)

    class Meta:
        db_table = "data_embeddings"
        indexes = [
            HnswIndex(
                name="ix_embedding_cosine",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
            GinIndex(
                fields=["metadata"],
                name="ix_metadata_gin",
                opclasses=["jsonb_path_ops"],
            ),
        ]

class User(models.Model):
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    )
    
    ROLE_CHOICES = (
        ('DAD', 'Dad'),
        ('SON', 'Son'),
    )

    name = models.CharField(max_length=255)
    age = models.IntegerField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    role = models.CharField(max_length=3, choices=ROLE_CHOICES)
    mood_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.role})"

    @property
    def mood_schema(self):
        """
        Example mood JSON structure:
        {
            "timestamp": "2024-03-20T14:30:00Z",
            "overall_mood": "good",  # good, neutral, bad
            "energy_level": 8,       # scale 1-10
            "emotional_state": {
                "happiness": 7,      # scale 1-10
                "anxiety": 3,        # scale 1-10
                "irritability": 2,   # scale 1-10
                "stress": 4         # scale 1-10
            },
            "physical_state": {
                "pain_level": 2,     # scale 1-10
                "fatigue": 3,        # scale 1-10
                "sleep_quality": 8   # scale 1-10
            },
            "notes": "Feeling well after morning walk",
            "activities": ["walking", "reading", "family time"],
            "medication_taken": true
        }
        """
        return {}
