"""Tests for DCS code typing: quoted three-digit octal, closed to the standard set."""

import pytest
import yaml
from pydantic import ValidationError

from ssrf.models.pydantic_models import DCS_CODES, Mode


def test_standard_set_is_complete() -> None:
    assert len(DCS_CODES) == 104
    assert DCS_CODES[0] == "023"
    assert DCS_CODES[-1] == "754"


def test_accepts_quoted_code() -> None:
    mode = Mode(type="FM", dcs_tx_code="023", dcs_rx_code="624")

    assert mode.dcs_tx_code == "023"
    assert mode.dcs_rx_code == "624"


def test_zero_pads_short_string() -> None:
    assert Mode(type="FM", dcs_rx_code="23").dcs_rx_code == "023"


def test_rejects_integer_and_explains_why() -> None:
    with pytest.raises(ValidationError) as excinfo:
        Mode(type="FM", dcs_rx_code=624)

    message = str(excinfo.value)
    assert "quoted three-digit octal string" in message
    assert "octal" in message


def test_rejects_yaml_octal_coerced_integer() -> None:
    """An unquoted `032` is YAML 1.1 octal and loads as 26; it must not pass."""
    loaded = yaml.safe_load("dcs_rx_code: 032")
    assert loaded["dcs_rx_code"] == 26

    with pytest.raises(ValidationError):
        Mode(type="FM", **loaded)


@pytest.mark.parametrize("code", ["224", "011"])
def test_rejects_non_standard_codes(code: str) -> None:
    """Both are real corruptions seen in the wild: a 9-bit code truncated to 8."""
    with pytest.raises(ValidationError) as excinfo:
        Mode(type="FM", dcs_rx_code=code)

    assert "not a standard DCS code" in str(excinfo.value)


def test_blank_is_treated_as_absent() -> None:
    assert Mode(type="FM", dcs_rx_code="  ").dcs_rx_code is None
