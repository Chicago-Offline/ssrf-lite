"""Channel plans that permit several emissions on one frequency."""

from __future__ import annotations

import pathlib
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from generate_ssrf_codeplug import _records_from_plan_channel
from ssrf import load_ssrf_document
from ssrf.models.pydantic_models import ChannelPlan, ChannelPlanChannel, validate_data

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _records(channel: ChannelPlanChannel) -> list[dict[str, object]]:
    return _records_from_plan_channel(
        SimpleNamespace(service=None),
        SimpleNamespace(service="cb"),
        channel,
    )


def test_single_emission_channel_yields_one_record() -> None:
    records = _records(
        ChannelPlanChannel(name="Ch 06", freq_mhz=156.3, emission="16K0F3E")
    )

    assert len(records) == 1
    assert records[0]["name"] == "Ch 06"
    assert records[0]["mode"] == "FM"


def test_multi_emission_channel_yields_one_record_each() -> None:
    records = _records(
        ChannelPlanChannel(
            name="CB 01",
            freq_mhz=26.965,
            emissions=[
                {"emission": "8K00A3E", "mode": "AM", "bandwidth_khz": 8},
                {"emission": "4K00J3E", "mode": "USB", "bandwidth_khz": 4},
                {"emission": "4K00J3E", "mode": "LSB", "bandwidth_khz": 4},
            ],
        )
    )

    assert [r["name"] for r in records] == ["CB 01 AM", "CB 01 USB", "CB 01 LSB"]
    assert [r["mode"] for r in records] == ["AM", "USB", "LSB"]
    assert [r["bandwidth_khz"] for r in records] == [8, 4, 4]
    # Same frequency throughout -- these are modulations, not channels.
    assert {r["rx_mhz"] for r in records} == {26.965}


def test_mode_disambiguates_an_ambiguous_designator() -> None:
    """J3E alone cannot say whether a sideband is upper or lower."""

    channel = ChannelPlanChannel(
        name="CB 38",
        freq_mhz=27.385,
        emissions=[{"emission": "4K00J3E", "mode": "LSB"}],
    )

    assert _records(channel)[0]["mode"] == "LSB"


def test_plan_level_emissions_apply_to_every_channel() -> None:
    plan = ChannelPlan(
        id="chplan_test",
        name="Test",
        emissions=[{"emission": "8K00A3E", "mode": "AM"}],
        channels=[
            ChannelPlanChannel(name="One", freq_mhz=27.0),
            ChannelPlanChannel(name="Two", freq_mhz=27.1, emission="8K00F3E"),
        ],
    )

    assert [e.mode for e in plan.channels[0].permitted_emissions()] == ["AM"]
    # A channel declaring its own emission overrides the plan default.
    assert plan.channels[1].permitted_emissions()[0].emission == "8K00F3E"


def test_emission_and_emissions_are_mutually_exclusive() -> None:
    with pytest.raises(ValidationError, match="both `emission` and `emissions`"):
        ChannelPlanChannel(
            name="Bad",
            freq_mhz=27.0,
            emission="8K00A3E",
            emissions=[{"emission": "8K00F3E"}],
        )


def test_empty_emissions_list_is_rejected() -> None:
    with pytest.raises(ValidationError, match="empty `emissions` list"):
        ChannelPlanChannel(name="Bad", freq_mhz=27.0, emissions=[])


def test_legacy_tx_freq_mhz_fails_loudly() -> None:
    """The 0.8.0 key changed meaning, so silently dropping it would be worse."""

    with pytest.raises(ValueError, match="removed in SSRF-Lite 0.9.0"):
        validate_data(
            {
                "channel_plans": [
                    {
                        "id": "chplan_legacy",
                        "name": "Legacy",
                        "channels": [
                            {"name": "Ch 20", "freq_mhz": 161.6, "tx_freq_mhz": 157.0}
                        ],
                    }
                ]
            }
        )


def test_us_cb_plan_permits_am_ssb_and_fm_on_every_channel() -> None:
    document = load_ssrf_document(PROJECT_ROOT / "ssrf/plans/US/cb/cb_channels.yml")
    plan = document.channel_plans[0]

    assert len(plan.channels) == 40
    for channel in plan.channels:
        modes = [e.mode for e in channel.permitted_emissions()]
        assert modes == ["AM", "USB", "LSB", "FM"], channel.name
