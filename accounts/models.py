from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES=(
        ('admin','Admin'),
        ('mechanic','Mechanic'),
        ('customer','Customer'),
    )
    role=models.CharField(max_length=100,choices= ROLE_CHOICES)

