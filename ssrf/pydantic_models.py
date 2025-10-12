"""Pydantic models for the SSRF-Lite reference schema.

These models intentionally reflect the v0.5.3 specification located in
``ssrf/_schema/SSRF-Lite-Spec.md``. They do not include legacy or policy-layer
fields that appeared in historical data files. Use the helper functions at the
bottom of this file to validate YAML documents against the schema.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing import Literal


BASE_DIR = Path(__file__).parent
_SERVICES_PATH = BASE_DIR / "_taxonomies" / "services.yaml"


def _load_service_ids() -> Tuple[str, ...]:
    try:
        with _SERVICES_PATH.open("r", encoding="utf-8") as handle:
            doc = yaml.safe_load(handle) or {}
    except FileNotFoundError:
        return ()
    except Exception:
        return ()

    services: List[str] = []
    entries = doc.get("services", [])
    if isinstance(entries, list):
        for entry in entries:
            if isinstance(entry, dict):
                svc_id = entry.get("id")
                if isinstance(svc_id, str) and svc_id.strip():
                    services.append(svc_id.strip().lower())
    return tuple(sorted(set(services)))


SERVICE_IDS: Tuple[str, ...] = _load_service_ids()
ALLOWED_SERVICE_VALUES: Tuple[str, ...] = SERVICE_IDS or (
    "amateur",
    "gmrs",
    "murs",
    "noaa_weather_radio",
    "pmr446",
    "public_safety_part90",
    "business_itinerant_part90",
    "railroad_aar",
)

_literal_globals = {"Literal": Literal}
_service_literal_args = ", ".join(repr(val) for val in ALLOWED_SERVICE_VALUES)
ServiceLiteral = eval(f"Literal[{_service_literal_args}]", _literal_globals)


SUPPORTED_MODES: Tuple[str, ...] = (
    "AM",
    "APRS",
    "C4FM",
    "CW",
    "DMR",
    "D-STAR",
    "DSD",
    "FM",
    "LSB",
    "NFM",
    "NXDN",
    "PACKET",
    "P25",
    "USB",
)
_mode_literal_args = ", ".join(repr(val) for val in SUPPORTED_MODES)
ModeLiteral = eval(f"Literal[{_mode_literal_args}]", _literal_globals)


def _normalize_service_optional(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        candidate = value.strip()
    else:
        candidate = str(value).strip()
    if not candidate:
        return None
    normalized = candidate.lower()
    if normalized not in ALLOWED_SERVICE_VALUES:
        raise ValueError(
            f"Unknown service '{candidate}'. Expected one of: {', '.join(ALLOWED_SERVICE_VALUES)}"
        )
    return normalized


def _normalize_service_required(value: Any) -> str:
    normalized = _normalize_service_optional(value)
    if normalized is None:
        raise ValueError(
            "service is required and must be one of the defined taxonomy ids"
        )
    return normalized


def _normalize_mode(value: Any) -> str:
    if not isinstance(value, str):
        value = str(value)
    candidate = value.strip()
    if not candidate:
        raise ValueError("mode type must be a non-empty string")
    normalized = candidate.upper()
    if normalized == "DSTAR":
        normalized = "D-STAR"
    if normalized not in SUPPORTED_MODES:
        raise ValueError(
            f"Unsupported mode '{candidate}'. Expected one of: {', '.join(SUPPORTED_MODES)}"
        )
    return normalized


def _normalize_optional_string(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        candidate = value.strip()
    else:
        candidate = str(value).strip()
    return candidate or None


class Organization(BaseModel):
    """Owning or operating body."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str


class Location(BaseModel):
    """Geographic site with optional latitude/longitude."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    lat: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    lon: Optional[float] = Field(default=None, ge=-180.0, le=180.0)


class Station(BaseModel):
    """Logical station, typically tied to an organization and location."""

    model_config = ConfigDict(extra="forbid")

    id: str
    call_sign: Optional[str] = None
    organization_id: Optional[str] = None
    location_id: Optional[str] = None
    service: Optional[str] = None

    @field_validator("call_sign", mode="before")
    @classmethod
    def _normalize_call_sign(cls, value: Any) -> Optional[str]:
        return _normalize_optional_string(value)

    @field_validator("service", mode="before")
    @classmethod
    def _normalize_service(cls, value: Any) -> Optional[str]:
        return _normalize_service_optional(value)


class Antenna(BaseModel):
    """Antenna definition with optional gain and height references."""

    model_config = ConfigDict(extra="forbid")

    id: str
    station_id: str
    name: Optional[str] = None
    gain_dbi: Optional[float] = None
    height_agl_m: Optional[float] = Field(default=None, ge=0.0)
    height_amsl_m: Optional[float] = Field(default=None, ge=0.0)


class Transmitter(BaseModel):
    """Transmitter metadata (frequency, power, emission designator)."""

    model_config = ConfigDict(extra="forbid")

    freq_mhz: Optional[float] = Field(default=None, gt=0)
    power_w: Optional[float] = Field(default=None, gt=0)
    emission: Optional[str] = None
    bandwidth_khz: Optional[float] = Field(default=None, gt=0)


class Receiver(BaseModel):
    """Receiver metadata (frequency and sensitivity)."""

    model_config = ConfigDict(extra="forbid")

    freq_mhz: float = Field(gt=0)
    sensitivity_dbm: Optional[float] = None


class Mode(BaseModel):
    """Mode definition capturing analogue or digital specifics."""

    model_config = ConfigDict(extra="forbid")

    type: str = Field(description="Modulation or mode (e.g., FM, DMR)")
    ctcss_tx_hz: Optional[float] = Field(default=None, gt=0)
    ctcss_rx_hz: Optional[float] = Field(default=None, gt=0)
    dcs_tx_code: Optional[Union[str, int]] = None
    dcs_rx_code: Optional[Union[str, int]] = None
    color_code: Optional[int] = Field(default=None, ge=0, le=15)
    timeslots: Optional[List[int]] = None
    notes: Optional[str] = None

    @field_validator("type", mode="before")
    @classmethod
    def _normalize_type_field(cls, value: Any) -> str:
        return _normalize_mode(value)


class RFChain(BaseModel):
    """Bundled transmitter + receiver + mode for a station."""

    model_config = ConfigDict(extra="forbid")

    id: str
    station_id: str
    antenna_id: Optional[str] = None
    tx: Transmitter
    rx: Receiver
    mode: Mode


class ChannelPlanChannel(BaseModel):
    """Single entry in a channel plan."""

    model_config = ConfigDict(extra="forbid")

    name: str
    freq_mhz: float = Field(gt=0)
    notes: Optional[str] = None
    emission: Optional[str] = None
    bandwidth_khz: Optional[float] = Field(default=None, gt=0)


class ChannelPlan(BaseModel):
    """Collection of reusable channels (e.g., NOAA, marine)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    channels: List[ChannelPlanChannel]
    service: Optional[str] = None

    @field_validator("service", mode="before")
    @classmethod
    def _normalize_service(cls, value: Any) -> Optional[str]:
        return _normalize_service_optional(value)


class Authorization(BaseModel):
    """License or permission data."""

    model_config = ConfigDict(extra="forbid")

    id: str
    authority: str
    service: str
    class_field: Optional[str] = Field(default=None, alias="class")
    identifier: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("service", mode="before")
    @classmethod
    def _normalize_service(cls, value: Any) -> str:
        return _normalize_service_required(value)

    @property
    def class_(self) -> Optional[str]:
        """Expose the authorization class without colliding with the keyword."""

        return self.class_field


class Contact(BaseModel):
    """DMR talkgroup or similar contact directory entry."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    kind: str = Field(description="Group, Private, or AllCall")
    number: Optional[int] = Field(default=None, ge=0)
    default_timeslot: Optional[int] = None
    notes: Optional[str] = None


class Assignment(BaseModel):
    """Link between RF resources and an operational use."""

    model_config = ConfigDict(extra="forbid")

    id: str
    rf_chain_id: Optional[str] = None
    channel_plan_id: Optional[str] = None
    channel_name: Optional[str] = None
    usage: str
    service: Optional[str] = None
    authorization_id: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("service", mode="before")
    @classmethod
    def _normalize_service(cls, value: Any) -> Optional[str]:
        return _normalize_service_optional(value)


class SSRFReference(BaseModel):
    """Top-level SSRF-Lite reference document."""

    model_config = ConfigDict(extra="forbid")

    organizations: List[Organization] = Field(default_factory=list)
    locations: List[Location] = Field(default_factory=list)
    stations: List[Station] = Field(default_factory=list)
    antennas: List[Antenna] = Field(default_factory=list)
    rf_chains: List[RFChain] = Field(default_factory=list)
    channel_plans: List[ChannelPlan] = Field(default_factory=list)
    authorizations: List[Authorization] = Field(default_factory=list)
    contacts: List[Contact] = Field(default_factory=list)
    assignments: List[Assignment] = Field(default_factory=list)


def _extract_reference_payload(data: Any) -> Dict[str, Any]:
    """Return the payload that should feed :class:`SSRFReference`."""

    if not isinstance(data, dict):
        raise TypeError("SSRF documents must be mappings at the top level")

    if "ssrf_lite" in data and not isinstance(data["ssrf_lite"], dict):
        raise TypeError("'ssrf_lite' key must point to a mapping")

    allowed_keys = {
        "organizations",
        "locations",
        "stations",
        "antennas",
        "rf_chains",
        "channel_plans",
        "authorizations",
        "contacts",
        "assignments",
    }

    filtered: Dict[str, Any] = {
        key: value for key, value in data.items() if key in allowed_keys
    }

    assignments_block = filtered.get("assignments")
    if isinstance(assignments_block, list):
        cleaned_assignments: List[Dict[str, Any]] = []
        for entry in assignments_block:
            if not isinstance(entry, dict):
                continue
            cleaned = dict(entry)
            cleaned.pop("codeplug", None)
            cleaned.pop("zones", None)
            cleaned.pop("scan", None)
            if "comment" in cleaned and "notes" not in cleaned:
                cleaned["notes"] = cleaned.pop("comment")
            cleaned_assignments.append(cleaned)
        filtered["assignments"] = cleaned_assignments

    channel_plans_block = filtered.get("channel_plans")
    if isinstance(channel_plans_block, list):
        cleaned_plans: List[Dict[str, Any]] = []
        for plan in channel_plans_block:
            if not isinstance(plan, dict):
                continue
            plan_copy = dict(plan)
            channels = plan_copy.get("channels")
            if isinstance(channels, list):
                new_channels: List[Dict[str, Any]] = []
                for ch in channels:
                    if not isinstance(ch, dict):
                        continue
                    channel_copy = {
                        key: ch[key]
                        for key in (
                            "name",
                            "freq_mhz",
                            "notes",
                            "emission",
                            "bandwidth_khz",
                        )
                        if key in ch
                    }
                    new_channels.append(channel_copy)
                plan_copy["channels"] = new_channels
            cleaned_plans.append(plan_copy)
        filtered["channel_plans"] = cleaned_plans

    return filtered


def load_ssrf_document(path: Union[str, Path]) -> SSRFReference:
    """Load and validate a single SSRF-Lite YAML document."""

    resolved = Path(path)
    with resolved.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    payload = _extract_reference_payload(raw)
    return SSRFReference.model_validate(payload)


def load_multiple(paths: Sequence[Union[str, Path]]) -> List[SSRFReference]:
    """Validate several SSRF-Lite documents in order."""

    documents: List[SSRFReference] = []
    for path in paths:
        documents.append(load_ssrf_document(path))
    return documents


def validate_data(data: Dict[str, Any]) -> SSRFReference:
    """Validate an in-memory mapping against the SSRF-Lite schema."""

    payload = _extract_reference_payload(data)
    return SSRFReference.model_validate(payload)


__all__ = [
    "Assignment",
    "Antenna",
    "Authorization",
    "ChannelPlan",
    "ChannelPlanChannel",
    "Contact",
    "Location",
    "Mode",
    "Organization",
    "RFChain",
    "Receiver",
    "SSRFReference",
    "Station",
    "Transmitter",
    "load_multiple",
    "load_ssrf_document",
    "validate_data",
]
