import os
import django
from django.conf import settings

# Initialize Django
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.django_orm.settings')
    django.setup() 