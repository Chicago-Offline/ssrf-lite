"""Channel plans that carry the convention's squelch and digital parameters.

A channel plan records an agreed channel definition. Where that agreement
includes a CTCSS tone (NIFOG interop) or a DMR color code and timeslot (an
agreed simplex channel), the plan is often the only record carrying it --
there may be no deployed station to hang an rf_chain off. See spec 2.6.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from generate_ssrf_codeplug import _records_from_plan_channel
from ssrf.models.pydantic_models import ChannelPlanChannel


def _records(channel: ChannelPlanChannel) -> list[dict[str, object]]:
    return _records_from_plan_channel(
        SimpleNamespace(service=None),
        SimpleNamespace(service="interop"),
        channel,
    )


def test_mode_is_optional() -> None:
    assert ChannelPlanChannel(name="Ch 06", freq_mhz=156.3).mode is None


def test_analog_tone_reaches_the_record() -> None:
    (record,) = _records(
        ChannelPlanChannel(
            name="VTAC11",
            freq_mhz=151.1375,
            emission="11K2F3E",
            mode={"type": "FM", "ctcss_tx_hz": 156.7, "ctcss_rx_hz": 156.7},
        )
    )

    assert record["ctcss"] == pytest.approx(156.7)
    assert record["mode"] == "FM"
    assert record["color_code"] is None


def test_dmr_color_code_and_timeslots_reach_the_record() -> None:
    (record,) = _records(
        ChannelPlanChannel(
            name="DMR Simplex",
            freq_mhz=441.0,
            mode={"type": "DMR", "color_code": 1, "timeslots": [1, 2]},
        )
    )

    assert record["color_code"] == 1
    assert record["timeslots"] == [1, 2]
    assert record["mode"] == "DMR"


def test_dcs_code_and_polarity_reach_the_record() -> None:
    (record,) = _records(
        ChannelPlanChannel(
            name="Yard 1",
            freq_mhz=464.5,
            mode={"type": "FM", "dcs_tx_code": "023", "dcs_tx_polarity": "N"},
        )
    )

    assert record["dcs"] == "023"
    assert record["dcs_polarity"] == "N"


def test_channel_without_mode_still_has_null_tone_keys() -> None:
    (record,) = _records(
        ChannelPlanChannel(name="Ch 06", freq_mhz=156.3, emission="16K0F3E")
    )

    assert record["ctcss"] is None
    assert record["dcs"] is None
    assert record["color_code"] is None
    assert record["timeslots"] is None
    assert record["mode"] == "FM"


def test_per_emission_mode_wins_over_channel_mode() -> None:
    records = _records(
        ChannelPlanChannel(
            name="CB 01",
            freq_mhz=26.965,
            mode={"type": "AM", "ctcss_tx_hz": 100.0},
            emissions=[
                {"emission": "6K00A3E", "mode": "AM"},
                {"emission": "4K00J3E", "mode": "USB"},
            ],
        )
    )

    modes = [r["mode"] for r in records]
    assert modes == ["AM", "USB"]
    # The channel-level tone still applies to every emission's record.
    assert all(r["ctcss"] == pytest.approx(100.0) for r in records)


def test_mode_rejects_unknown_keys() -> None:
    with pytest.raises(ValidationError):
        ChannelPlanChannel(name="bad", freq_mhz=1.0, mode={"type": "FM", "bogus": 1})
