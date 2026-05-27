"""
Integration tests for patient duplicate detection via the HTTP API.
Tests go through the full Django request/response cycle.
process_careplan.delay is mocked so Celery never actually runs.
"""
import json
import pytest
from datetime import date
from django.test import Client

from app.models import Patient


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def post(client, base_payload):
    """Helper: POST to /api/careplan/generate/ and return the response."""
    def _post(overrides=None):
        payload = {**base_payload, **(overrides or {})}
        return client.post(
            "/api/careplan/generate/",
            data=json.dumps(payload),
            content_type="application/json",
        )
    return _post


# ── Happy path ────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestNewPatient:
    def test_returns_pending_and_careplan_id(self, post, mocker):
        mocker.patch("app.services.process_careplan")

        resp = post()

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "pending"
        assert "careplan_id" in body

    def test_patient_record_is_created(self, post, mocker):
        mocker.patch("app.services.process_careplan")

        post()

        assert Patient.objects.filter(mrn="INT001").exists()

    def test_celery_task_is_queued(self, post, mocker):
        mock_task = mocker.patch("app.services.process_careplan")

        post()

        mock_task.delay.assert_called_once()


@pytest.mark.django_db
class TestExistingPatientReuse:
    def test_same_mrn_same_details_reuses_patient(self, post, mocker, make_patient):
        mocker.patch("app.services.process_careplan")
        make_patient("INT001", "John", "Doe", date(1990, 1, 15))

        resp = post()

        assert resp.status_code == 200
        assert Patient.objects.filter(mrn="INT001").count() == 1  # no duplicate


# ── BlockError cases (409) ────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPatientBlockErrors:
    def test_mrn_first_name_conflict_returns_409(self, post, make_patient):
        make_patient("INT001", first_name="Jane")  # existing: Jane Doe

        resp = post()  # payload has: John Doe

        assert resp.status_code == 409
        body = resp.json()
        assert body["type"] == "block_error"
        assert body["code"] == "PATIENT_MRN_MISMATCH"
        assert "message" in body

    def test_mrn_last_name_conflict_returns_409(self, post, make_patient):
        make_patient("INT001", last_name="Smith")  # existing: John Smith

        resp = post()  # payload has: John Doe

        assert resp.status_code == 409
        assert resp.json()["code"] == "PATIENT_MRN_MISMATCH"

    def test_mrn_dob_conflict_returns_409(self, post, make_patient):
        make_patient("INT001", dob=date(2000, 5, 10))  # different DOB

        resp = post()  # payload has: 1990-01-15

        assert resp.status_code == 409
        assert resp.json()["code"] == "PATIENT_MRN_MISMATCH"

    def test_response_format_has_all_required_fields(self, post, make_patient):
        """Verify the unified error format: type, code, message, detail."""
        make_patient("INT001", first_name="Jane")

        body = post().json()

        assert set(body.keys()) >= {"type", "code", "message", "detail"}


# ── WarningException cases (200 + type=warning) ───────────────────────────────

@pytest.mark.django_db
class TestPatientDuplicateWarning:
    def test_different_mrn_same_name_dob_returns_warning(self, post, make_patient):
        make_patient("OTHER001", "John", "Doe", date(1990, 1, 15))

        resp = post()  # different MRN (INT001), same name+DOB

        assert resp.status_code == 200
        body = resp.json()
        assert body["type"] == "warning"
        assert body["code"] == "PATIENT_POSSIBLE_DUPLICATE"

    def test_warning_message_contains_existing_mrn(self, post, make_patient):
        make_patient("OTHER001", "John", "Doe", date(1990, 1, 15))

        body = post().json()

        assert "OTHER001" in body["message"]

    def test_no_warning_when_dob_omitted(self, post, mocker, make_patient):
        """If dob is not sent, name+DOB check is skipped → no warning."""
        mocker.patch("app.services.process_careplan")
        make_patient("OTHER001", "John", "Doe", None)

        resp = post({"patient_dob": None})

        assert resp.status_code == 200
        assert resp.json().get("type") != "warning"
