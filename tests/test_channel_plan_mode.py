"""Channel plans that carry a Mode: regulatory tones and shared digital params."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from generate_ssrf_codeplug import _records_from_plan_channel
from ssrf.models.pydantic_models import ChannelPlan, ChannelPlanChannel, validate_data


def _record(channel: ChannelPlanChannel) -> dict[str, object]:
    records = _records_from_plan_channel(
        SimpleNamespace(service=None), SimpleNamespace(service=None), channel
    )
    assert len(records) == 1
    return records[0]


def test_simplex_tone_is_encoded_for_the_radio() -> None:
    record = _record(
        ChannelPlanChannel(
            name="VCALL10",
            freq_mhz=155.7525,
            emission="11K0F3E",
            mode={"type": "FM", "ctcss_tx_hz": 156.7, "ctcss_rx_hz": 156.7},
        )
    )

    assert record["mode"] == "FM"
    assert record["ctcss"] == 156.7
    assert record["dcs"] is None


def test_repeater_pair_uses_the_station_perspective() -> None:
    """Mobile TX tone is what the repeater *requires*, so it lives in ctcss_rx_hz."""

    record = _record(
        ChannelPlanChannel(
            name="VTAC36",
            freq_mhz=151.1375,
            rx_freq_mhz=159.4725,
            emission="11K0F3E",
            mode={"type": "FM", "ctcss_tx_hz": 156.7, "ctcss_rx_hz": 136.5},
        )
    )

    assert record["rx_mhz"] == 151.1375
    assert record["tx_mhz"] == 159.4725
    assert record["ctcss"] == 136.5


def test_dmr_simplex_plan_carries_colour_code_and_timeslot() -> None:
    record = _record(
        ChannelPlanChannel(
            name="DMR SIMPLEX 1",
            freq_mhz=441.0,
            emission="7K60FXE",
            mode={"type": "DMR", "color_code": 1, "timeslots": [1]},
        )
    )

    assert record["mode"] == "DMR"
    assert record["color_code"] == 1
    assert record["timeslots"] == [1]


def test_plan_level_mode_applies_to_channels_without_one() -> None:
    plan = ChannelPlan(
        id="chplan_test",
        name="Test",
        mode={"type": "FM", "ctcss_tx_hz": 156.7, "ctcss_rx_hz": 156.7},
        channels=[
            ChannelPlanChannel(name="One", freq_mhz=155.7525),
            ChannelPlanChannel(
                name="Two",
                freq_mhz=155.475,
                mode={"type": "FM", "ctcss_tx_hz": 127.3, "ctcss_rx_hz": 127.3},
            ),
        ],
    )

    assert plan.channels[0].mode is not None
    assert plan.channels[0].mode.ctcss_rx_hz == 156.7
    assert plan.channels[1].mode.ctcss_rx_hz == 127.3
    # Each channel gets its own copy, not a shared reference.
    assert plan.channels[0].mode is not plan.mode


def test_mode_type_must_agree_with_the_emission() -> None:
    with pytest.raises(ValidationError, match="implies 'FM'"):
        ChannelPlanChannel(
            name="Bad", freq_mhz=146.52, emission="16K0F3E", mode={"type": "DMR"}
        )


def test_j3e_does_not_pin_a_sideband() -> None:
    ChannelPlanChannel(
        name="CB 38 LSB", freq_mhz=27.385, emission="4K00J3E", mode={"type": "LSB"}
    )


def test_mode_cannot_span_several_emissions() -> None:
    with pytest.raises(ValidationError, match="alongside 2 `emissions`"):
        ChannelPlanChannel(
            name="Bad",
            freq_mhz=27.0,
            emissions=[{"emission": "8K00A3E"}, {"emission": "8K00F3E"}],
            mode={"type": "AM"},
        )


def test_plan_default_mode_is_checked_against_channel_emissions() -> None:
    with pytest.raises(ValidationError, match="alongside 2 `emissions`"):
        ChannelPlan(
            id="chplan_bad",
            name="Bad",
            mode={"type": "AM"},
            channels=[
                ChannelPlanChannel(
                    name="CB 01",
                    freq_mhz=26.965,
                    emissions=[{"emission": "8K00A3E"}, {"emission": "8K00F3E"}],
                )
            ],
        )


def test_unknown_channel_keys_are_rejected_not_dropped() -> None:
    """The loader used to whitelist channel keys and silently discard the rest."""

    with pytest.raises(ValidationError, match="ctcss"):
        validate_data(
            {
                "channel_plans": [
                    {
                        "id": "chplan_x",
                        "name": "X",
                        "channels": [{"name": "A", "freq_mhz": 146.52, "ctcss": 100.0}],
                    }
                ]
            }
        )


def test_legacy_assignment_policy_keys_are_rejected() -> None:
    """`codeplug`, `zones`, `scan`, `comment` were dropped on read before 0.10.0."""

    for key in ("codeplug", "zones", "scan", "comment"):
        with pytest.raises(ValidationError, match=key):
            validate_data(
                {"assignments": [{"id": "asg_x", "channel_plan_id": "p", key: "x"}]}
            )
