"""Short channel names for radios with narrow displays.

The tightest common limit is a 6-character alpha tag, so a name that fits 6
fits every wider radio. Records may author `short_name` directly; everything
else falls back to a deterministic abbreviation so no channel ever reaches a
radio without a usable tag.

Collision handling is deliberately out of scope here: uniqueness is a property
of a particular codeplug's zone, which this library cannot see.
"""

from __future__ import annotations

import pathlib
import textwrap
from types import SimpleNamespace

import pytest

from generate_ssrf_codeplug import (
    SHORT_NAME_MAX_LEN,
    _abbreviate,
    _record_from_rf_chain,
    _short_name,
    build_records,
)
from ssrf.models.pydantic_models import Mode, RFChain, Receiver, Transmitter


def _records(tmp_path: pathlib.Path, doc: str) -> list:
    root = tmp_path / "ssrf"
    root.mkdir(parents=True, exist_ok=True)
    (root / "doc.yml").write_text(doc)
    return build_records([root])


def _chain() -> RFChain:
    return RFChain(
        id="chain_example",
        station_id="stn_example",
        tx=Transmitter(freq_mhz=146.940),
        rx=Receiver(freq_mhz=146.340),
        mode=Mode(type="FM"),
    )


def _assignment(short_name=None, channel_name="Example Channel") -> SimpleNamespace:
    return SimpleNamespace(
        id="asg_example",
        service="amateur",
        short_name=short_name,
        channel_name=channel_name,
    )


# --- abbreviation tiers ------------------------------------------------------


@pytest.mark.parametrize(
    "name,expected",
    [
        # Fits whole: separators dropped, nothing else lost.
        ("Ch 06", "CH06"),
        ("NSEA PK", "NSEAPK"),
        # Enough words to read as an acronym.
        ("Tampa Amateur Radio Club", "TARC"),
        ("NOAA Weather Radio 1", "NWR1"),
        # Balanced trim: every word keeps a character, the longest give up most.
        ("Metra Rail", "METRAI"),
        # Siblings that differ at the tail...
        ("Sparta BOE", "SPABOE"),
        ("Sparta DPW", "SPADPW"),
        # ...at the head...
        ("KARR UNICOM", "KARUNI"),
        ("KORD ASOS", "KORASO"),
        # ...and in the middle, which no fixed truncation can handle.
        ("CB 30 USB", "CB30US"),
        ("CB 31 USB", "CB31US"),
        # Numbers surrender high-order digits: 160230/160320 differ late.
        ("aar 160230", "AAR230"),
        ("aar 160320", "AAR320"),
        # Nothing left to trim -> straight truncation.
        ("A B C D E F G H", "ABCDEF"),
    ],
)
def test_abbreviate_preserves_what_distinguishes_siblings(
    name: str, expected: str
) -> None:
    assert _abbreviate(name) == expected


@pytest.mark.parametrize(
    "name",
    [
        "Ch 06",
        "Tampa Amateur Radio Club",
        "A B C D E F G H",
        "North Shore Emergency Association Park District Repeater",
    ],
)
def test_abbreviation_never_exceeds_the_limit(name: str) -> None:
    assert len(_abbreviate(name)) <= SHORT_NAME_MAX_LEN


def test_abbreviating_a_nameless_record_yields_empty_not_an_error() -> None:
    assert _abbreviate(None) == ""
    assert _abbreviate("---") == ""


# --- resolution order --------------------------------------------------------


def test_authored_short_name_wins_over_callsign_and_abbreviation() -> None:
    # House style carries information no abbreviation can recover: club + band.
    assert _short_name("SARA2M", "SARA 2 Meter Repeater", "W9SRC") == "SARA2M"


def test_callsign_is_borrowed_when_the_name_adds_nothing() -> None:
    assert _short_name(None, "NS9RC", "NS9RC") == "NS9RC"
    assert _short_name(None, "", "NS9RC") == "NS9RC"


def test_callsign_is_ignored_when_the_name_carries_a_discriminator() -> None:
    # One licensee holds many channels; collapsing them all to the callsign
    # would lose the only thing that tells them apart.
    assert _short_name(None, "KORD ASOS", "KORD") == "KORASO"
    assert _short_name(None, "KORD APP", "KORD") == "KORAPP"


def test_overlong_callsign_falls_through_to_abbreviation() -> None:
    # GMRS callsigns blow the 6-char budget, so the name has to carry the tag.
    assert _short_name(None, "Ch 06", "WQAB123") == "CH06"


def test_abbreviation_used_when_there_is_no_callsign() -> None:
    assert _short_name(None, "Tampa Amateur Radio Club", None) == "TARC"


# --- rf_chain assignments ----------------------------------------------------


def test_rf_chain_record_honours_authored_short_name() -> None:
    record = _record_from_rf_chain(
        _assignment(short_name="NSRC7C"),
        _chain(),
        SimpleNamespace(call_sign="NS9RC", service="amateur", location_id=None),
        None,
    )

    assert record["short_name"] == "NSRC7C"
    # The full name must survive untouched for radios that can display it.
    assert record["name"] == "Example Channel"


def test_rf_chain_record_falls_back_to_callsign() -> None:
    record = _record_from_rf_chain(
        _assignment(channel_name="NS9RC"),
        _chain(),
        SimpleNamespace(call_sign="NS9RC", service="amateur", location_id=None),
        None,
    )

    assert record["short_name"] == "NS9RC"


def test_rf_chain_record_keeps_the_frequency_that_names_the_repeater() -> None:
    station = SimpleNamespace(call_sign="NS9RC", service="amateur", location_id=None)
    tags = {
        _record_from_rf_chain(
            _assignment(channel_name=name), _chain(), station, None
        )["short_name"]
        for name in ("NS9RC 147.345", "NS9RC 147.405", "NS9RC 146.460")
    }

    # Nine NS9RC repeaters share the callsign; only the frequency separates
    # them, so borrowing the callsign would collapse all nine to one tag.
    assert tags != {"NS9RC"}
    assert len(tags) == 3


# --- channel plans -----------------------------------------------------------


PLAN_DOC = textwrap.dedent(
    """\
    ssrf_lite_version: "0.10.0"
    channel_plans:
      - id: test_marine_plan
        name: "Test Marine VHF"
        service: "marine"
        channels:
          - name: "Ch 06"
            short_name: "M06"
            freq_mhz: 156.300
            emission: "16K0F3E"
          - name: "Ch 16 Distress"
            freq_mhz: 156.800
            emission: "16K0F3E"
    assignments:
      - id: asg_plan_wide
        channel_plan_id: test_marine_plan
        usage: "receive_only"
    """
)

OVERRIDE_DOC = textwrap.dedent(
    """\
    ssrf_lite_version: "0.10.0"
    channel_plans:
      - id: test_plan
        name: "Test Plan"
        service: "marine"
        channels:
          - name: "Ch 06"
            short_name: "M06"
            freq_mhz: 156.300
            emission: "16K0F3E"
          - name: "Ch 09"
            freq_mhz: 156.450
            emission: "16K0F3E"
    assignments:
      - id: asg_override
        channel_plan_id: test_plan
        channel_name: "Ch 06"
        short_name: "SAFETY"
        usage: "receive_only"
      - id: asg_plain
        channel_plan_id: test_plan
        channel_name: "Ch 09"
        usage: "receive_only"
    """
)

FANOUT_DOC = textwrap.dedent(
    """\
    ssrf_lite_version: "0.10.0"
    channel_plans:
      - id: test_fanout
        name: "Test Fanout"
        service: "marine"
        channels:
          - name: "Ch 21"
            freq_mhz: 157.050
            emission: "16K0F3E"
          - name: "Ch 22"
            freq_mhz: 157.100
            emission: "16K0F3E"
    assignments:
      - id: asg_fanout
        channel_plan_id: test_fanout
        short_name: "NOPE"
        usage: "receive_only"
    """
)


def test_plan_channel_short_name_is_used_and_absent_ones_abbreviated(
    tmp_path: pathlib.Path,
) -> None:
    by_freq = {r["rx_mhz"]: r for r in _records(tmp_path, PLAN_DOC)}

    assert by_freq[156.300]["short_name"] == "M06"
    assert by_freq[156.800]["short_name"] == _abbreviate("Ch 16 Distress")


def test_assignment_short_name_overrides_a_single_selected_plan_channel(
    tmp_path: pathlib.Path,
) -> None:
    by_freq = {r["rx_mhz"]: r for r in _records(tmp_path, OVERRIDE_DOC)}

    assert by_freq[156.300]["short_name"] == "SAFETY"
    # Untouched assignment keeps the plan's own short name.
    assert by_freq[156.450]["short_name"] == _abbreviate("Ch 09")


def test_assignment_short_name_ignored_when_it_would_collapse_a_fanout(
    tmp_path: pathlib.Path,
) -> None:
    short_names = sorted(r["short_name"] for r in _records(tmp_path, FANOUT_DOC))

    assert short_names == ["CH21", "CH22"]
    assert "NOPE" not in short_names


def test_every_published_record_carries_a_short_name() -> None:
    records = build_records()

    missing = [r["name"] for r in records if not r["short_name"]]
    assert missing == []
    overlong = [
        (r["name"], r["short_name"])
        for r in records
        if len(r["short_name"]) > SHORT_NAME_MAX_LEN
    ]
    assert overlong == []
