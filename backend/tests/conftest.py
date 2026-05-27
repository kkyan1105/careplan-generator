import pytest
from datetime import date


DOB = date(1990, 1, 15)
ALT_DOB = date(2000, 5, 10)


@pytest.fixture
def make_patient():
    """Factory: create Patient rows directly in the test DB."""
    from app.models import Patient

    def _factory(mrn, first_name="John", last_name="Doe", dob=DOB):
        return Patient.objects.create(
            mrn=mrn, first_name=first_name, last_name=last_name, dob=dob
        )

    return _factory


@pytest.fixture
def base_payload():
    """Minimal valid POST payload for /api/careplan/generate/."""
    return {
        "patient_first_name": "John",
        "patient_last_name": "Doe",
        "patient_mrn": "INT001",
        "patient_dob": "1990-01-15",
        "primary_diagnosis": "Z79.899",
        "referring_provider_name": "Dr. Smith",
        "referring_provider_npi": "1234567890",
        "medication_name": "Humira",
    }
