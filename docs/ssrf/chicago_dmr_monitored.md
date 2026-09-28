# chicago_dmr_monitored

**Path:** `systems/US/IL/Cook/Chicago/business/chicago_dmr_monitored.yml`  
**Category:** Geographic System  
**Geographic Scope:** US / IL / Cook / Chicago  
**Primary Service:** business  

## Overview

- **Assignments:** 5
- **Services:** business_itinerant_part90
- **Organizations:** 1
- **Locations:** 1
- **RF Chains:** 4
- **Channel Plans:** 0
- **Contacts:** 5

### Modes
- **DMR:** 5

### Usage Types
- **Repeater:** 5

### Frequency Bands
- **UHF (400-480 MHz):** 5

## Organizations

- **Chicago DMR (monitor-confirmed, licensee unidentified)** (`org_chi_dmr_monitored`)

## Locations

### Chicago north side receive site (approx)
**Coordinates:** 41.9600, -87.6600

## Assignments

### Unknown (5 assignments)

- **asgn_chi_dmr_464_975** - repeater
  - *Monitor-confirmed DMR repeater output, timeslot 2 - talkgroups 1 and 1101, which together carry 80% of all voice traffic observed on this chain.*
- **asgn_chi_dmr_464_975_ts1** - repeater
  - *Same transmitter as asgn_chi_dmr_464_975, split out as a separate assignment for timeslot 1, which carries only TG 200 (1.0% of bursts, 5 radios). A receiver can only sit on one slot at a time, so monitoring both slots needs two channels.*
- **asgn_chi_dmr_462_1375** - repeater
  - *Monitor-confirmed DMR repeater output. Single-talkgroup operation (TG 50) on TS1.*
- **asgn_chi_dmr_452_3875** - repeater
  - *Monitor-confirmed Motorola Capacity Plus system, frequency confirmed by exact-channel dwell 2026-09-27. Still no talkgroup captured: 1.8 h of camps plus a dedicated continuous camp produced 14,892 CSBK and 8,173 Cap+ indications but zero decodable voice headers. On Capacity Plus the payload follows the rest slot as it moves, so a single fixed receiver on one channel sees control traffic almost exclusively - the earlier "traffic volume was too low" reading was wrong about the cause. Harvesting talkgroups here needs a trunk-following receiver driven by an LSN-to-frequency channel map, which does not exist yet.*
- **asgn_chi_dmr_453_5875** - repeater
  - *Monitor-confirmed DMR repeater output, timeslot 1 only, single talkgroup (TG 1). Downlink only - the uplink was never observed, so tx.freq_mhz is null rather than guessed from a standard Part 90 offset. Traffic carries the privacy bit, so this entry is a frequency and identity reference, not a listenable channel.*

## Authorization Requirements

### business_itinerant_part90
- **Authority:** FCC
- **Notes:** Part 90 licensed land mobile. Licensee not identified - these systems were located by spectrum survey, not from a published source, and no FCC ULS frequency search has been run against them yet. Receive-only reference data; transmitting on these channels requires the licensee's authority.
