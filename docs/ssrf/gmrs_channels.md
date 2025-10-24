# gmrs_channels

**Path:** `plans/US/gmrs/gmrs_channels.yml`  
**Category:** Channel Plan  
**Geographic Scope:** US  
**Primary Service:** gmrs  

## Overview

- **Assignments:** 30
- **Services:** gmrs
- **Organizations:** 1
- **Locations:** 0
- **RF Chains:** 0
- **Channel Plans:** 1
- **Contacts:** 0

### Modes
- **FM:** 660

### Usage Types
- **Simplex:** 15
- **Repeater:** 8
- **Receive-Only:** 7

### Frequency Bands
- **UHF (400-480 MHz):** 660

## Organizations

- **Federal Communications Commission (FCC)** (`org_fcc`)

## Channel Plans

### US GMRS (`chplan_us_gmrs`)

| Channel | Frequency | Emission |
|---------|-----------|----------|
| GMRS 01 | 462.5625 MHz | 11K2F3E |
| GMRS 02 | 462.5875 MHz | 11K2F3E |
| GMRS 03 | 462.6125 MHz | 11K2F3E |
| GMRS 04 | 462.6375 MHz | 11K2F3E |
| GMRS 05 | 462.6625 MHz | 11K2F3E |
| GMRS 06 | 462.6875 MHz | 11K2F3E |
| GMRS 07 | 462.7125 MHz | 11K2F3E |
| GMRS 08 | 467.5625 MHz | 11K2F3E |
| GMRS 09 | 467.5875 MHz | 11K2F3E |
| GMRS 10 | 467.6125 MHz | 11K2F3E |
| GMRS 11 | 467.6375 MHz | 11K2F3E |
| GMRS 12 | 467.6625 MHz | 11K2F3E |
| GMRS 13 | 467.6875 MHz | 11K2F3E |
| GMRS 14 | 467.7125 MHz | 11K2F3E |
| GMRS 15 | 462.5500 MHz | 20K0F3E |
| GMRS 16 | 462.5750 MHz | 20K0F3E |
| GMRS 17 | 462.6000 MHz | 20K0F3E |
| GMRS 18 | 462.6250 MHz | 20K0F3E |
| GMRS 19 | 462.6500 MHz | 20K0F3E |
| GMRS 20 | 462.6750 MHz | 20K0F3E |
| GMRS 21 | 462.7000 MHz | 20K0F3E |
| GMRS 22 | 462.7250 MHz | 20K0F3E |

## Assignments

### Unknown (30 assignments)

- **asgn_gmrs_01** - simplex
- **asgn_gmrs_02** - simplex
- **asgn_gmrs_03** - simplex
- **asgn_gmrs_04** - simplex
- **asgn_gmrs_05** - simplex
- **asgn_gmrs_06** - simplex
- **asgn_gmrs_07** - simplex
- **asgn_gmrs_08** - receive-only
- **asgn_gmrs_09** - receive-only
- **asgn_gmrs_10** - receive-only
- **asgn_gmrs_11** - receive-only
- **asgn_gmrs_12** - receive-only
- **asgn_gmrs_13** - receive-only
- **asgn_gmrs_14** - receive-only
- **asgn_gmrs_15** - simplex
- **asgn_gmrs_16** - simplex
- **asgn_gmrs_17** - simplex
- **asgn_gmrs_18** - simplex
- **asgn_gmrs_19** - simplex
- **asgn_gmrs_20** - simplex
- **asgn_gmrs_21** - simplex
- **asgn_gmrs_22** - simplex
- **asgn_gmrs_rpt_15** - repeater
  - *Repeater output 462.5500 MHz, input 467.5500 MHz (+5.000). Set local tone as required.*
- **asgn_gmrs_rpt_16** - repeater
  - *Repeater output 462.5750 MHz, input 467.5750 MHz (+5.000). Set local tone as required.*
- **asgn_gmrs_rpt_17** - repeater
  - *Repeater output 462.6000 MHz, input 467.6000 MHz (+5.000). Set local tone as required.*
- **asgn_gmrs_rpt_18** - repeater
  - *Repeater output 462.6250 MHz, input 467.6250 MHz (+5.000). Set local tone as required.*
- **asgn_gmrs_rpt_19** - repeater
  - *Repeater output 462.6500 MHz, input 467.6500 MHz (+5.000). Set local tone as required.*
- **asgn_gmrs_rpt_20** - repeater
  - *Repeater output 462.6750 MHz, input 467.6750 MHz (+5.000). Set local tone as required.*
- **asgn_gmrs_rpt_21** - repeater
  - *Repeater output 462.7000 MHz, input 467.7000 MHz (+5.000). Set local tone as required.*
- **asgn_gmrs_rpt_22** - repeater
  - *Repeater output 462.7250 MHz, input 467.7250 MHz (+5.000). Set local tone as required.*

## Authorization Requirements

### gmrs
- **Authority:** FCC
- **Class:** License required
- **Notes:** GMRS simplex permitted on 462 MHz interstitial (Ch 1-7) and main 462 MHz (Ch 15-22). 
467 MHz interstitial (Ch 8-14) are FRS-only simplex; GMRS licensees should not transmit on these frequencies 
except as repeater inputs where authorized. Marked as Rx-only here for GMRS use.

