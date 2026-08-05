"""Tests for channel-plan records in the generated codeplug."""

from __future__ import annotations

import pathlib
from types import SimpleNamespace

from generate_ssrf_codeplug import _record_from_plan_channel
from ssrf import load_ssrf_document
from ssrf.models.pydantic_models import ChannelPlanChannel

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _record(channel: ChannelPlanChannel) -> dict[str, object]:
    assignment = SimpleNamespace(service=None)
    plan = SimpleNamespace(service="marine")
    return _record_from_plan_channel(assignment, plan, channel)


def test_plan_channel_uses_frequency_for_simplex_tx() -> None:
    record = _record(ChannelPlanChannel(name="Ch 06", freq_mhz=156.3))

    assert record["rx_mhz"] == 156.3
    assert record["tx_mhz"] == 156.3


def test_plan_channel_uses_explicit_duplex_tx_frequency() -> None:
    record = _record(
        ChannelPlanChannel(
            name="Ch 20",
            freq_mhz=161.6,
            tx_freq_mhz=157.0,
        )
    )

    assert record["rx_mhz"] == 161.6
    assert record["tx_mhz"] == 157.0


def test_us_marine_plan_defines_duplex_pairs() -> None:
    expected_pairs = {
        "Ch 20": (161.600, 157.000),
        "Ch 24": (161.800, 157.200),
        "Ch 25": (161.850, 157.250),
        "Ch 26": (161.900, 157.300),
        "Ch 27": (161.950, 157.350),
        "Ch 28": (162.000, 157.400),
        "Ch 60": (160.625, 156.025),
        "Ch 84": (161.825, 157.225),
        "Ch 85": (161.875, 157.275),
        "Ch 86": (161.925, 157.325),
    }
    document = load_ssrf_document(
        PROJECT_ROOT / "ssrf/plans/US/marine/marine_vhf_channels.yml"
    )
    channels = {
        channel.name: channel for channel in document.channel_plans[0].channels
    }

    for name, (rx_mhz, tx_mhz) in expected_pairs.items():
        assert channels[name].freq_mhz == rx_mhz
        assert channels[name].tx_freq_mhz == tx_mhz