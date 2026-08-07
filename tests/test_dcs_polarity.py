"""Tests for DCS polarity fields."""

import pytest
from pydantic import ValidationError

from generate_ssrf_codeplug import _encode_dcs
from generate_ssrf_site import _mode_summary
from ssrf.models.pydantic_models import Mode


def test_dcs_polarity_defaults_to_normal() -> None:
    mode = Mode(type="FM", dcs_tx_code="023", dcs_rx_code="023")

    assert mode.dcs_tx_polarity == "N"
    assert mode.dcs_rx_polarity == "N"


def test_dcs_polarity_preserves_independent_values() -> None:
    mode = Mode(
        type="FM",
        dcs_tx_code="023",
        dcs_tx_polarity="I",
        dcs_rx_code="205",
        dcs_rx_polarity="N",
    )

    assert mode.dcs_tx_polarity == "I"
    assert mode.dcs_rx_polarity == "N"


def test_dcs_polarity_rejects_unknown_value() -> None:
    with pytest.raises(ValidationError):
        Mode(type="FM", dcs_tx_code="023", dcs_tx_polarity="R")


def test_codeplug_uses_polarity_for_selected_dcs_code() -> None:
    tx_only = Mode(type="FM", dcs_tx_code="023", dcs_tx_polarity="I")
    split = Mode(
        type="FM",
        dcs_tx_code="023",
        dcs_tx_polarity="I",
        dcs_rx_code="205",
        dcs_rx_polarity="N",
    )

    assert _encode_dcs(tx_only) == ("023", "I")
    assert _encode_dcs(split) == ("205", "N")
    assert _encode_dcs(Mode(type="FM")) == (None, None)


def test_site_summary_displays_split_dcs_polarity() -> None:
    mode = Mode(
        type="FM",
        dcs_tx_code="023",
        dcs_tx_polarity="I",
        dcs_rx_code="205",
        dcs_rx_polarity="N",
    )

    assert _mode_summary(mode)["detail"] == "DCS 023 I/205 N"