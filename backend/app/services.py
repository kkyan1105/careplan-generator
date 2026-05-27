from app.models import Patient, Provider, Order, CarePlan
from app.tasks import process_careplan


def create_careplan(data):
    patient, _ = Patient.objects.get_or_create(
        mrn=data["patient_mrn"],
        defaults={
            "first_name": data["patient_first_name"],
            "last_name": data["patient_last_name"],
        },
    )

    provider, _ = Provider.objects.get_or_create(
        npi=data["referring_provider_npi"],
        defaults={"name": data["referring_provider_name"]},
    )

    order = Order.objects.create(
        patient=patient,
        provider=provider,
        medication=data["medication_name"],
        diagnosis=data["primary_diagnosis"],
        additional_diagnoses=data.get("additional_diagnoses", []),
        medication_history=data.get("medication_history", []),
        medical_records=data.get("patient_records", ""),
    )

    care_plan = CarePlan.objects.create(order=order, content="", status="pending")
    process_careplan.delay(care_plan.id)
    return care_plan


def get_careplan_status(careplan_id):
    return CarePlan.objects.get(id=careplan_id)


def get_careplan_by_mrn(mrn):
    patient = Patient.objects.get(mrn=mrn)
    order = patient.orders.order_by("-created_at").first()
    care_plan = order.care_plan
    return patient, order, care_plan
