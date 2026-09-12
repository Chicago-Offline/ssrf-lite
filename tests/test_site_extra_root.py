"""Tests for generate_ssrf_site.build_payload multi-root (private overlay) support."""

from __future__ import annotations

import html
import importlib.util
import pathlib
import sys
import textwrap
import unittest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

_spec = importlib.util.spec_from_file_location(
    "generate_ssrf_site", PROJECT_ROOT / "generate_ssrf_site.py"
)
gsite = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(gsite)


PRIVATE_DOC = textwrap.dedent(
    """\
    ssrf_lite_version: "0.5.3"
    organizations:
      - id: org_priv_test
        name: "Private Test Org"
    stations:
      - id: stn_priv_test
        organization_id: org_priv_test
        service: "gmrs"
    antennas:
      - id: ant_priv_test
        station_id: stn_priv_test
        name: "Test"
    rf_chains:
      - id: chain_priv_test
        station_id: stn_priv_test
        antenna_id: ant_priv_test
        rx:
          freq_mhz: 462.575
        tx:
          freq_mhz: 462.575
          emission: "11K2F3E"
        mode:
          type: "FM"
          ctcss_tx_hz: 141.3
          ctcss_rx_hz: 141.3
    assignments:
      - id: asg_priv_test
        rf_chain_id: chain_priv_test
        channel_name: "PRIV TEST CH"
        usage: "simplex"
        service: "gmrs"
    """
)


class SiteBuildPayloadRootsTest(unittest.TestCase):
    def test_default_matches_explicit_primary_root(self) -> None:
        default = gsite.build_payload()
        explicit = gsite.build_payload([gsite.SSRF_ROOT])
        self.assertEqual(
            len(default["channels"]), len(explicit["channels"]),
            "explicit primary root should match the default",
        )

    def test_extra_root_merges_private_channels(self) -> None:
        import tempfile

        base = gsite.build_payload()
        with tempfile.TemporaryDirectory() as tmp:
            priv = pathlib.Path(tmp) / "ssrf" / "systems" / "custom"
            priv.mkdir(parents=True)
            (priv / "priv_test.yml").write_text(PRIVATE_DOC, encoding="utf-8")

            merged = gsite.build_payload(
                [gsite.SSRF_ROOT, pathlib.Path(tmp) / "ssrf"]
            )

        self.assertEqual(
            len(merged["channels"]), len(base["channels"]) + 1,
            "extra root should add exactly the one private channel",
        )
        names = [c.get("name") for c in merged["channels"]]
        self.assertIn("PRIV TEST CH", names)
        priv_ch = next(c for c in merged["channels"] if c.get("name") == "PRIV TEST CH")
        self.assertEqual(priv_ch["freq_mhz"], 462.575)
        self.assertEqual(priv_ch["mode"], "FM")
        self.assertIn("141.3", priv_ch.get("mode_detail", ""))

    def test_overlay_files_have_no_public_repo_links(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            priv = pathlib.Path(tmp) / "ssrf" / "systems" / "custom"
            priv.mkdir(parents=True)
            (priv / "priv_test.yml").write_text(PRIVATE_DOC, encoding="utf-8")

            merged = gsite.build_payload(
                [gsite.SSRF_ROOT, pathlib.Path(tmp) / "ssrf"]
            )

        by_id = {f["id"]: f for f in merged["files"]}
        overlay = by_id["systems/custom/priv_test.yml"]
        # Overlay files are not in the public repo, so no public GitHub links
        # (they would 404). They are flagged local instead.
        self.assertTrue(overlay.get("local"))
        self.assertNotIn("url", overlay)
        self.assertNotIn("download_url", overlay)
        self.assertNotIn("doc_url", overlay)

        # Public files keep their links and are not flagged local.
        public = next(f for f in merged["files"] if not f.get("local"))
        self.assertIn("url", public)
        self.assertIn("download_url", public)
        self.assertTrue(public["url"].startswith("https://github.com/"))

    def test_detail_pages_written_for_public_files_only(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            priv = pathlib.Path(tmp) / "ssrf" / "systems" / "custom"
            priv.mkdir(parents=True)
            (priv / "priv_test.yml").write_text(PRIVATE_DOC, encoding="utf-8")
            payload = gsite.build_payload([gsite.SSRF_ROOT, pathlib.Path(tmp) / "ssrf"])

            out = pathlib.Path(tmp) / "site"
            written = gsite.write_detail_pages(out, payload)

            public = [f for f in payload["files"] if f.get("doc_url")]
            self.assertEqual(written, len(public))
            self.assertGreater(written, 0)
            for f in public:
                page = out / f["doc_url"]
                self.assertTrue(page.exists(), f"missing detail page {page}")
                text = page.read_text(encoding="utf-8")
                self.assertIn(f"<h1>{html.escape(f['title'])}</h1>", text)
                self.assertIn('<link rel="stylesheet" href="../style.css" />', text)
            self.assertFalse((out / gsite.DETAIL_DIR_NAME / "priv_test.html").exists())

    def test_region_grouping(self) -> None:
        region, group, topic = gsite._region(
            pathlib.Path("systems/US/IL/Cook/Chicago/amateur/ns9rc_repeaters.yml")
        )
        self.assertEqual((region, group, topic), ("US / IL / Cook / Chicago", "US / IL", "amateur"))
        region, group, topic = gsite._region(pathlib.Path("plans/US/gmrs/gmrs_channels.yml"))
        self.assertEqual((region, group, topic), ("US", "US", "gmrs"))
        region, group, topic = gsite._region(
            pathlib.Path("systems/US/FL/_Regional/florida_simulcast_group.yml")
        )
        self.assertEqual((region, group, topic), ("US / FL / Regional", "US / FL", None))
        self.assertEqual(
            gsite._region(pathlib.Path("systems/custom/mmdvm_duplex_hotspot.yml")),
            ("Global", "Global", None),
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
