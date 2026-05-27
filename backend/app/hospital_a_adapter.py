"""
Adapter for Hospital A (St. Mary's) — nested JSON, ISO dates, arrays for lists.

Key differences from Clinic B:
  - all fields nested under "order_info"
  - first/last name are separate fields (no splitting needed)
  - date_of_birth is ISO 8601 (YYYY-MM-DD) not MM/DD/YYYY
  - diagnoses and medication history arrive as JSON arrays, not CSV strings
  - NPI field is called "license_id"
"""
from __future__ import annotations

import json
from datetime import date

from app.adapters import BaseIntakeAdapter
from app.exceptions import ValidationError
from app.schemas import InternalOrder, MedicationInfo, PatientInfo, ProviderInfo


class HospitalAAdapter(BaseIntakeAdapter[str, dict]):
    """
    Example input:
        {
          "order_info": {
            "patient": {
              "record_number": "SM-98765",
              "surname":       "Johnson",
              "given_name":    "Emily",
              "date_of_birth": "1985-03-22"
            },
            "prescriber": {
              "license_id": "9876543210",
              "full_name":  "Dr. Robert Chen MD"
            },
            "rx": {
              "drug_name":          "Enbrel 50mg",
              "icd10_primary":      "M06.9",
              "icd10_secondary":    ["M05.79", "M79.3"],
              "previous_therapies": ["Humira", "Methotrexate"],
              "clinical_summary":   "Patient with established RA."
            }
          }
        }
    """

    SOURCE = "hospital_a"

    # ── parse ─────────────────────────────────────────────────────────────────

    def parse(self, raw: str) -> dict:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValidationError(
                f"Hospital A: payload is not valid JSON — {exc}",
                code="HOSPITAL_A_INVALID_JSON",
            )
        if "order_info" not in data:
            raise ValidationError(
                "Hospital A: expected top-level key 'order_info' not found",
                code="HOSPITAL_A_MISSING_ROOT",
            )
        return data["order_info"]  # unwrap once here; transform sees the inner dict

    # ── transform ─────────────────────────────────────────────────────────────

    def transform(self, parsed: dict) -> InternalOrder:
        pt = parsed.get("patient", {})
        rx = parsed.get("rx", {})
        prescriber = parsed.get("prescriber", {})

        return InternalOrder(
            patient=PatientInfo(
                mrn=pt.get("record_number", ""),
                first_name=pt.get("given_name", ""),   # already split — no work needed
                last_name=pt.get("surname", ""),
                dob=self._parse_dob(pt.get("date_of_birth")),
            ),
            provider=ProviderInfo(
                npi=prescriber.get("license_id", ""),  # different key name
                name=prescriber.get("full_name", ""),
            ),
            medication=MedicationInfo(
                name=rx.get("drug_name", ""),
                primary_diagnosis=rx.get("icd10_primary", ""),
                additional_diagnoses=tuple(rx.get("icd10_secondary", [])),   # already a list
                medication_history=tuple(rx.get("previous_therapies", [])),  # already a list
                patient_records=rx.get("clinical_summary", ""),
            ),
            source=self.SOURCE,
        )

    # ── validate ──────────────────────────────────────────────────────────────

    def validate(self, order: InternalOrder) -> None:
        errors: list[str] = []

        if not order.patient.mrn:
            errors.append("patient.record_number is required")

        if not order.patient.first_name or not order.patient.last_name:
            errors.append("patient.given_name and patient.surname are required")

        npi = order.provider.npi
        if not npi.isdigit() or len(npi) != 10:
            errors.append(f"prescriber.license_id must be exactly 10 digits, got '{npi}'")

        if not order.medication.primary_diagnosis:
            errors.append("rx.icd10_primary is required")

        if errors:
            raise ValidationError(
                f"Hospital A validation failed: {'; '.join(errors)}",
                code="HOSPITAL_A_VALIDATION_FAILED",
                detail=errors,
            )

    # ── private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _parse_dob(raw_dob: str | None) -> date | None:
        """Hospital A sends ISO 8601: YYYY-MM-DD."""
        if not raw_dob:
            return None
        try:
            return date.fromisoformat(raw_dob)
        except ValueError:
            raise ValidationError(
                f"Hospital A: invalid date '{raw_dob}', expected YYYY-MM-DD",
                code="HOSPITAL_A_INVALID_DATE",
            )
