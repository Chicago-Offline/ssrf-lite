# chicago_dmr_monitored

**Path:** `systems/US/IL/Cook/Chicago/business/chicago_dmr_monitored.yml`  
**Category:** Geographic System  
**Geographic Scope:** US / IL / Cook / Chicago  
**Primary Service:** business  

## Overview

- **Assignments:** 4
- **Services:** business_itinerant_part90
- **Organizations:** 1
- **Locations:** 1
- **RF Chains:** 3
- **Channel Plans:** 0
- **Contacts:** 4

### Modes
- **DMR:** 4

### Usage Types
- **Repeater:** 4

### Frequency Bands
- **UHF (400-480 MHz):** 4

## Organizations

- **Chicago DMR (monitor-confirmed, licensee unidentified)** (`org_chi_dmr_monitored`)

## Locations

### Chicago north side receive site (approx)
**Coordinates:** 41.9600, -87.6600

## Assignments

### Unknown (4 assignments)

- **asgn_chi_dmr_464_975** - repeater
  - *Monitor-confirmed DMR repeater output, timeslot 2 - talkgroups 1 and 1101, which together carry 80% of all voice traffic observed on this chain.*
- **asgn_chi_dmr_464_975_ts1** - repeater
  - *Same transmitter as asgn_chi_dmr_464_975, split out as a separate assignment for timeslot 1, which carries only TG 200 (1.0% of bursts, 5 radios). A receiver can only sit on one slot at a time, so monitoring both slots needs two channels.*
- **asgn_chi_dmr_462_1375** - repeater
  - *Monitor-confirmed DMR repeater output. Single-talkgroup operation (TG 50) on TS1.*
- **asgn_chi_dmr_452_3875** - repeater
  - *Monitor-confirmed Motorola Capacity Plus system. No talkgroup captured - traffic volume was too low during the survey window for a voice header to be decoded.*

## Authorization Requirements

### business_itinerant_part90
- **Authority:** FCC
- **Notes:** Part 90 licensed land mobile. Licensee not identified - these systems were located by spectrum survey, not from a published source, and no FCC ULS frequency search has been run against them yet. Receive-only reference data; transmitting on these channels requires the licensee's authority.
