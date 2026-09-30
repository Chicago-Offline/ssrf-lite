"""The station perspective: every frequency belongs to the station described."""

from __future__ import annotations

import pathlib
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from generate_ssrf_codeplug import _record_from_rf_chain
from ssrf import load_ssrf_document
from ssrf.models.pydantic_models import Mode, RFChain, Receiver, Transmitter

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]

# GMRS is the clearest directional case: repeater outputs sit in the 462 MHz
# main block and inputs 5 MHz up in the 467 MHz block, never the reverse.
GMRS_OUTPUT_RANGE = (462.5500, 462.7250)
GMRS_INPUT_RANGE = (467.5500, 467.7250)


def test_repeater_chain_records_its_own_output_on_tx() -> None:
    chain = RFChain(
        id="chain_example",
        station_id="stn_example",
        tx=Transmitter(freq_mhz=462.550),
        rx=Receiver(freq_mhz=467.550),
        mode=Mode(type="FM", ctcss_tx_hz=141.3, ctcss_rx_hz=225.7),
    )

    record = _record_from_rf_chain(
        SimpleNamespace(service="gmrs", short_name=None, channel_name="Example", id="a"),
        chain,
        None,
        None,
    )

    # The codeplug is the mirror: the radio listens to the repeater's output
    # and transmits on its input, encoding the tone the repeater demands.
    assert record["rx_mhz"] == 462.550
    assert record["tx_mhz"] == 467.550
    assert record["ctcss"] == 225.7


def test_simplex_chain_omits_rx_and_still_round_trips() -> None:
    chain = RFChain(
        id="chain_simplex",
        station_id="stn_example",
        tx=Transmitter(freq_mhz=146.520),
        mode=Mode(type="FM"),
    )

    assert chain.simplex
    record = _record_from_rf_chain(
        SimpleNamespace(service="amateur", short_name=None, channel_name="Call", id="a"),
        chain,
        None,
        None,
    )
    assert record["rx_mhz"] == record["tx_mhz"] == 146.520


def test_receive_only_site_may_omit_tx() -> None:
    chain = RFChain(
        id="chain_voter",
        station_id="stn_voter",
        rx=Receiver(freq_mhz=147.585),
        mode=Mode(type="FM"),
    )

    assert chain.rx.freq_mhz == 147.585
    assert chain.tx.freq_mhz is None


def test_chain_without_any_frequency_is_rejected() -> None:
    with pytest.raises(ValidationError, match="neither tx.freq_mhz nor rx.freq_mhz"):
        RFChain(
            id="chain_empty",
            station_id="stn_example",
            mode=Mode(type="FM"),
        )


def test_gmrs_repeaters_are_not_recorded_backwards() -> None:
    """Regression guard for the 0.8.0 radio-centric convention."""

    failures: list[str] = []
    for path in sorted((PROJECT_ROOT / "ssrf").rglob("*.yml")):
        if "gmrs" not in str(path):
            continue
        for chain in load_ssrf_document(path).rf_chains:
            tx, rx = chain.tx.freq_mhz, chain.rx.freq_mhz
            if not tx or not rx or tx == rx:
                continue
            if not (GMRS_OUTPUT_RANGE[0] <= tx <= GMRS_OUTPUT_RANGE[1]):
                continue
            if not (GMRS_INPUT_RANGE[0] <= rx <= GMRS_INPUT_RANGE[1]):
                failures.append(
                    f"{path.relative_to(PROJECT_ROOT)}: {chain.id}: "
                    f"tx={tx} rx={rx} -- input should be the 467 MHz pair"
                )

    assert failures == [], "\n" + "\n".join(failures)


def test_zion_repeater_reads_from_the_repeater() -> None:
    document = load_ssrf_document(
        PROJECT_ROOT / "ssrf/systems/US/IL/Lake/Benton/gmrs/zion_gmrs_repeaters.yml"
    )
    chain = document.rf_chains[0]

    assert chain.tx.freq_mhz == 462.550
    assert chain.rx.freq_mhz == 467.550
    assert chain.mode.ctcss_tx_hz == 141.3
    assert chain.mode.ctcss_rx_hz == 225.7
