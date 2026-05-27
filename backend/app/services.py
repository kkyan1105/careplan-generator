from django.utils import timezone

from app.exceptions import BlockError, WarningException
from app.models import Patient, Provider, Order, CarePlan
from app.tasks import process_careplan


def _resolve_provider(npi, name):
    try:
        provider = Provider.objects.get(npi=npi)
        if provider.name != name:
            raise BlockError(
                f"NPI {npi} is already registered to '{provider.name}', not '{name}'. "
                f"NPI is a nationally unique identifier and cannot be reassigned.",
                code="PROVIDER_NPI_CONFLICT",
            )
        return provider
    except Provider.DoesNotExist:
        return Provider.objects.create(npi=npi, name=name)


def _resolve_patient(mrn, first_name, last_name, dob):
    try:
        patient = Patient.objects.get(mrn=mrn)
        name_match = patient.first_name == first_name and patient.last_name == last_name
        dob_match = patient.dob == dob
        if not name_match or not dob_match:
            raise BlockError(
                f"MRN {mrn} already exists but the provided name/DOB doesn't match the record. "
                f"Existing: {patient.first_name} {patient.last_name} / {patient.dob}.",
                code="PATIENT_MRN_MISMATCH",
            )
        return patient
    except Patient.DoesNotExist:
        pass

    if dob is not None:
        existing = Patient.objects.filter(
            first_name=first_name, last_name=last_name, dob=dob
        ).exclude(mrn=mrn).first()
        if existing:
            raise WarningException(
                f"A patient named {first_name} {last_name} with DOB {dob} already exists "
                f"under a different MRN ({existing.mrn}).",
                code="PATIENT_POSSIBLE_DUPLICATE",
            )

    return Patient.objects.create(
        mrn=mrn, first_name=first_name, last_name=last_name, dob=dob
    )


def _check_duplicate_order(patient, medication, confirm):
    today = timezone.now().date()

    same_day_exists = Order.objects.filter(
        patient=patient,
        medication=medication,
        created_at__date=today,
    ).exists()
    if same_day_exists:
        raise BlockError(
            f"An order for '{medication}' already exists today for this patient.",
            code="DUPLICATE_SAME_DAY_ORDER",
        )

    if not confirm:
        previous_exists = Order.objects.filter(
            patient=patient,
            medication=medication,
        ).exists()
        if previous_exists:
            raise WarningException(
                f"This patient already has a previous order for '{medication}'. "
                f"Pass confirm=true to proceed anyway.",
                code="DUPLICATE_PREVIOUS_ORDER",
            )


def create_careplan(data):
    confirm = data.get("confirm", False)

    provider = _resolve_provider(
        npi=data["referring_provider_npi"],
        name=data["referring_provider_name"],
    )

    patient = _resolve_patient(
        mrn=data["patient_mrn"],
        first_name=data["patient_first_name"],
        last_name=data["patient_last_name"],
        dob=data.get("patient_dob"),
    )

    _check_duplicate_order(
        patient=patient,
        medication=data["medication_name"],
        confirm=confirm,
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
