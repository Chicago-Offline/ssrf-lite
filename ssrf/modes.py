"""Human-readable rendering of a Mode block, shared by the generators."""

from __future__ import annotations

from typing import Any, Dict, List


def mode_summary(mode: Any) -> Dict[str, Any]:
    """``{"type": ..., "detail": ...}`` -- tones, colour code, NAC, RAN in one line."""

    out: Dict[str, Any] = {"type": mode.type}
    details: List[str] = []
    if mode.ctcss_tx_hz:
        if mode.ctcss_rx_hz and mode.ctcss_rx_hz != mode.ctcss_tx_hz:
            details.append(f"CTCSS {mode.ctcss_tx_hz:g}/{mode.ctcss_rx_hz:g} Hz")
        else:
            details.append(f"CTCSS {mode.ctcss_tx_hz:g} Hz")
    elif mode.ctcss_rx_hz:
        details.append(f"CTCSS rx {mode.ctcss_rx_hz:g} Hz")
    if mode.dcs_tx_code is not None:
        dcs = f"DCS {mode.dcs_tx_code} {mode.dcs_tx_polarity}"
        if mode.dcs_rx_code is not None and (
            mode.dcs_rx_code != mode.dcs_tx_code
            or mode.dcs_rx_polarity != mode.dcs_tx_polarity
        ):
            dcs += f"/{mode.dcs_rx_code} {mode.dcs_rx_polarity}"
        details.append(dcs)
    elif mode.dcs_rx_code is not None:
        details.append(f"DCS rx {mode.dcs_rx_code} {mode.dcs_rx_polarity}")
    if mode.color_code is not None:
        cc = f"CC{mode.color_code}"
        if mode.timeslots:
            cc += " TS" + ",".join(str(t) for t in mode.timeslots)
        details.append(cc)
    if mode.nac is not None:
        details.append(f"NAC ${mode.nac:03X}")
    if mode.nxdn_ran is not None:
        details.append(f"RAN {mode.nxdn_ran}")
    out["detail"] = " · ".join(details)
    return out
