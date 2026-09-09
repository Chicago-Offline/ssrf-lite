"""Tests for codeplug bandwidth_khz derivation."""

from generate_ssrf_codeplug import _emission_bandwidth_khz


def test_parses_common_voice_designators() -> None:
    assert _emission_bandwidth_khz("16K0F3E") == 16.0
    assert _emission_bandwidth_khz("11K2F3E") == 11.2
    assert _emission_bandwidth_khz("6K00A3E") == 6.0
    assert _emission_bandwidth_khz("7K60FXD") == 7.6


def test_scales_hz_and_mhz_prefixes() -> None:
    assert _emission_bandwidth_khz("150HA1A") == 0.15
    assert _emission_bandwidth_khz("1M25F9W") == 1250.0


def test_rejects_missing_or_malformed_designators() -> None:
    assert _emission_bandwidth_khz(None) is None
    assert _emission_bandwidth_khz("") is None
    assert _emission_bandwidth_khz("F3E") is None
    assert _emission_bandwidth_khz("K0F3E") is None
