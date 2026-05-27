"""
Adapter registry.

To add a new data source:
  1. Create MySourceAdapter(BaseIntakeAdapter) in its own file
  2. Add one line to _REGISTRY below
  3. Done — no other file needs to change
"""
from app.adapters import BaseIntakeAdapter
from app.clinic_b_adapter import ClinicBAdapter
from app.exceptions import ValidationError
from app.hospital_a_adapter import HospitalAAdapter

_REGISTRY: dict[str, type[BaseIntakeAdapter]] = {
    "clinic_b":   ClinicBAdapter,
    "hospital_a": HospitalAAdapter,
    # "epic_ehr": EpicEhrAdapter,
}


def get_adapter(source: str) -> BaseIntakeAdapter:
    cls = _REGISTRY.get(source)
    if cls is None:
        known = ", ".join(sorted(_REGISTRY))
        raise ValidationError(
            f"Unknown data source '{source}'. Known sources: {known}",
            code="UNKNOWN_ADAPTER_SOURCE",
        )
    return cls()
