import os
import json
from openai import OpenAI
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

# In-memory store: keyed by MRN
care_plans = {}


def build_prompt(data):
    med_history = ", ".join(data.get("medication_history", [])) or "None reported"
    additional_dx = ", ".join(data.get("additional_diagnoses", [])) or "None"
    patient_records = data.get("patient_records", "").strip() or "None provided"

    return f"""You are a clinical pharmacist generating a comprehensive care plan for a specialty pharmacy patient.

Patient Information:
- Name: {data["patient_first_name"]} {data["patient_last_name"]}
- MRN: {data["patient_mrn"]}
- Primary Diagnosis (ICD-10): {data["primary_diagnosis"]}
- Additional Diagnoses: {additional_dx}

Referring Provider:
- Name: {data["referring_provider_name"]}
- NPI: {data["referring_provider_npi"]}

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

    prompt = build_prompt(data)

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    message = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    care_plan_text = message.choices[0].message.content

    # Store in memory
    mrn = data["patient_mrn"]
    care_plans[mrn] = {
        "patient": f"{data['patient_first_name']} {data['patient_last_name']}",
        "medication": data["medication_name"],
        "care_plan": care_plan_text,
    }

    return JsonResponse({"care_plan": care_plan_text})
