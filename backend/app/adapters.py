"""
Adapter layer: converts external data formats into InternalOrder.

Each data source (hospital, EHR, web form) implements BaseIntakeAdapter.
The pipeline is always:  raw data → parse → transform → validate → InternalOrder
Business logic only ever receives an InternalOrder — never raw external data.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from app.exceptions import ValidationError
from app.schemas import InternalOrder

RawT = TypeVar("RawT")      # raw input: bytes, str, dict — depends on source
ParsedT = TypeVar("ParsedT")  # intermediate form after parsing, before transform


@dataclass(frozen=True)
class IntakeRecord:
    """
    What process() returns: the transformed order plus everything needed to
    reproduce or investigate what happened.
    """
    order: InternalOrder
    raw_payload: Any          # the original input, preserved verbatim
    source: str
    received_at: datetime     # UTC timestamp of when process() was called


class BaseIntakeAdapter(ABC, Generic[RawT, ParsedT]):
    """
    Template for all intake adapters.

    Subclasses must implement parse(), transform(), and validate().
    Callers use process() — the fixed pipeline that chains all three.

    Type parameters:
        RawT    — the raw input type this adapter accepts (e.g. bytes for HL7,
                  dict for JSON, str for CSV)
        ParsedT — the intermediate structure parse() returns before transform()
                  converts it to InternalOrder (can be dict, a source-specific
                  dataclass, or the same as RawT if no pre-processing is needed)
    """

    @abstractmethod
    def parse(self, raw: RawT) -> ParsedT:
        """
        Extract fields from the raw payload.

        Handles format-specific concerns: JSON decoding, HL7 segment splitting,
        CSV parsing, XML traversal. Should not contain business logic.
        Raises ValidationError if the raw payload is malformed or unreadable.
        """

    @abstractmethod
    def transform(self, parsed: ParsedT) -> InternalOrder:
        """
        Map source-specific field names and structures to InternalOrder.

        This is where "hospital_patient_id" becomes PatientInfo.mrn,
        "prescriber_npi_number" becomes ProviderInfo.npi, and so on.
        Raises ValidationError if required fields are missing after mapping.
        """

    @abstractmethod
    def validate(self, order: InternalOrder) -> None:
        """
        Enforce business rules on the fully-formed InternalOrder.

        Examples: NPI must be 10 digits, MRN must match expected format,
        ICD-10 code must be non-empty. Raises ValidationError on failure.
        Returns None on success.
        """

    # ── Template method ───────────────────────────────────────────────────────

    def process(self, raw: RawT) -> IntakeRecord:
        """
        Public entry point. Runs parse → transform → validate in sequence.
        Returns IntakeRecord, which bundles the InternalOrder with the original
        raw payload and a timestamp — ready for audit logging or debugging.
        Any step may raise ValidationError; callers handle it once, here.
        """
        received_at = datetime.now(timezone.utc)
        parsed = self.parse(raw)
        order = self.transform(parsed)
        self.validate(order)
        return IntakeRecord(
            order=order,
            raw_payload=raw,
            source=order.source,
            received_at=received_at,
        )
