from django.urls import path
from app import views

urlpatterns = [
    path("api/careplan/generate/", views.generate_careplan),
    path("api/careplan/<str:mrn>/", views.get_careplan)
]

