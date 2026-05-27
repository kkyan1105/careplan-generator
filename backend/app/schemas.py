"""
Internal canonical data format.

All inbound data sources (hospitals, clinics, EHRs) must transform their
payloads into InternalOrder before any business logic runs. Services and
duplicate detection only operate on this type — never on raw dicts.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class PatientInfo:
    mrn: str
    first_name: str
    last_name: str
    dob: date | None = None


@dataclass(frozen=True)
class ProviderInfo:
    npi: str
    name: str


@dataclass(frozen=True)
class MedicationInfo:
    name: str
    primary_diagnosis: str               # ICD-10 code
    additional_diagnoses: tuple[str, ...] = ()
    medication_history: tuple[str, ...] = ()
    patient_records: str = ""


@dataclass(frozen=True)
class InternalOrder:
    patient: PatientInfo
    provider: ProviderInfo
    medication: MedicationInfo
    source: str = ""      # origin system: "epic", "hospital_a", "web_form", etc.
    confirm: bool = False  # True = bypass soft duplicate warnings
