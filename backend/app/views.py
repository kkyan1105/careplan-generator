import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from app.models import Patient, Provider, Order, CarePlan
from app.tasks import process_careplan


def build_prompt(data, patient, provider):
    med_history = ", ".join(data.get("medication_history", [])) or "None reported"
    additional_dx = ", ".join(data.get("additional_diagnoses", [])) or "None"
    patient_records = data.get("patient_records", "").strip() or "None provided"

    return f"""You are a clinical pharmacist generating a comprehensive care plan for a specialty pharmacy patient.

Patient Information:
- Name: {patient.first_name} {patient.last_name}
- MRN: {patient.mrn}
- Primary Diagnosis (ICD-10): {data["primary_diagnosis"]}
- Additional Diagnoses: {additional_dx}

Referring Provider:
- Name: {provider.name}
- NPI: {provider.npi}

Medication Order:
- Medication: {data["medication_name"]}
- Prior Medication History: {med_history}

Patient Records / Notes:
{patient_records}

Generate a complete care plan with the following four sections. Be specific and clinically appropriate.

## 1. Problem List / Drug Therapy Problems (DTPs)
List the identified drug therapy problems. For each DTP, specify:
- The problem
- The drug involved (if applicable)
- The clinical rationale

## 2. Goals (SMART Format)
List measurable, time-bound goals for this patient. Each goal should be Specific, Measurable, Achievable, Relevant, and Time-bound.

## 3. Pharmacist Interventions / Plan
Detail the pharmacist's action plan, including:
- Patient counseling points
- Adherence strategies
- Drug therapy recommendations or changes
- Coordination with the prescriber

## 4. Monitoring Plan & Lab Schedule
Specify:
- Labs to monitor and frequency
- Clinical parameters to track
- Follow-up schedule
- Criteria for escalation or referral

Write in a clear, professional clinical tone suitable for a specialty pharmacy care plan document."""


@csrf_exempt
@require_POST
def generate_careplan(request):
    data = json.loads(request.body)

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

    return JsonResponse({"status": "pending", "careplan_id": care_plan.id})


@require_GET
def get_careplan(request, mrn):
    patient = Patient.objects.get(mrn=mrn)
    order = patient.orders.order_by("-created_at").first()
    care_plan = order.care_plan
    return JsonResponse({
        "patient": f"{patient.first_name} {patient.last_name}",
        "medication": order.medication,
        "care_plan": care_plan.content,
        "status": care_plan.status,
    })
