"""
Adapter for Clinic B — a small clinic that POSTs JSON orders.

Clinic B's field naming and formats differ from our internal standard:
  - full name in one field instead of first + last
  - dates as MM/DD/YYYY instead of ISO 8601
  - comma-separated strings instead of lists for diagnoses and medications
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime

from app.adapters import BaseIntakeAdapter
from app.exceptions import ValidationError
from app.schemas import InternalOrder, MedicationInfo, PatientInfo, ProviderInfo

logger = logging.getLogger(__name__)

# Clinic B's field names, documented in one place so renames are a one-liner
_FIELD = {
    "patient_id":       "pt_id",
    "full_name":        "pt_full_name",
    "dob":              "dob",
    "primary_dx":       "primary_dx",
    "secondary_dx":     "secondary_dx",
    "provider_name":    "provider_name",
    "provider_npi":     "provider_npi",
    "medication":       "medication",
    "prior_medications":"prior_medications",
    "notes":            "notes",
}


class ClinicBAdapter(BaseIntakeAdapter[str, dict]):
    """
    Converts Clinic B JSON → IntakeRecord(InternalOrder, raw_payload, ...).

    Example input:
        {
            "pt_id":             "P-00234",
            "pt_full_name":      "John Doe",
            "dob":               "01/15/1990",
            "primary_dx":        "Z79.899",
            "secondary_dx":      "E11.9, I10",
            "provider_name":     "Dr. Jane Smith",
            "provider_npi":      "1234567890",
            "medication":        "Humira 40mg/0.8mL",
            "prior_medications": "MTX 15mg weekly, Sulfasalazine",
            "notes":             "Moderate disease activity."
        }
    """

    SOURCE = "clinic_b"

    # ── parse ─────────────────────────────────────────────────────────────────

    def parse(self, raw: str) -> dict:
        """Decode JSON string → dict. Fails fast on malformed input."""
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValidationError(
                f"Clinic B: payload is not valid JSON — {exc}",
                code="CLINIC_B_INVALID_JSON",
            )

    # ── transform ─────────────────────────────────────────────────────────────

    def transform(self, parsed: dict) -> InternalOrder:
        """Map Clinic B field names and formats to InternalOrder."""
        return InternalOrder(
            patient=self._build_patient(parsed),
            provider=self._build_provider(parsed),
            medication=self._build_medication(parsed),
            source=self.SOURCE,
        )

    def _build_patient(self, d: dict) -> PatientInfo:
        first_name, last_name = self._split_full_name(
            d.get(_FIELD["full_name"], "")
        )
        return PatientInfo(
            mrn=d.get(_FIELD["patient_id"], ""),
            first_name=first_name,
            last_name=last_name,
            dob=self._parse_dob(d.get(_FIELD["dob"])),
        )

    def _build_provider(self, d: dict) -> ProviderInfo:
        return ProviderInfo(
            npi=d.get(_FIELD["provider_npi"], ""),
            name=d.get(_FIELD["provider_name"], ""),
        )

    def _build_medication(self, d: dict) -> MedicationInfo:
        return MedicationInfo(
            name=d.get(_FIELD["medication"], ""),
            primary_diagnosis=d.get(_FIELD["primary_dx"], ""),
            additional_diagnoses=self._split_csv(d.get(_FIELD["secondary_dx"], "")),
            medication_history=self._split_csv(d.get(_FIELD["prior_medications"], "")),
            patient_records=d.get(_FIELD["notes"], ""),
        )

    # ── validate ──────────────────────────────────────────────────────────────

    def validate(self, order: InternalOrder) -> None:
        """Enforce Clinic B's required fields and format rules."""
        errors: list[str] = []

        if not order.patient.mrn:
            errors.append("pt_id is required")

        if not order.patient.first_name or not order.patient.last_name:
            errors.append("pt_full_name must contain at least a first and last name")

        npi = order.provider.npi
        if not npi.isdigit() or len(npi) != 10:
            errors.append(f"provider_npi must be exactly 10 digits, got '{npi}'")

        if not order.medication.primary_diagnosis:
            errors.append("primary_dx is required")

        if errors:
            raise ValidationError(
                f"Clinic B validation failed: {'; '.join(errors)}",
                code="CLINIC_B_VALIDATION_FAILED",
                detail=errors,
            )

    # ── private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _split_full_name(full_name: str) -> tuple[str, str]:
        """'John Doe' → ('John', 'Doe')   |   'Mary Jane Watson' → ('Mary', 'Jane Watson')"""
        parts = full_name.strip().split(maxsplit=1)
        if len(parts) == 2:
            return parts[0], parts[1]
        return (parts[0], "") if parts else ("", "")

    @staticmethod
    def _parse_dob(raw_dob: str | None) -> date | None:
        """Parse Clinic B's MM/DD/YYYY date format."""
        if not raw_dob:
            return None
        try:
            return datetime.strptime(raw_dob, "%m/%d/%Y").date()
        except ValueError:
            raise ValidationError(
                f"Clinic B: invalid date '{raw_dob}', expected MM/DD/YYYY",
                code="CLINIC_B_INVALID_DATE",
            )

    @staticmethod
    def _split_csv(value: str) -> tuple[str, ...]:
        """'E11.9, I10' → ('E11.9', 'I10')   |   '' → ()"""
        return tuple(item.strip() for item in value.split(",") if item.strip())
