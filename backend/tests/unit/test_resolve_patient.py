"""
Unit tests for _resolve_patient() in services.py.
Tests call the service function directly against the test DB — no HTTP layer.
"""
import pytest
from datetime import date

from app.exceptions import BlockError, WarningException
from app.models import Patient
from app.services import _resolve_patient

DOB = date(1990, 1, 15)
ALT_DOB = date(2000, 5, 10)


@pytest.mark.django_db
class TestResolvePatientNewPatient:
    """Cases where no matching MRN exists → patient is created."""

    def test_creates_patient_when_mrn_not_found(self):
        patient = _resolve_patient("MRN001", "John", "Doe", DOB)

        assert patient.mrn == "MRN001"
        assert patient.first_name == "John"
        assert patient.dob == DOB
        assert Patient.objects.filter(mrn="MRN001").count() == 1

    def test_creates_patient_without_dob(self):
        """dob=None is valid; patient is created with no dob."""
        patient = _resolve_patient("MRN001", "John", "Doe", None)

        assert patient.mrn == "MRN001"
        assert patient.dob is None

    def test_accepts_dob_as_string(self):
        """API passes dob as 'YYYY-MM-DD' string; should be parsed and stored."""
        patient = _resolve_patient("MRN001", "John", "Doe", "1990-01-15")

        assert patient.dob == DOB

    def test_no_name_dob_clash_creates_new_patient(self, make_patient):
        """Different name+DOB exists under another MRN → no warning, new patient created."""
        make_patient("MRN001", "Jane", "Smith", ALT_DOB)

        patient = _resolve_patient("MRN002", "John", "Doe", DOB)

        assert patient.mrn == "MRN002"
        assert Patient.objects.count() == 2


@pytest.mark.django_db
class TestResolvePatientExistingMrn:
    """Cases where MRN already exists in the DB."""

    def test_reuses_patient_when_all_fields_match(self, make_patient):
        existing = make_patient("MRN001", "John", "Doe", DOB)

        result = _resolve_patient("MRN001", "John", "Doe", DOB)

        assert result.id == existing.id
        assert Patient.objects.count() == 1  # no duplicate created

    def test_reuses_patient_dob_passed_as_string(self, make_patient):
        """Same scenario via the real API path: dob arrives as string."""
        existing = make_patient("MRN001", "John", "Doe", DOB)

        result = _resolve_patient("MRN001", "John", "Doe", "1990-01-15")

        assert result.id == existing.id

    def test_blocks_when_first_name_differs(self, make_patient):
        make_patient("MRN001", "John", "Doe", DOB)

        with pytest.raises(BlockError) as exc:
            _resolve_patient("MRN001", "Jane", "Doe", DOB)

        assert exc.value.code == "PATIENT_MRN_MISMATCH"
        assert exc.value.http_status == 409

    def test_blocks_when_last_name_differs(self, make_patient):
        make_patient("MRN001", "John", "Doe", DOB)

        with pytest.raises(BlockError) as exc:
            _resolve_patient("MRN001", "John", "Smith", DOB)

        assert exc.value.code == "PATIENT_MRN_MISMATCH"

    def test_blocks_when_dob_differs(self, make_patient):
        make_patient("MRN001", "John", "Doe", DOB)

        with pytest.raises(BlockError) as exc:
            _resolve_patient("MRN001", "John", "Doe", ALT_DOB)

        assert exc.value.code == "PATIENT_MRN_MISMATCH"

    def test_blocks_when_both_name_and_dob_differ(self, make_patient):
        make_patient("MRN001", "John", "Doe", DOB)

        with pytest.raises(BlockError) as exc:
            _resolve_patient("MRN001", "Jane", "Smith", ALT_DOB)

        assert exc.value.code == "PATIENT_MRN_MISMATCH"

    def test_block_error_message_contains_existing_name(self, make_patient):
        make_patient("MRN001", "John", "Doe", DOB)

        with pytest.raises(BlockError) as exc:
            _resolve_patient("MRN001", "Jane", "Doe", DOB)

        assert "John Doe" in exc.value.message


@pytest.mark.django_db
class TestResolvePatientNameDobDuplicate:
    """Cases where MRN is new but name+DOB matches an existing patient."""

    def test_warns_when_same_name_and_dob_under_different_mrn(self, make_patient):
        make_patient("MRN001", "John", "Doe", DOB)

        with pytest.raises(WarningException) as exc:
            _resolve_patient("MRN002", "John", "Doe", DOB)

        assert exc.value.code == "PATIENT_POSSIBLE_DUPLICATE"
        assert exc.value.http_status == 200

    def test_warning_message_contains_existing_mrn(self, make_patient):
        make_patient("MRN001", "John", "Doe", DOB)

        with pytest.raises(WarningException) as exc:
            _resolve_patient("MRN002", "John", "Doe", DOB)

        assert "MRN001" in exc.value.message

    def test_no_warning_when_dob_is_none(self, make_patient):
        """dob=None skips the name+DOB check entirely — no warning raised."""
        make_patient("MRN001", "John", "Doe", None)

        patient = _resolve_patient("MRN002", "John", "Doe", None)

        assert patient.mrn == "MRN002"
        assert Patient.objects.count() == 2

    def test_no_warning_when_name_differs_same_dob(self, make_patient):
        """Same DOB but different name → not a duplicate, patient created."""
        make_patient("MRN001", "Jane", "Doe", DOB)

        patient = _resolve_patient("MRN002", "John", "Doe", DOB)

        assert patient.mrn == "MRN002"
