from django.core.management.base import BaseCommand
from app.models import Patient, Provider, Order, CarePlan


PATIENTS = [
    {"first_name": "John",    "last_name": "Doe",       "mrn": "MRN001", "dob": "1965-03-12"},
    {"first_name": "Maria",   "last_name": "Garcia",    "mrn": "MRN002", "dob": "1978-07-24"},
    {"first_name": "James",   "last_name": "Chen",      "mrn": "MRN003", "dob": "1952-11-05"},
    {"first_name": "Ashley",  "last_name": "Patel",     "mrn": "MRN004", "dob": "1990-01-30"},
    {"first_name": "Robert",  "last_name": "Williams",  "mrn": "MRN005", "dob": "1943-09-18"},
]

PROVIDERS = [
    {"name": "Dr. Sarah Thompson", "npi": "1234567890"},
    {"name": "Dr. Michael Lee",    "npi": "0987654321"},
    {"name": "Dr. Emily Nguyen",   "npi": "1122334455"},
]

ORDERS = [
    {
        "patient_mrn": "MRN001",
        "provider_npi": "1234567890",
        "medication": "Adalimumab (Humira)",
        "diagnosis": "M05.79",
        "additional_diagnoses": ["M79.3", "E11.9"],
        "medication_history": ["Methotrexate", "Naproxen"],
        "medical_records": "Patient presents with moderate-to-severe rheumatoid arthritis. Previous DMARD therapy insufficient. Labs: CRP elevated at 18 mg/L, RF positive.",
    },
    {
        "patient_mrn": "MRN002",
        "provider_npi": "0987654321",
        "medication": "Etanercept (Enbrel)",
        "diagnosis": "L40.50",
        "additional_diagnoses": ["L40.0"],
        "medication_history": ["Methotrexate", "Cyclosporine"],
        "medical_records": "Patient with psoriatic arthritis, failed conventional therapy. BSA involvement ~15%. Starting biologic therapy.",
    },
    {
        "patient_mrn": "MRN003",
        "provider_npi": "1122334455",
        "medication": "Apixaban (Eliquis)",
        "diagnosis": "I48.91",
        "additional_diagnoses": ["I10", "E78.5"],
        "medication_history": ["Warfarin", "Aspirin"],
        "medical_records": "79-year-old male with non-valvular atrial fibrillation. Transitioned from warfarin due to labile INR. CrCl 52 mL/min.",
    },
    {
        "patient_mrn": "MRN004",
        "provider_npi": "1234567890",
        "medication": "Semaglutide (Ozempic)",
        "diagnosis": "E11.65",
        "additional_diagnoses": ["E66.01", "I10"],
        "medication_history": ["Metformin", "Sitagliptin"],
        "medical_records": "Patient with T2DM and obesity. A1C 9.2%. Inadequate glycemic control on oral agents. Starting GLP-1 agonist.",
    },
    {
        "patient_mrn": "MRN005",
        "provider_npi": "0987654321",
        "medication": "Rivaroxaban (Xarelto)",
        "diagnosis": "I26.99",
        "additional_diagnoses": ["I48.0", "J44.1"],
        "medication_history": ["Warfarin", "Enoxaparin"],
        "medical_records": "Patient with PE secondary to DVT. Stable on anticoagulation. Transitioning to oral DOAC. CrCl 68 mL/min.",
    },
]

CARE_PLAN_CONTENT = {
    "MRN001": """## 1. Problem List / Drug Therapy Problems
- Undertreated RA: Adalimumab initiated due to inadequate response to methotrexate
- Comorbid T2DM (E11.9): Monitor for infection risk with biologic therapy

## 2. Goals (SMART Format)
- Reduce DAS28 score by ≥1.2 within 12 weeks of adalimumab initiation
- Maintain CRP <5 mg/L at 3-month follow-up

## 3. Pharmacist Interventions
- Counsel patient on subcutaneous injection technique and rotation sites
- Educate on signs of infection and when to hold medication
- Ensure TB screening and baseline labs completed prior to first dose

## 4. Monitoring Plan & Lab Schedule
- CBC, CMP, LFTs at baseline, 4 weeks, then every 3 months
- TB test and hepatitis B serology prior to initiation
- Follow-up call at 2 weeks post-first dose""",

    "MRN002": """## 1. Problem List / Drug Therapy Problems
- Active psoriatic arthritis: Inadequate response to conventional DMARDs
- Skin involvement: BSA 15%, requiring biologic escalation

## 2. Goals (SMART Format)
- Achieve PASI 75 response within 16 weeks
- Reduce joint swelling and pain VAS score to <3/10 by week 12

## 3. Pharmacist Interventions
- Counsel on proper storage (refrigerated 2-8°C) and self-injection
- Review infection precautions and live vaccine contraindications
- Coordinate with dermatology for skin monitoring

## 4. Monitoring Plan & Lab Schedule
- CBC, CMP at baseline and every 3 months
- PASI and joint assessment at 4, 12, 24 weeks
- Annual TB and hepatitis screening""",

    "MRN003": """## 1. Problem List / Drug Therapy Problems
- Atrial fibrillation: Anticoagulation needed to reduce stroke risk
- Renal impairment (CrCl 52): Dose verification required for apixaban

## 2. Goals (SMART Format)
- Maintain therapeutic anticoagulation without major bleeding events
- CrCl monitoring quarterly to reassess dose appropriateness

## 3. Pharmacist Interventions
- Counsel on twice-daily dosing adherence — missed dose protocol
- Review drug interactions (NSAIDs, aspirin)
- Educate on bleeding precautions and when to seek emergency care

## 4. Monitoring Plan & Lab Schedule
- Renal function (CrCl) every 3 months
- CBC annually or with clinical changes
- Follow-up at 1 month post-transition from warfarin""",

    "MRN004": """## 1. Problem List / Drug Therapy Problems
- Uncontrolled T2DM (A1C 9.2%): GLP-1 agonist added to regimen
- Obesity (BMI >35): Weight reduction target alongside glycemic control

## 2. Goals (SMART Format)
- Reduce A1C to <7.5% within 6 months
- Achieve 5-10% body weight reduction in 3 months

## 3. Pharmacist Interventions
- Counsel on weekly subcutaneous injection and dose escalation schedule
- Address GI side effects (nausea, vomiting) — take with food, start low dose
- Reinforce diet and exercise alongside medication

## 4. Monitoring Plan & Lab Schedule
- A1C at 3 and 6 months
- Fasting glucose self-monitoring weekly
- Renal function annually; lipid panel at 6 months""",

    "MRN005": """## 1. Problem List / Drug Therapy Problems
- PE with DVT: Anticoagulation required for minimum 3-6 months
- Comorbid AF: Long-term anticoagulation likely indicated

## 2. Goals (SMART Format)
- Prevent recurrent VTE with therapeutic anticoagulation
- No major bleeding events during treatment period

## 3. Pharmacist Interventions
- Counsel on once-daily dosing with evening meal for absorption
- Review bleeding risk factors and drug-drug interactions
- Educate on signs of recurrent DVT/PE requiring immediate care

## 4. Monitoring Plan & Lab Schedule
- Renal function at 1 month, then every 3-6 months
- CBC if bleeding suspected
- Follow-up at 4 weeks, then 3 months""",
}


class Command(BaseCommand):
    help = "Seed the database with mock patients, providers, orders, and care plans"

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding database...")

        for p in PATIENTS:
            Patient.objects.get_or_create(mrn=p["mrn"], defaults=p)

        for p in PROVIDERS:
            Provider.objects.get_or_create(npi=p["npi"], defaults=p)

        for o in ORDERS:
            patient = Patient.objects.get(mrn=o["patient_mrn"])
            provider = Provider.objects.get(npi=o["provider_npi"])

            order, created = Order.objects.get_or_create(
                patient=patient,
                medication=o["medication"],
                defaults={
                    "provider": provider,
                    "diagnosis": o["diagnosis"],
                    "additional_diagnoses": o["additional_diagnoses"],
                    "medication_history": o["medication_history"],
                    "medical_records": o["medical_records"],
                },
            )

            if created:
                CarePlan.objects.create(
                    order=order,
                    content=CARE_PLAN_CONTENT[o["patient_mrn"]],
                    status="completed",
                )

        self.stdout.write(self.style.SUCCESS(
            f"Done. {len(PATIENTS)} patients, {len(PROVIDERS)} providers, {len(ORDERS)} orders seeded."
        ))
