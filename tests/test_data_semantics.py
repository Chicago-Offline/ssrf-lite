"""Semantic data-hygiene checks for SSRF-Lite content.

Schema validation proves documents are well-formed; these tests catch
plausible-but-wrong data: out-of-allocation frequencies, non-standard
CTCSS/DCS values, implausible repeater offsets, coordinates outside the
file's region, and duplicate channel definitions.
"""

from __future__ import annotations

import pathlib
import sys
import unittest
from typing import Any, Dict, Iterator, List, Optional, Tuple

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ssrf.models import pydantic_models

SSRF_DIR = PROJECT_ROOT / "ssrf"

# --- Frequency allocations (MHz) per SSRF service taxonomy id ----------------

US_AMATEUR_BANDS = [
    (1.8, 2.0),
    (3.5, 4.0),
    (5.3, 5.41),
    (7.0, 7.3),
    (10.1, 10.15),
    (14.0, 14.35),
    (18.068, 18.168),
    (21.0, 21.45),
    (24.89, 24.99),
    (28.0, 29.7),
    (50.0, 54.0),
    (144.0, 148.0),
    (222.0, 225.0),
    (420.0, 450.0),
    (902.0, 928.0),
    (1240.0, 1300.0),
]

SERVICE_RANGES: Dict[str, List[Tuple[float, float]]] = {
    "amateur": US_AMATEUR_BANDS,
    # GMRS/FRS: 462 MHz mains + interstitials, 467 MHz inputs + interstitials
    "gmrs": [(462.53, 462.74), (467.53, 467.74)],
    "frs": [(462.53, 462.74), (467.53, 467.74)],
    "murs": [(151.81, 151.95), (154.56, 154.61)],
    "pmr446": [(446.0, 446.2)],
    "noaa_weather_radio": [(162.4, 162.55)],
    # Marine VHF including shore-side duplex outputs around 161-162
    "marine": [(155.9, 162.1)],
    "aviation": [(118.0, 137.0)],
    # AAR channels 2-97
    "railroad_aar": [(159.5, 161.6)],
    # public_safety_part90 / business_itinerant_part90 span too many bands
    # to constrain usefully; they are intentionally unchecked.
}

# Standard 50-tone CTCSS (EIA + extended) set.
CTCSS_TONES = {
    67.0, 69.3, 71.9, 74.4, 77.0, 79.7, 82.5, 85.4, 88.5, 91.5,
    94.8, 97.4, 100.0, 103.5, 107.2, 110.9, 114.8, 118.8, 123.0, 127.3,
    131.8, 136.5, 141.3, 146.2, 151.4, 156.7, 159.8, 162.2, 165.5, 167.9,
    171.3, 173.8, 177.3, 179.9, 183.5, 186.2, 189.9, 192.8, 196.6, 199.5,
    203.5, 206.5, 210.7, 218.1, 225.7, 229.1, 233.6, 241.8, 250.3, 254.1,
}

# Standard 104-code DCS set (normalized to zero-padded 3-digit strings).
DCS_CODES = {
    "023", "025", "026", "031", "032", "036", "043", "047", "051", "053",
    "054", "065", "071", "072", "073", "074", "114", "115", "116", "122",
    "125", "131", "132", "134", "143", "145", "152", "155", "156", "162",
    "165", "172", "174", "205", "212", "223", "225", "226", "243", "244",
    "245", "246", "251", "252", "255", "261", "263", "265", "266", "271",
    "274", "306", "311", "315", "325", "331", "332", "343", "346", "351",
    "356", "364", "365", "371", "411", "412", "413", "423", "431", "432",
    "445", "446", "452", "454", "455", "462", "464", "465", "466", "503",
    "506", "516", "523", "526", "532", "546", "565", "606", "612", "624",
    "627", "631", "632", "654", "662", "664", "703", "712", "723", "731",
    "732", "734", "743", "754",
}

# Conventional repeater splits (MHz) by band, with a little slack for
# non-standard-but-real splits.
REPEATER_OFFSETS = [
    ((50.0, 54.0), {0.5, 1.0, 1.7}),
    ((144.0, 148.0), {0.6, 1.0, 1.5}),
    ((222.0, 225.0), {1.6}),
    ((420.0, 450.0), {5.0, 9.0}),  # 9 MHz = common MMDVM duplex hotspot split
    ((462.0, 468.0), {5.0}),  # GMRS
    ((902.0, 928.0), {12.0, 25.0}),
    ((1240.0, 1300.0), {12.0, 20.0}),
]

# State bounding boxes (lat_min, lat_max, lon_min, lon_max), padded ~1.5deg so
# regional systems that straddle a border don't false-fail.
_PAD = 1.5
STATE_BOUNDS = {
    "IL": (36.97 - _PAD, 42.51 + _PAD, -91.51 - _PAD, -87.02 + _PAD),
    "IN": (37.77 - _PAD, 41.76 + _PAD, -88.10 - _PAD, -84.78 + _PAD),
    "MI": (41.70 - _PAD, 48.31 + _PAD, -90.42 - _PAD, -82.12 + _PAD),
    "FL": (24.40 - _PAD, 31.00 + _PAD, -87.63 - _PAD, -79.97 + _PAD),
}
US_BOUNDS = (17.0, 72.0, -180.0, -64.0)


def _iter_documents() -> Iterator[Tuple[pathlib.Path, Any]]:
    for path in sorted(SSRF_DIR.rglob("*.yml")):
        yield path, pydantic_models.load_ssrf_document(path)


def _rel(path: pathlib.Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def _in_ranges(freq: float, ranges: List[Tuple[float, float]]) -> bool:
    return any(lo <= freq <= hi for lo, hi in ranges)


def _normalize_dcs(code: Any) -> str:
    return str(code).zfill(3)


def _iter_service_freqs(ref: Any) -> Iterator[Tuple[str, str, float]]:
    """Yield (service, label, freq_mhz) for every frequency in a document."""
    stations = {s.id: s for s in ref.stations}
    chains = {c.id: c for c in ref.rf_chains}
    plans = {p.id: p for p in ref.channel_plans}

    for a in ref.assignments:
        if a.rf_chain_id and a.rf_chain_id in chains:
            chain = chains[a.rf_chain_id]
            station = stations.get(chain.station_id)
            service = a.service or (station.service if station else None)
            if not service:
                continue
            for freq in (chain.tx.freq_mhz, chain.rx.freq_mhz):
                if freq:
                    yield service, a.id, freq
        elif a.channel_plan_id and a.channel_plan_id in plans:
            plan = plans[a.channel_plan_id]
            service = a.service or plan.service
            if not service:
                continue
            channels = plan.channels
            if a.channel_name:
                channels = [
                    c for c in plan.channels if c.name == a.channel_name
                ] or plan.channels
            for ch in channels:
                for freq in (ch.freq_mhz, ch.tx_freq_mhz):
                    if freq:
                        yield service, f"{plan.id}/{ch.name}", freq

    # Plans may exist without assignments in the same file; check them too.
    for plan in ref.channel_plans:
        if not plan.service:
            continue
        for ch in plan.channels:
            for freq in (ch.freq_mhz, ch.tx_freq_mhz):
                if freq:
                    yield plan.service, f"{plan.id}/{ch.name}", freq


class ServiceFrequencyTest(unittest.TestCase):
    def test_frequencies_within_service_allocation(self) -> None:
        failures: List[str] = []
        for path, ref in _iter_documents():
            for service, label, freq in _iter_service_freqs(ref):
                ranges = SERVICE_RANGES.get(service)
                if ranges and not _in_ranges(freq, ranges):
                    failures.append(
                        f"{_rel(path)}: {label}: {freq} MHz outside {service} allocation"
                    )
        self.assertEqual(failures, [], "\n" + "\n".join(failures))


class ToneAndCodeTest(unittest.TestCase):
    def test_ctcss_tones_are_standard(self) -> None:
        failures: List[str] = []
        for path, ref in _iter_documents():
            for chain in ref.rf_chains:
                for field in ("ctcss_tx_hz", "ctcss_rx_hz"):
                    tone = getattr(chain.mode, field)
                    if tone is not None and round(tone, 1) not in CTCSS_TONES:
                        failures.append(
                            f"{_rel(path)}: {chain.id}: {field}={tone} is not a standard CTCSS tone"
                        )
        self.assertEqual(failures, [], "\n" + "\n".join(failures))

    def test_dcs_codes_are_standard(self) -> None:
        failures: List[str] = []
        for path, ref in _iter_documents():
            for chain in ref.rf_chains:
                for field in ("dcs_tx_code", "dcs_rx_code"):
                    code = getattr(chain.mode, field)
                    if code is not None and _normalize_dcs(code) not in DCS_CODES:
                        failures.append(
                            f"{_rel(path)}: {chain.id}: {field}={code} is not a standard DCS code"
                        )
        self.assertEqual(failures, [], "\n" + "\n".join(failures))


class RepeaterOffsetTest(unittest.TestCase):
    def test_repeater_splits_are_conventional(self) -> None:
        failures: List[str] = []
        for path, ref in _iter_documents():
            for chain in ref.rf_chains:
                tx, rx = chain.tx.freq_mhz, chain.rx.freq_mhz
                if not tx or not rx or tx == rx:
                    continue
                offset = abs(tx - rx)
                for (lo, hi), allowed in REPEATER_OFFSETS:
                    if lo <= tx <= hi:
                        if not any(abs(offset - a) < 0.01 for a in allowed):
                            failures.append(
                                f"{_rel(path)}: {chain.id}: unusual split "
                                f"{offset:.4f} MHz at {tx} MHz (expected one of {sorted(allowed)})"
                            )
                        break
        self.assertEqual(failures, [], "\n" + "\n".join(failures))


class CoordinateBoundsTest(unittest.TestCase):
    @staticmethod
    def _bounds_for(path: pathlib.Path) -> Optional[Tuple[float, float, float, float]]:
        parts = path.relative_to(SSRF_DIR).parts
        if len(parts) < 2 or parts[0] != "systems":
            return None
        if parts[1] != "US":
            return None
        # Statewide files (e.g. tri-state networks) legitimately span borders.
        if "_Statewide" in parts:
            return US_BOUNDS
        if len(parts) > 2 and parts[2] in STATE_BOUNDS:
            return STATE_BOUNDS[parts[2]]
        return US_BOUNDS

    def test_locations_within_region(self) -> None:
        failures: List[str] = []
        for path, ref in _iter_documents():
            bounds = self._bounds_for(path)
            if bounds is None:
                continue
            lat_min, lat_max, lon_min, lon_max = bounds
            for loc in ref.locations:
                if loc.lat is None or loc.lon is None:
                    continue
                if not (lat_min <= loc.lat <= lat_max and lon_min <= loc.lon <= lon_max):
                    failures.append(
                        f"{_rel(path)}: {loc.id}: ({loc.lat}, {loc.lon}) outside expected region"
                    )
        self.assertEqual(failures, [], "\n" + "\n".join(failures))


class DuplicateChannelTest(unittest.TestCase):
    def test_no_duplicate_channel_definitions_within_file(self) -> None:
        # Cross-file listings (e.g. a repeater in both a club file and a
        # network file) are legitimate; this targets copy-paste errors.
        failures: List[str] = []
        for path, ref in _iter_documents():
            stations = {s.id: s for s in ref.stations}
            seen: Dict[Tuple[Any, ...], str] = {}
            for chain in ref.rf_chains:
                station = stations.get(chain.station_id)
                if not station or not station.call_sign:
                    continue
                key = (
                    station.call_sign,
                    round(chain.tx.freq_mhz, 4) if chain.tx.freq_mhz else None,
                    round(chain.rx.freq_mhz, 4),
                    chain.mode.type,
                    station.location_id,
                )
                if key in seen:
                    failures.append(
                        f"{_rel(path)}: {chain.id} duplicates {seen[key]} "
                        f"({key[0]} {key[1]}/{key[2]} {key[3]})"
                    )
                else:
                    seen[key] = chain.id
        self.assertEqual(failures, [], "\n" + "\n".join(failures))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
