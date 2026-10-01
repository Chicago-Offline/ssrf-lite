# nifog_federal

**Path:** `plans/US/interop/nifog_federal.yml`  
**Category:** Channel Plan  
**Geographic Scope:** US  
**Primary Service:** interop  

## Overview

- **Assignments:** 25
- **Services:** federal_interop_ntia
- **Organizations:** 2
- **Locations:** 0
- **RF Chains:** 0
- **Channel Plans:** 1
- **Contacts:** 0

### Modes
- **FM:** 625

### Usage Types
- **Simplex:** 14
- **Repeater:** 11

### Frequency Bands
- **UHF (400-480 MHz):** 325
- **VHF (136-174 MHz):** 300

## Organizations

- **National Telecommunications and Information Administration (NTIA)** (`org_ntia`)
- **Cybersecurity and Infrastructure Security Agency (CISA)** (`org_cisa`)

## Channel Plans

### US NIFOG Federal Interoperability (analog) (`chplan_us_nifog_federal`)

| Channel | Frequency | Emission | Mode |
|---------|-----------|----------|------|
| NC 1 | 169.5375 MHz | N/A | FM CTCSS rx 167.9 Hz |
| IR 1 | 170.0125 MHz | N/A | FM CTCSS rx 167.9 Hz |
| IR 2 | 170.4125 MHz | N/A | FM CTCSS rx 167.9 Hz |
| IR 3 | 170.6875 MHz | N/A | FM CTCSS rx 167.9 Hz |
| IR 4 | 173.0375 MHz | N/A | FM CTCSS rx 167.9 Hz |
| IR 5 | 169.5375 MHz | N/A | FM |
| IR 6 | 170.0125 MHz | N/A | FM |
| IR 7 | 170.4125 MHz | N/A | FM |
| IR 8 | 170.6875 MHz | N/A | FM |
| IR 9 | 173.0375 MHz | N/A | FM |
| LE A | 167.0875 MHz | N/A | FM |
| LE 1 | 167.0875 MHz | N/A | FM |
| NC 2 | 410.2375 MHz | N/A | FM CTCSS rx 167.9 Hz |
| IR 10 | 410.4375 MHz | N/A | FM CTCSS rx 167.9 Hz |
| IR 11 | 410.6375 MHz | N/A | FM CTCSS rx 167.9 Hz |
| IR 12 | 410.8375 MHz | N/A | FM CTCSS rx 167.9 Hz |
| IR 13 | 413.1875 MHz | N/A | FM |
| IR 14 | 413.2125 MHz | N/A | FM |
| IR 15 | 410.2375 MHz | N/A | FM |
| IR 16 | 410.4375 MHz | N/A | FM |
| IR 17 | 410.6375 MHz | N/A | FM |
| IR 18 | 410.8375 MHz | N/A | FM |
| LE B | 414.0375 MHz | N/A | FM |
| LE 10 | 409.9875 MHz | N/A | FM |
| LE 16 | 409.9875 MHz | N/A | FM |

## Assignments

### Unknown (25 assignments)

- **asgn_nifog_fed_nc_1** - repeater
- **asgn_nifog_fed_ir_1** - repeater
- **asgn_nifog_fed_ir_2** - repeater
- **asgn_nifog_fed_ir_3** - repeater
- **asgn_nifog_fed_ir_4** - repeater
- **asgn_nifog_fed_ir_5** - simplex
- **asgn_nifog_fed_ir_6** - simplex
- **asgn_nifog_fed_ir_7** - simplex
- **asgn_nifog_fed_ir_8** - simplex
- **asgn_nifog_fed_ir_9** - simplex
- **asgn_nifog_fed_le_a** - simplex
- **asgn_nifog_fed_le_1** - repeater
- **asgn_nifog_fed_nc_2** - repeater
- **asgn_nifog_fed_ir_10** - repeater
- **asgn_nifog_fed_ir_11** - repeater
- **asgn_nifog_fed_ir_12** - repeater
- **asgn_nifog_fed_ir_13** - simplex
- **asgn_nifog_fed_ir_14** - simplex
- **asgn_nifog_fed_ir_15** - simplex
- **asgn_nifog_fed_ir_16** - simplex
- **asgn_nifog_fed_ir_17** - simplex
- **asgn_nifog_fed_ir_18** - simplex
- **asgn_nifog_fed_le_b** - simplex
- **asgn_nifog_fed_le_10** - repeater
- **asgn_nifog_fed_le_16** - simplex

## Authorization Requirements

### federal_interop_ntia
- **Authority:** NTIA
- **Class:** Federal assignment
- **Notes:** Nationwide federal interoperability channels (Incident Response "IR", National Calling "NC",
and Federal Law Enforcement "LE") coordinated by NTIA and published in the CISA National
Interoperability Field Operations Guide (NIFOG) 2.02.

TRANSMIT IS LIMITED TO FEDERAL AGENCIES AND THOSE OPERATING UNDER A FEDERAL AGENCY'S
AUTHORIZATION. There is no license class available to amateur or GMRS operators that confers
transmit privileges here. Treat every channel in this plan as receive-only.

NC/IR repeater channels require a 167.9 Hz mobile transmit CTCSS tone and are carrier
squelch on receive; that is carried as structured `mode` data (`ctcss_rx_hz` from the
repeater's perspective). Simplex channels and the LE repeaters are carrier squelch.

SCOPE: this plan records only the ANALOG FM federal interoperability channels. The federal law
enforcement channels that are P25-only (LE 2 through LE 9 on VHF, and LE 11 through LE 15 plus
LE 17 and LE 18 on UHF, all using NAC $68F) are deliberately omitted, because they are not
receivable on the analog/DMR radios this dataset feeds. Add them as a separate P25 pass if a
P25-capable receiver is introduced.

Several IR channels intentionally share a frequency with the repeater output of a lower-numbered
channel (IR 5-9 with NC 1/IR 1-4, IR 15-18 with NC 2/IR 10-12, LE 16 with LE 10). These are
distinct channel designators on the same frequency, not duplicates in error.

