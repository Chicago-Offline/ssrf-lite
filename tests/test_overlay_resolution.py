from __future__ import annotations

import pathlib
import sys
import tempfile
import textwrap
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from generate_ssrf_codeplug import build_records
from generate_ssrf_site import build_payload
from ssrf import resolve_ssrf_roots


BASE_DOCUMENT = textwrap.dedent(
    """\
    ssrf_lite_version: "0.5.3"
    organizations:
      - id: org_test
        name: "Test Organization"
    stations:
      - id: stn_test
        organization_id: org_test
        service: "amateur"
    antennas:
      - id: ant_test
        station_id: stn_test
        name: "Base antenna"
    rf_chains:
      - id: chain_test
        station_id: stn_test
        antenna_id: ant_test
        tx:
          freq_mhz: 146.52
          power_w: 5
          emission: "16K0F3E"
        rx:
          freq_mhz: 146.52
        mode:
          type: "FM"
          ctcss_tx_hz: 100.0
          timeslots: [1, 2]
          notes: "Base note"
    assignments:
      - id: asg_test
        rf_chain_id: chain_test
        channel_name: "BASE NAME"
        usage: "simplex"
        service: "amateur"
    """
)

PATCH_DOCUMENT = textwrap.dedent(
    """\
    ssrf_lite_version: "0.5.3"
    overrides:
      rf_chains:
        - id: chain_test
          patch:
            tx:
              power_w: 2
            mode:
              ctcss_tx_hz: null
              timeslots: [2]
              notes: "Overlay note"
      assignments:
        - id: asg_test
          patch:
            channel_name: "LOCAL NAME"
    """
)


class OverlayResolutionTest(unittest.TestCase):
    def _write_roots(
        self, temporary: pathlib.Path, overlay: str = PATCH_DOCUMENT
    ) -> tuple[pathlib.Path, pathlib.Path]:
        primary = temporary / "primary"
        extra = temporary / "extra"
        (primary / "systems").mkdir(parents=True)
        (extra / "systems").mkdir(parents=True)
        (primary / "systems" / "base.yml").write_text(
            BASE_DOCUMENT, encoding="utf-8"
        )
        (extra / "systems" / "overlay.yml").write_text(overlay, encoding="utf-8")
        return primary, extra

    def test_field_patch_merges_nested_maps_replaces_lists_and_clears_null(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            primary, extra = self._write_roots(pathlib.Path(tmp))
            documents = resolve_ssrf_roots([primary, extra])

        self.assertEqual(len(documents), 1)
        reference = documents[0].reference
        chain = reference.rf_chains[0]
        self.assertEqual(chain.tx.freq_mhz, 146.52)
        self.assertEqual(chain.tx.power_w, 2)
        self.assertIsNone(chain.mode.ctcss_tx_hz)
        self.assertEqual(chain.mode.timeslots, [2])
        self.assertEqual(chain.mode.notes, "Overlay note")
        self.assertEqual(reference.assignments[0].channel_name, "LOCAL NAME")

    def test_additive_documents_remain_in_the_resolved_output(self) -> None:
        additive = PATCH_DOCUMENT + textwrap.dedent(
            """\
            organizations:
              - id: org_extra
                name: "Extra Organization"
            """
        )
        with tempfile.TemporaryDirectory() as tmp:
            primary, extra = self._write_roots(pathlib.Path(tmp), additive)
            documents = resolve_ssrf_roots([primary, extra])

        self.assertEqual(len(documents), 2)
        extra_document = next(document for document in documents if document.is_overlay)
        self.assertEqual(extra_document.reference.organizations[0].id, "org_extra")

    def test_unknown_override_target_fails(self) -> None:
        overlay = textwrap.dedent(
            """\
            ssrf_lite_version: "0.5.3"
            overrides:
              assignments:
                - id: asg_missing
                  patch:
                    channel_name: "UNKNOWN"
            """
        )
        with tempfile.TemporaryDirectory() as tmp:
            primary, extra = self._write_roots(pathlib.Path(tmp), overlay)
            with self.assertRaisesRegex(ValueError, "asg_missing"):
                resolve_ssrf_roots([primary, extra])

    def test_override_cannot_target_addition_in_the_same_root(self) -> None:
        overlay = textwrap.dedent(
            """\
            ssrf_lite_version: "0.5.3"
            organizations:
              - id: org_same_root
                name: "Same Root"
            overrides:
              organizations:
                - id: org_same_root
                  patch:
                    name: "Patched Same Root"
            """
        )
        with tempfile.TemporaryDirectory() as tmp:
            primary, extra = self._write_roots(pathlib.Path(tmp), overlay)
            with self.assertRaisesRegex(ValueError, "org_same_root"):
                resolve_ssrf_roots([primary, extra])

    def test_ambiguous_override_target_fails(self) -> None:
        duplicate = BASE_DOCUMENT.replace("BASE NAME", "SECOND NAME")
        with tempfile.TemporaryDirectory() as tmp:
            temporary = pathlib.Path(tmp)
            primary, extra = self._write_roots(temporary)
            (primary / "systems" / "duplicate.yml").write_text(
                duplicate, encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "ambiguous.*chain_test"):
                resolve_ssrf_roots([primary, extra])

    def test_override_cannot_change_entity_id(self) -> None:
        overlay = textwrap.dedent(
            """\
            ssrf_lite_version: "0.5.3"
            overrides:
              assignments:
                - id: asg_test
                  patch:
                    id: asg_renamed
            """
        )
        with tempfile.TemporaryDirectory() as tmp:
            primary, extra = self._write_roots(pathlib.Path(tmp), overlay)
            with self.assertRaisesRegex(ValueError, "immutable"):
                resolve_ssrf_roots([primary, extra])

    def test_generators_consume_resolved_entities(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            primary, extra = self._write_roots(pathlib.Path(tmp))
            roots = [primary, extra]
            site_channels = build_payload(roots)["channels"]
            codeplug_records = build_records(roots)

        self.assertEqual(site_channels[0]["name"], "LOCAL NAME")
        self.assertNotIn("CTCSS", site_channels[0]["mode_detail"])
        self.assertEqual(codeplug_records[0]["name"], "LOCAL NAME")
        self.assertIsNone(codeplug_records[0]["ctcss"])


if __name__ == "__main__":
    unittest.main()