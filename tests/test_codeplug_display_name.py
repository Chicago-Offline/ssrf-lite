"""Tests for assignment-level ``display_name`` overrides of channel-plan names.

A shared channel plan carries canonical national names (``Ch 06``). A local
document may want its own label (``M06 SAFETY``) without forking the plan.
``display_name`` provides that, and these tests pin the three behaviours that
matter: the override applies to a single-channel selection, it is ignored when
an assignment fans out to many channels (which would otherwise collapse them
all to one name), and documents without ``display_name`` are unchanged.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import textwrap
import unittest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

_spec = importlib.util.spec_from_file_location(
    "generate_ssrf_codeplug", PROJECT_ROOT / "generate_ssrf_codeplug.py"
)
gcp = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(gcp)


PLAN_DOC = textwrap.dedent(
    """\
    ssrf_lite_version: "0.5.3"
    channel_plans:
      - id: test_marine_plan
        name: "Test Marine VHF"
        service: "marine"
        channels:
          - name: "Ch 06"
            freq_mhz: 156.300
            emission: "16K0F3E"
          - name: "Ch 09"
            freq_mhz: 156.450
            emission: "16K0F3E"
    assignments:
      - id: asg_single_override
        channel_plan_id: test_marine_plan
        channel_name: "Ch 06"
        display_name: "M06 SAFETY"
        usage: "receive_only"
      - id: asg_single_no_override
        channel_plan_id: test_marine_plan
        channel_name: "Ch 09"
        usage: "receive_only"
    """
)

FANOUT_DOC = textwrap.dedent(
    """\
    ssrf_lite_version: "0.5.3"
    channel_plans:
      - id: test_fanout_plan
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
        channel_plan_id: test_fanout_plan
        display_name: "SHOULD NOT APPLY"
        usage: "receive_only"
    """
)


def _records(tmp: pathlib.Path, doc: str) -> list:
    root = tmp / "ssrf"
    root.mkdir(parents=True, exist_ok=True)
    (root / "doc.yml").write_text(doc)
    return gcp.build_records([root])


class DisplayNameOverrideTests(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile

        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._tmpdir.name)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_display_name_renames_single_selected_channel(self) -> None:
        records = _records(self.tmp, PLAN_DOC)
        by_freq = {r["rx_mhz"]: r for r in records}

        # Ch 06 was selected by name and carries display_name -> renamed.
        self.assertEqual(by_freq[156.300]["name"], "M06 SAFETY")
        # Frequency and inferred mode must survive the rename untouched.
        self.assertEqual(by_freq[156.300]["tx_mhz"], 156.300)
        self.assertEqual(by_freq[156.300]["mode"], "FM")
        self.assertEqual(by_freq[156.300]["service"], "marine")

    def test_absent_display_name_keeps_plan_name(self) -> None:
        records = _records(self.tmp, PLAN_DOC)
        by_freq = {r["rx_mhz"]: r for r in records}

        # No display_name on this assignment -> canonical plan name retained.
        self.assertEqual(by_freq[156.450]["name"], "Ch 09")

    def test_display_name_ignored_when_assignment_fans_out(self) -> None:
        """A plan-wide assignment must NOT collapse every channel to one name."""
        records = _records(self.tmp, FANOUT_DOC)
        names = sorted(r["name"] for r in records)

        self.assertEqual(names, ["Ch 21", "Ch 22"])
        self.assertNotIn("SHOULD NOT APPLY", names)


if __name__ == "__main__":
    unittest.main()
