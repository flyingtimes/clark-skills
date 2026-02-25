# Wireless Resource Model

## Overview

Wireless resource management involves managing resource objects and their fields. There are 36 resource objects with 684 fields covering the entire lifecycle from requirements, design, acceptance to decommissioning.

## Resource Objects

| Object | Field Count | Object | Field Count | Object | Field Count |
|--------|-------------|--------|-------------|--------|-------------|
| 机房 (Room) | 77 | BTS | 23 | 天线小区关联关系 (Antenna-Cell Relationship) | 6 |
| 站点 (Site) | 57 | CELL | 23 | 物理天线 (Physical Antenna) | 27 |
| 室分系统 (Indoor Distribution System) | 17 | 直放站 (Repeater) | 20 | CU | 7 |
| 铁塔 (Tower) | 23 | 一体化皮飞AP (Integrated Pico/Femto AP) | 12 | DU | 9 |
| OMC | 10 | AAU | 20 | 板卡 (Card) | 31 |
| OMC板卡 (OMC Card) | 8 | AAU与小区关系 (AAU-Cell Relationship) | 6 | 机房与电表关联关系 (Room-Meter Relationship) | 2 |
| BSC | 11 | 物理AAU (Physical AAU) | 32 | 机房与电费合同关联关系 (Room-Electricity Contract Relationship) | 3 |
| BBU | 12 | RRU | 14 | 机房与租费合同关联关系 (Room-Rental Contract Relationship) | 3 |
| G-NODEB | 30 | 物理RRU (Physical RRU) | 32 | 室分系统与小区关联 (Indoor System-Cell Relationship) | 5 |
| NR-CELL | 32 | RRU场景映射表 (RRU Scene Mapping) | 5 | 无源波分 (Passive WDM) | 9 |
| ENODEB | 40 | RRU与小区关系 (RRU-Cell Relationship) | 5 | 无源波分端口 (Passive WDM Port) | 13 |
| E-UTRANCELL | 31 | 天线 (Antenna) | 16 | 场景表 (Scene Table) | 13 |

## Field Categories

### Field Nature
1. **主键 (Primary Key)**: Unique identifier field, manually maintained. Example: ENODEB-ID
2. **外键 (Foreign Key)**: Establishes relationships with other objects, mostly manually maintained. Example: Belonging Room/Resource Point, Belonging MME
3. **专业字段 (Professional Field)**: Records resource object attributes, most common fields, maintained via collection or manual. Example: VIP Level, Transmission Type
4. **显示字段 (Display Field)**: Can be presented or calculated through relationships, maintained by system. Example: Belonging County, Longitude, Latitude (inherited from room/site)

### Maintenance Mode
1. **采集 (Collection)**: Updated through OMC or other sources. Example: Software version, manufacturer in ENODEB template
2. **系统 (System)**: Updated via internal calculations, inheritance from upstream/downstream relationships, or association with status database. Example: Belonging county, longitude, latitude inherited from room/site
3. **人工 (Manual)**: Manually maintained. Example: VIP Level field

### Field Types
- Association, Enumeration, Character, Number, Date (5 types)

### Required Fields
Fields marked as required must be populated. Manually maintained fields are either required or conditionally required.

## Key Object Details

### Room (机房)
Rooms serve as bridges connecting wireless resources to spatial resource sites. Not limited to physical rooms; any new location point requires a virtual room to host remote resources.

**Key Fields:**
- Primary Key: Room Identifier
- Foreign Key: Site Identifier
- Display Fields: Belonging region, city, floor location (auto-generated from site)
- Manual Professional Fields: Room type, business level, provincial room type, property nature, property unit, sharing unit

**Property Nature:**
- Owned: Property unit is China Mobile
- Leased: Leased from other units (including landlords or tower companies)

**Room Product Classification:**
- Color steel plate, brick-concrete, integrated cabinet, wall-mounted (no room), simple pole (no room)

### Site (站点)
Sites represent location information in the system. All wireless resource coordinates and addresses are derived through associated sites.

**Key Fields:**
- Primary Key: Site Identifier
- Display Fields: Address, lifecycle status, business level, building, associated profession, whether contains配套, maintenance level, maintenance type (auto-generated)
- Manual Professional Fields: Site type, geographical environment, associated tower company site code, sensitive site flag

**Maintenance Difficulty:**
- Medium: Vehicle inaccessible, need to walk 1-2km; distance 100-200km; mountain site 100-200m elevation
- High: Walk >2km; need boat; distance >200km; mountain elevation >200m
- Other: Baseline difficulty

**Maintenance Type:**
Calculated by system based on rules:
- CRAN: Site with ≥5 active BBUs/DU (macro基站)
- 基站 (Base Station): Site with ≥1 active macro base station (outdoor coverage)
- 微蜂窝 (Microcell): Site with micro base stations (outdoor coverage)
- 拉远站点 (Remote Site): Site without local BBU but with remote RRU/AAU
- 室外直放站 (Outdoor Repeater): Site with outdoor repeaters
- 室分信源 (Indoor Source): Site with indoor microcells

**Whether Contains配套 (Supporting Facilities):**
- Outdoor sites: If room type is wireless room, property unit not China Tower, and supporting property belongs to China Mobile → "Yes"
- Indoor sites: Additional requirement of distribution system property belonging to China Mobile

**Maintenance Level:**
- VVIP: Covering party/government/military organs, key transportation hubs, core business districts, major enterprise clients, etc. (≤10%)
- VIP: Score ≥80 based on coverage area, scenario, station type, traffic statistics (≤20%)
- General: Score <80

### Other Objects
Detailed field specifications for each object are available in the original documentation.

## Data Quality Impact

Resource data quality affects:
- Network optimization strategies
- Planning and construction rationality
- Maintenance quality improvement
- Settlement cost accuracy

## Field Management Requirements

Each field has requirements for:
- Field name (unique within object)
- Maintenance mode
- Field nature
- Field type
- Required or not