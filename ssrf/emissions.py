"""ITU emission designator helpers shared by the generators."""

from __future__ import annotations

import re
from typing import Optional

# ITU necessary-bandwidth prefix: digits around a decimal-point letter
# (H = Hz, K = kHz, M = MHz), e.g. 16K0 -> 16.0 kHz, 11K2 -> 11.2 kHz.
_BANDWIDTH_RE = re.compile(r"^(\d{0,3})([HKM])(\d{0,2})")

# ITU emission designator (5th symbol = type of modulation) -> SSRF mode.
# Only unambiguous analog-voice designators are mapped; digital/data emissions
# stay None because the designator alone can't distinguish DMR/P25/NXDN/etc.
_MODE_BY_DESIGNATOR = {
    "F3E": "FM",   # angle-modulated telephony (FM voice) -> 16K0F3E, 11K0F3E, ...
    "A3E": "AM",   # double-sideband AM telephony (aircraft band) -> 6K00A3E
    "J3E": "USB",  # single-sideband, suppressed carrier (upper by convention)
}


def bandwidth_khz(emission: Optional[str]) -> Optional[float]:
    """Necessary bandwidth in kHz from an ITU emission designator."""

    if not emission:
        return None
    match = _BANDWIDTH_RE.match(emission.strip().upper())
    if not match or not match.group(1):
        return None
    value = float(f"{match.group(1)}.{match.group(3) or 0}")
    scale = {"H": 0.001, "K": 1.0, "M": 1000.0}[match.group(2)]
    return (value * scale) or None


def mode_from_emission(emission: Optional[str]) -> Optional[str]:
    """Infer an SSRF mode from an ITU emission designator.

    The designator's 3-char modulation code is its final three characters
    (e.g. ``16K0F3E`` -> ``F3E``). Returns None for digital/data or unknown
    emissions, which downstream consumers treat as untyped.
    """

    if not emission:
        return None
    return _MODE_BY_DESIGNATOR.get(emission.strip().upper()[-3:])
