from django.db import models
from accounts.models import User
from django.utils.timezone import now
from datetime import timedelta
from django.core.validators import MinValueValidator, MaxValueValidator

class Vehicle(models.Model):
    customer=models.ForeignKey(User,on_delete=models.CASCADE)
    vehicle_number=models.CharField(max_length=20)
    model=models.CharField(max_length=100)
    company=models.CharField(max_length=100)

    def __str__(self):
        return self.vehicle_number

class ServiceJob(models.Model):
    STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('in_progress', 'In Progress'),
    ('completed', 'Completed'),
    ]
    vehicle = models.ForeignKey('Vehicle', on_delete=models.CASCADE)
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='customer_jobs')
    mechanic = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='mechanic_jobs')
    problem_description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    service_image = models.ImageField(upload_to='service_pics/', null=True, blank=True)
    mechanic_notes = models.TextField(null=True, blank=True)
    is_approved = models.BooleanField(default=False) # New field
    estimated_completion = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    rating = models.IntegerField(
    null=True, blank=True,
    validators=[MinValueValidator(1), MaxValueValidator(5)])
    feedback = models.TextField(null=True, blank=True)
    warranty_expiry = models.DateField(null=True, blank=True)
    next_service_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.vehicle} - {self.status}"

    def can_delete(self):
        return self.status == 'completed' and self.created_at < now() - timedelta(days=3)



class Part(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    quantity = models.PositiveIntegerField(default=0)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    low_stock_threshold = models.PositiveIntegerField(default=5)

    def __str__(self):
        return self.name

    def is_low_stock(self):
        return self.quantity <= self.low_stock_threshold

class Invoice(models.Model):
    STATUS_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('paid', 'Paid'),
    ]

    service_job = models.OneToOneField(ServiceJob, on_delete=models.CASCADE, related_name='invoice')
    created_at = models.DateTimeField(auto_now_add=True)
    labour_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='unpaid')
    notes = models.TextField(blank=True)

    def parts_total(self):
        return sum(item.total_price() for item in self.invoice_parts.all())

    def grand_total(self):
        return self.parts_total() + self.labour_charge

    def __str__(self):
        return f"Invoice - {self.service_job}"


class InvoicePart(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='invoice_parts')
    part = models.ForeignKey(Part, on_delete=models.CASCADE)
    quantity_used = models.PositiveIntegerField(default=1)

    def total_price(self):
        return self.quantity_used * self.part.unit_price

    def __str__(self):
        return f"{self.part.name} x {self.quantity_used}"

# In your models.py
class Payment(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    razorpay_order_id = models.CharField(max_length=100)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=100, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, default='Pending') # Pending, Success, Failed
    created_at = models.DateTimeField(auto_now_add=True)

    @property  # <--- Add this decorator
    def grand_total(self):
        return self.parts_total + self.labour_charge


