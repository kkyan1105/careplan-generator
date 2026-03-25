import os
from celery import shared_task
from openai import OpenAI
from app.models import CarePlan


def build_prompt(care_plan):
    order = care_plan.order
    patient = order.patient
    provider = order.provider
    med_history = ", ".join(order.medication_history) or "None reported"
    additional_dx = ", ".join(order.additional_diagnoses) or "None"
    patient_records = order.medical_records or "None provided"

    return f"""You are a clinical pharmacist generating a comprehensive care plan for a specialty pharmacy patient.

Patient Information:
- Name: {patient.first_name} {patient.last_name}
- MRN: {patient.mrn}
- Primary Diagnosis (ICD-10): {order.diagnosis}
- Additional Diagnoses: {additional_dx}

Referring Provider:
- Name: {provider.name}
- NPI: {provider.npi}

Medication Order:
- Medication: {order.medication}
- Prior Medication History: {med_history}

Patient Records / Notes:
{patient_records}

Generate a complete care plan with the following four sections. Be specific and clinically appropriate.

## 1. Problem List / Drug Therapy Problems (DTPs)
## 2. Goals (SMART Format)
## 3. Pharmacist Interventions / Plan
## 4. Monitoring Plan & Lab Schedule

Write in a clear, professional clinical tone."""


@shared_task(bind=True, max_retries=3)
def process_careplan(self, careplan_id):
    care_plan = CarePlan.objects.get(id=careplan_id)
    care_plan.status = "processing"
    care_plan.save()

    try:
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        message = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=2048,
            messages=[{"role": "user", "content": build_prompt(care_plan)}],
        )
        care_plan.content = message.choices[0].message.content
        care_plan.status = "completed"
        care_plan.save()

    except Exception as exc:
        care_plan.status = "failed"
        care_plan.save()
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
