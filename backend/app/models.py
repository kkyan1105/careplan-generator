from django.db import models


class Patient(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    mrn = models.CharField(max_length=50, unique=True)
    dob = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.mrn})"


class Provider(models.Model):
    name = models.CharField(max_length=200)
    npi = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return f"{self.name} ({self.npi})"


class Order(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="orders")
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name="orders")
    medication = models.CharField(max_length=200)
    diagnosis = models.CharField(max_length=100)
    additional_diagnoses = models.JSONField(default=list)
    medication_history = models.JSONField(default=list)
    medical_records = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.id} - {self.patient} - {self.medication}"


class CarePlan(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="care_plan")
    content = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"CarePlan {self.id} - {self.status}"
