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

    def test_declared_precedence_overrides_argv_order_both_directions(self) -> None:
        # Two roots both patch the same field. Without declared precedence,
        # whichever root is passed LAST wins (today's argv-order behavior).
        # With declared precedence, the higher-precedence root wins
        # regardless of argv order.
        low_overlay = textwrap.dedent(
            """\
            ssrf_lite_version: "0.5.3"
            overrides:
              assignments:
                - id: asg_test
                  patch:
                    channel_name: "LOW"
            """
        )
        high_overlay = textwrap.dedent(
            """\
            ssrf_lite_version: "0.5.3"
            overrides:
              assignments:
                - id: asg_test
                  patch:
                    channel_name: "HIGH"
            """
        )
        with tempfile.TemporaryDirectory() as tmp:
            temporary = pathlib.Path(tmp)
            primary = temporary / "primary"
            low = temporary / "low"
            high = temporary / "high"
            (primary / "systems").mkdir(parents=True)
            (low / "systems").mkdir(parents=True)
            (high / "systems").mkdir(parents=True)
            (primary / "systems" / "base.yml").write_text(BASE_DOCUMENT, encoding="utf-8")
            (low / "systems" / "overlay.yml").write_text(low_overlay, encoding="utf-8")
            (high / "systems" / "overlay.yml").write_text(high_overlay, encoding="utf-8")
            (low / "_root.yml").write_text(
                "ssrf_root:\n  id: low\n  precedence: 10\n", encoding="utf-8"
            )
            (high / "_root.yml").write_text(
                "ssrf_root:\n  id: high\n  precedence: 20\n", encoding="utf-8"
            )

            # argv order: primary, high, low -- but 'high' has higher declared
            # precedence, so it must still win even though it loads first.
            documents = resolve_ssrf_roots([primary, high, low])
            base_document = next(doc for doc in documents if not doc.is_overlay)
            self.assertEqual(base_document.reference.assignments[0].channel_name, "HIGH")

            # argv order flipped: primary, low, high -- same declared
            # precedences must produce the identical result.
            documents = resolve_ssrf_roots([primary, low, high])
            base_document = next(doc for doc in documents if not doc.is_overlay)
            self.assertEqual(base_document.reference.assignments[0].channel_name, "HIGH")

    def test_duplicate_declared_precedence_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temporary = pathlib.Path(tmp)
            primary, extra = self._write_roots(temporary)
            other = temporary / "other"
            (other / "systems").mkdir(parents=True)
            (extra / "_root.yml").write_text(
                "ssrf_root:\n  id: extra\n  precedence: 5\n", encoding="utf-8"
            )
            (other / "_root.yml").write_text(
                "ssrf_root:\n  id: other\n  precedence: 5\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "duplicate declared SSRF root precedence"):
                resolve_ssrf_roots([primary, extra, other])

    def test_additive_only_overlay_ordering_honors_declared_precedence(self) -> None:
        # Additive-only overlays (no `overrides` block) previously reordered
        # silently since only override-target eligibility checked root_index.
        # With declared precedence, an additive-only overlay's declared
        # precedence still determines its is_overlay/load-order position.
        additive = textwrap.dedent(
            """\
            ssrf_lite_version: "0.5.3"
            organizations:
              - id: org_extra
                name: "Extra Organization"
            """
        )
        with tempfile.TemporaryDirectory() as tmp:
            temporary = pathlib.Path(tmp)
            primary, extra = self._write_roots(temporary, additive)
            (extra / "_root.yml").write_text(
                "ssrf_root:\n  id: extra\n  precedence: -1\n", encoding="utf-8"
            )
            # Even though 'extra' is passed second (argv order), a declared
            # precedence lower than the implicit precedence of 'primary' (0)
            # puts it first in load order, so it's no longer the overlay.
            documents = resolve_ssrf_roots([primary, extra])
            base_document = next(doc for doc in documents if not doc.is_overlay)
            self.assertEqual(base_document.root, extra)

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