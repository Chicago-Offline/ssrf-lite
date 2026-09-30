# cb_channels

**Path:** `plans/US/cb/cb_channels.yml`  
**Category:** Channel Plan  
**Geographic Scope:** US  
**Primary Service:** cb  

## Overview

- **Assignments:** 40
- **Services:** cb
- **Organizations:** 1
- **Locations:** 0
- **RF Chains:** 0
- **Channel Plans:** 1
- **Contacts:** 0

### Modes
- **FM:** 1600

### Usage Types
- **Simplex:** 40

### Frequency Bands
- **HF (<30 MHz):** 1600

## Organizations

- **Federal Communications Commission (FCC)** (`org_fcc`)

## Channel Plans

### US CB (Citizens Band) (`chplan_us_cb`)

| Channel | Frequency | Emission |
|---------|-----------|----------|
| CB 01 | 26.9650 MHz | N/A |
| CB 02 | 26.9750 MHz | N/A |
| CB 03 | 26.9850 MHz | N/A |
| CB 04 | 27.0050 MHz | N/A |
| CB 05 | 27.0150 MHz | N/A |
| CB 06 | 27.0250 MHz | N/A |
| CB 07 | 27.0350 MHz | N/A |
| CB 08 | 27.0550 MHz | N/A |
| CB 09 (Emergency) | 27.0650 MHz | N/A |
| CB 10 | 27.0750 MHz | N/A |
| CB 11 | 27.0850 MHz | N/A |
| CB 12 | 27.1050 MHz | N/A |
| CB 13 | 27.1150 MHz | N/A |
| CB 14 | 27.1250 MHz | N/A |
| CB 15 | 27.1350 MHz | N/A |
| CB 16 | 27.1550 MHz | N/A |
| CB 17 | 27.1650 MHz | N/A |
| CB 18 | 27.1750 MHz | N/A |
| CB 19 (Highway) | 27.1850 MHz | N/A |
| CB 20 | 27.2050 MHz | N/A |
| CB 21 | 27.2150 MHz | N/A |
| CB 22 | 27.2250 MHz | N/A |
| CB 23 | 27.2550 MHz | N/A |
| CB 24 | 27.2350 MHz | N/A |
| CB 25 | 27.2450 MHz | N/A |
| CB 26 | 27.2650 MHz | N/A |
| CB 27 | 27.2750 MHz | N/A |
| CB 28 | 27.2850 MHz | N/A |
| CB 29 | 27.2950 MHz | N/A |
| CB 30 | 27.3050 MHz | N/A |
| CB 31 | 27.3150 MHz | N/A |
| CB 32 | 27.3250 MHz | N/A |
| CB 33 | 27.3350 MHz | N/A |
| CB 34 | 27.3450 MHz | N/A |
| CB 35 | 27.3550 MHz | N/A |
| CB 36 | 27.3650 MHz | N/A |
| CB 37 | 27.3750 MHz | N/A |
| CB 38 | 27.3850 MHz | N/A |
| CB 39 | 27.3950 MHz | N/A |
| CB 40 | 27.4050 MHz | N/A |

## Assignments

### Unknown (40 assignments)

- **asgn_cb_01** - simplex
- **asgn_cb_02** - simplex
- **asgn_cb_03** - simplex
- **asgn_cb_04** - simplex
- **asgn_cb_05** - simplex
- **asgn_cb_06** - simplex
- **asgn_cb_07** - simplex
- **asgn_cb_08** - simplex
- **asgn_cb_09** - simplex
- **asgn_cb_10** - simplex
- **asgn_cb_11** - simplex
- **asgn_cb_12** - simplex
- **asgn_cb_13** - simplex
- **asgn_cb_14** - simplex
- **asgn_cb_15** - simplex
- **asgn_cb_16** - simplex
- **asgn_cb_17** - simplex
- **asgn_cb_18** - simplex
- **asgn_cb_19** - simplex
- **asgn_cb_20** - simplex
- **asgn_cb_21** - simplex
- **asgn_cb_22** - simplex
- **asgn_cb_23** - simplex
- **asgn_cb_24** - simplex
- **asgn_cb_25** - simplex
- **asgn_cb_26** - simplex
- **asgn_cb_27** - simplex
- **asgn_cb_28** - simplex
- **asgn_cb_29** - simplex
- **asgn_cb_30** - simplex
- **asgn_cb_31** - simplex
- **asgn_cb_32** - simplex
- **asgn_cb_33** - simplex
- **asgn_cb_34** - simplex
- **asgn_cb_35** - simplex
- **asgn_cb_36** - simplex
- **asgn_cb_37** - simplex
- **asgn_cb_38** - simplex
- **asgn_cb_39** - simplex
- **asgn_cb_40** - simplex

## Authorization Requirements

### cb
- **Authority:** FCC
- **Class:** Licensed by rule
- **Notes:** No individual license required under 47 CFR Part 95, Subpart D (95.305).
Power (95.967): AM (A3E) and FM (F3E) mean carrier power <= 4 W; SSB
(J3E/R3E/H3E) peak envelope power <= 12 W.
Emissions (95.971): A3E or SSB required; F3E permitted since the 2021
amendment (86 FR 53565). SSB sets must offer USB and may add LSB.
Bandwidth (95.973): 8 kHz for A3E/F3E, 4 kHz for J3E/R3E/H3E. All four
permitted emissions are carried on the channel plan's `emissions` block
and apply to every channel.
Channel 9 is restricted to emergency and traveler assistance (95.931(a)(2)).
External RF power amplifiers are prohibited outright (95.939).
Antenna height (95.941): <= 18.3 m (60 ft) AGL, or 6.1 m (20 ft) above the
building or tree it is mounted on, whichever is higher.
No repeaters. No international contacts except Canadian General Radio
Service stations (95.933(d)).

