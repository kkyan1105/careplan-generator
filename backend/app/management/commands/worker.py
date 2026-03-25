import os
import redis
from openai import OpenAI
from django.core.management.base import BaseCommand
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


def process(careplan_id):
    care_plan = CarePlan.objects.get(id=careplan_id)
    care_plan.status = "processing"
    care_plan.save()

    prompt = build_prompt(care_plan)

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    message = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    care_plan.content = message.choices[0].message.content
    care_plan.status = "completed"
    care_plan.save()

    print(f"careplan {careplan_id} completed")


class Command(BaseCommand):
    help = "Worker: pull careplan jobs from Redis and process them"

    def handle(self, *args, **kwargs):
        r = redis.Redis(host="redis", port=6379)
        self.stdout.write("Worker started, waiting for jobs...")

        while True:
            _, careplan_id = r.blpop("careplan_queue")
            careplan_id = int(careplan_id)
            self.stdout.write(f"Processing careplan {careplan_id}...")
            process(careplan_id)
