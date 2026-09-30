#!/usr/bin/env python3
"""Write authored ``short_name`` values into amateur and GMRS files.

House style, as decided with the maintainer:

* amateur -- club + band (SARA2M, DARC7C); when a club runs more than one
  machine on a band, club(3) + the last three frequency digits (TRC475,
  TRC025); when the same frequency carries a second mode, club(4) + band digit
  + mode letter (NSRC2F / NSRC2C).
* GMRS -- system + site (NSEAPK, NSEAEV).

Re-runnable: an assignment that already declares a ``short_name`` is left
alone, so this can be pointed at a private overlay tree and run repeatedly.
Extend ``SHORT_NAMES`` with that tree's assignment ids first.
"""

from __future__ import annotations

import pathlib
import re
import sys

SHORT_NAMES: dict[str, dict[str, str]] = {
    "plans/US/amateur/ham_dmr_simplex.yml": {
        "asg_dmr_smpx_446500": "DMR500",
        "asg_dmr_smpx_446075": "DMR075",
        "asg_dmr_hs_4304125": "H30412",
        "asg_dmr_hs_4304250": "H30425",
        "asg_dmr_hs_4394125": "H39412",
        "asg_dmr_hs_4394250": "H39425",
        "asg_dmr_hs_duplex_4394375": "D39437",
        "asg_dmr_hs_duplex_4394500": "D39450",
        "asg_dmr_hs_duplex_4394625": "D39462",
        "asg_dmr_hs_duplex_4394750": "D39475",
        "asg_dmr_hs_duplex_4304375": "D30437",
        "asg_dmr_hs_duplex_4304500": "D30450",
        "asg_dmr_hs_duplex_4304625": "D30462",
        "asg_dmr_hs_duplex_4304750": "D30475",
    },
    "systems/US/FL/Hillsborough/Tampa/amateur/tarc_repeaters.yml": {
        "asgn_tarc_vhf": "TARC2M",
        "asgn_tarc_uhf1": "TRC475",
        "asgn_tarc_uhf2": "TRC025",
    },
    "systems/US/FL/_Regional/gmrs/st_pete_gmrs_repeaters.yml": {
        "asg_gmrs_seminole_725": "TBSEMI",
        "asg_gmrs_clearwater_675": "TBCLWR",
        "asg_gmrs_ruskin_700": "TBRUSK",
        "asg_gmrs_tampa_shores_700": "TBTSH7",
        "asg_gmrs_tampa_shores_650": "TBTSH6",
        "asg_gmrs_west_bradenton_625": "TBWBRA",
        "asg_gmrs_tampa_600": "TBTAMP",
        "asgn_gmrs_sun_sara_650": "SUNSAR",
        "asgn_gmrs_sun_venice_700": "SUNVEN",
        "asgn_gmrs_sun_englewood_675": "SUNENG",
        "asgn_gmrs_sun_bonita_575": "SUNBON",
        "asgn_gmrs_sun_duette_550": "SUNDUE",
    },
    "systems/US/IL/Cook/Chicago/amateur/cfmc_repeaters.yml": {
        "asgn_cfmc_440": "CFMC7F",
        "asgn_cfmc_2m": "CFM676",
        "asgn_cfmc_220_north": "CFM241",
        "asgn_cfmc_220_south": "CFM418",
        "asgn_cfmc_dstar_440": "CFMC7S",
        "asgn_cfmc_fusion_2m_fm": "CFM535",
        "asgn_cfmc_fusion_2m_c4fm": "CFM53C",
    },
    "systems/US/IL/Cook/Chicago/amateur/chicagoland_dmr_system.yml": {
        "asgn_cl_loop": "CLLOOP",
        "asgn_cl_schaumburg": "CLSCHM",
    },
    "systems/US/IL/Cook/Chicago/amateur/n9bbm_loop_repeater.yml": {
        "asgn_n9bbm_440_fm": "N9BBM",
    },
    "systems/US/IL/Cook/Chicago/amateur/ns9rc_repeaters.yml": {
        "asgn_ns9rc_2m_fm": "NSRC2F",
        "asgn_ns9rc_2m_c4fm": "NSRC2C",
        "asgn_ns9rc_220": "NSRC12",
        "asgn_ns9rc_440": "NSR725",
        "asgn_ns9rc_dstar_440": "NSR375",
        "asgn_ns9rc_dstar_23cm": "NSRC23",
        "asgn_ns9rc_aprs": "NSRAPR",
        "asgn_ns9rc_aprs_fill": "NSRAP5",
        "asgn_ns9rc_winlink": "NSRWIN",
        "asgn_ns9rc_beacon_10m": "NSRB10",
        "asgn_ns9rc_beacon_6m": "NSRB06",
        "asgn_ns9rc_simplex_446_025": "NSR025",
        "asgn_ns9rc_simplex_147_405": "NSR405",
        "asgn_ns9rc_simplex_146_460": "NSR460",
    },
    "systems/US/IL/Cook/Chicago/amateur/sara_repeaters.yml": {
        "asgn_ka9hhh_2m_fm": "SARA2M",
        "asgn_ka9hhh_440_fm": "SARA7C",
        "asgn_na9pl_440_c4fm": "PAA25C",
    },
    "systems/US/IL/Cook/Chicago/gmrs/chicago_gmrs_repeaters.yml": {
        "asgn_gmrs_lincolnwood_575": "LNWD57",
        "asgn_gmrs_chicago_600": "CHI600",
        "asgn_gmrs_ohare_575": "OHAR57",
        "asgn_gmrs_chicago_550": "CHI550",
        "asgn_gmrs_downtown_575": "DWTN57",
        "asgn_gmrs_forest_view_650": "FSTV65",
        "asgn_gmrs_oak_forest_625": "OAKF62",
        "asgn_gmrs_montclare_650": "MNTC65",
    },
    "systems/US/IL/Cook/Chicago/gmrs/family_channels.yml": {
        "asgn_family_f1_all": "FAM1AL",
        "asgn_family_f2_team_a": "FAM2TA",
        "asgn_family_f3_team_b": "FAM3TB",
        "asgn_family_f4_team_c": "FAM4TC",
        "asgn_family_f5_road": "FAM5RD",
        "asgn_family_f6_rptr": "FAM6RP",
        "asgn_family_f8_evnstn": "FAM8EV",
        "asgn_family_f9_prkrdg": "FAM9PR",
        "asgn_family_f10_evnst": "FAM10E",
        "asgn_family_f11_nrthbrk": "FAM11N",
        "asgn_family_f13_uhf_call": "FAM13U",
        "asgn_family_f14_ns9rc": "FAM14N",
        "asgn_family_f15_cmfc": "FAM15C",
        "asgn_family_fd1_all": "FD1ALL",
        "asgn_family_fd2_team_a": "FD2TMA",
        "asgn_family_fd3_team_b": "FD3TMB",
        "asgn_family_fd4_team_c": "FD4TMC",
    },
    "systems/US/IL/Cook/Northbrook/amateur/skokie_repeater_club.yml": {
        "asgn_skokie_rc_440_fm": "SKRC7C",
    },
    "systems/US/IL/Cook/_Countywide/amateur/paaros_repeaters.yml": {
        "asgn_na9pl_440_fm": "PAA250",
        "asgn_na9pl_440_c4fm": "PAA25C",
        "asgn_na9pl_440_500_fm": "PAA500",
        "asgn_na9pl_440_725_dstar": "PAA725",
    },
    "systems/US/IL/Cook/_Countywide/gmrs/nsea_gmrs_repeaters.yml": {
        "asgn_nsea_675": "NSEAPK",
        "asgn_nsea_650": "NSEANB",
        "asgn_nsea_700": "NSEAEV",
        "asgn_nsea_coop_evanston_725": "EVAN72",
    },
    "systems/US/IL/DuPage/DownersGrove/amateur/w9dup_darc_repeaters.yml": {
        "asgn_w9dup_2m_fm": "DARC2M",
        "asgn_w9dup_220_fm": "DARC12",
        "asgn_w9dup_440_fm": "DARC7C",
    },
    "systems/US/IL/Lake/Benton/gmrs/zion_gmrs_repeaters.yml": {
        "asgn_gmrs_zion_550": "ZION55",
    },
    "systems/US/IL/_Statewide/amateur/tri_state_dmr.yml": {
        "asgn_k9bar_bolingbrook": "TSDBOL",
        "asgn_n9pay_carlsville": "TSDCAR",
        "asgn_aa9vi_chicago": "TSDCHI",
        "asgn_k9vi_crystal_lake": "TSDCRY",
        "asgn_n9iaa_crown_point": "TSDCRP",
        "asgn_k9nro_elburn": "TSDELB",
        "asgn_n9pay_green_bay": "TSDGRB",
        "asgn_k9ord_inverness": "TSDINV",
        "asgn_n9iaa_la_porte": "TSDLAP",
        "asgn_n9pay_milwaukee": "TSDMIL",
        "asgn_kc9kko_morris": "TSDMOR",
        "asgn_n9pay_new_berlin": "TSDNWB",
        "asgn_ww9p_rockford": "TSDROC",
        "asgn_k9mot_schaumburg": "TSDSCH",
        "asgn_n8ouz_traverse_city": "TSDTRV",
        "asgn_n9iaa_valparaiso": "TSDVAL",
    },
    "systems/US/IN/LaPorte/LaPorte/amateur/laporte_county_amateur_radio_club.yml": {
        "asgn_k9jsi_vhf_fm": "LPC661",
        "asgn_w9ly_vhf_fm": "LPC697",
        "asgn_w9ly_vhf_c4fm": "LPC69C",
        "asgn_w9ly_uhf_fm": "LPC195",
        "asgn_w9ly_uhf_c4fm": "LPC19C",
        "asgn_w9sal_uhf_fm": "LPC495",
    },
    "systems/US/IN/Northwest/Regional/amateur/n9iaa_aresc_network.yml": {
        "asgn_n9iaa_146_fm": "ARSC2M",
        "asgn_n9iaa_valpo_dmr": "ARSCVA",
        "asgn_n9iaa_crownpoint_dmr": "ARSCCP",
        "asgn_n9iaa_laporte_dmr": "ARSCLP",
    },
    "systems/US/IN/StJoseph/Osceola/gmrs/osceola_gmrs_repeaters.yml": {
        "asgn_gmrs_osceola_600": "OSCE60",
    },
    "systems/US/MI/Berrien/Niles/amateur/kc8brs_four_flags.yml": {
        "asgn_kc8brs_vhf_fm": "FFRC2M",
    },
    "systems/US/MI/Berrien/_Countywide/amateur/berrien_county_amateur.yml": {
        "asg_skywarn_primary": "BCSW82",
        "asg_skywarn_secondary": "BCSW72",
        "asg_skywarn_intercounty": "BCSW43",
        "asg_skywarn_link": "BCSWLK",
        "asg_w8mai_dstar_b": "W8MAIB",
    },
    "systems/US/NJ/Sussex/Hopatcong/amateur/n2ozo_repeaters.yml": {
        "asgn_n2ozo_448175_fm": "N2OZOA",
        "asgn_n2ozo_448175_p25": "N2OZOD",
        "asgn_n2ozo_448825": "N2OZ82",
    },
    "systems/US/NJ/Sussex/Hopatcong/amateur/n2qjn_repeater.yml": {
        "asgn_n2qjn_224280": "N2QJN",
    },
    "systems/US/NJ/Sussex/Hopatcong/amateur/wr2m_repeater.yml": {
        "asgn_wr2m_448675": "WR2M7C",
    },
    "systems/US/NJ/Sussex/Newton/amateur/w2lv_repeaters.yml": {
        "asgn_w2lv_147210": "W2L210",
        "asgn_w2lv_147300": "W2L300",
        "asgn_w2lv_147330": "W2L330",
        "asgn_w2lv_224500": "W2LV12",
        "asgn_w2lv_443000": "W2LV7C",
    },
    "systems/US/NJ/Sussex/Vernon/amateur/w2ver_repeaters.yml": {
        "asgn_w2ver_6m": "W2VER6",
        "asgn_w2ver_2m": "W2VER2",
        "asgn_w2ver_70cm": "W2VER7",
        "asgn_w2ver_33cm_vernon": "W2V33V",
        "asgn_w2ver_33cm_hardyston": "W2V33H",
    },
    "systems/US/UT/Summit/ParkCity/gmrs/ecker_hill_gmrs.yml": {
        "asgn_gmrs_ecker_hill_575": "ECKH57",
    },
    "systems/US/WI/Monroe/Sparta/gmrs/gmrs_two_way_radio.yml": {
        "asgn_gmrs_sparta_625": "SPRT62",
    },
    "systems/US/WI/Racine/_Countywide/amateur/kr9rk_lakeshore_repeaters.yml": {
        "asgn_kr9rk_2m_fm": "LRA2M",
        "asgn_kr9rk_440_fm": "LRA7C",
        "asgn_kr9rk_440_dmr": "LRA7D",
    },
    "systems/US/WI/Racine/_Countywide/gmrs/real_fine_gmrs_repeaters.yml": {
        "asgn_gmrs_real_fine_650": "RFGM65",
    },
}

SSRF = pathlib.Path(__file__).parent / "ssrf"


def main() -> int:
    inserted = 0
    missed: list[str] = []

    for rel, mapping in SHORT_NAMES.items():
        path = SSRF / rel
        if not path.exists():
            missed.append(f"{rel}: file not found")
            continue

        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        out: list[str] = []
        seen: set[str] = set()

        # Assignments appear in block style (`- id: foo`) and in flow style
        # (`- {\n  id: foo,`); both carry the id on a line of its own.
        block = re.compile(r"^(\s*)-\s+id:\s*[\"']?([A-Za-z0-9_]+)[\"']?\s*$")
        flow = re.compile(r"^(\s*)id:\s*[\"']?([A-Za-z0-9_]+)[\"']?\s*,\s*$")

        for i, line in enumerate(lines):
            out.append(line)
            m = block.match(line)
            style_flow = False
            if not m:
                m = flow.match(line)
                style_flow = bool(m)
            if not m:
                continue
            indent, ident = m.group(1), m.group(2)
            if ident not in mapping or ident in seen:
                continue
            # Idempotent: leave a value that is already there alone.
            if i + 1 < len(lines) and "short_name:" in lines[i + 1]:
                seen.add(ident)
                continue
            seen.add(ident)
            value = mapping[ident]
            if style_flow:
                out.append(f'{indent}short_name: "{value}",\n')
            else:
                out.append(f'{indent}  short_name: "{value}"\n')
            inserted += 1

        for ident in mapping:
            if ident not in seen:
                missed.append(f"{rel}: {ident}")

        path.write_text("".join(out), encoding="utf-8")

    print(f"inserted {inserted} short_name values")
    if missed:
        print(f"MISSED {len(missed)}:")
        for m in missed:
            print(f"  {m}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
