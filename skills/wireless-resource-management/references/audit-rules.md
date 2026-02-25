# Audit Rules (Data Quality Rules)

Based on 综资省内模型20230215.xlsx

## Overview

Audit rules ensure data quality and compliance with business requirements. Rules are categorized by object type and field.

## Key Audit Rules (High Priority)

These three rules are considered high priority for periodic reporting:

1. **Cell-to-base station relationship**: Every cell (EUTRANCELL/NRCELL) must关联 a valid base station (ENODEB/G-NODEB) record. This ensures proper network topology and service attribution.

2. **Mandatory field completeness**: Required fields (必录字段) must be populated for each resource type. Missing mandatory fields impact data usability and reporting accuracy.

3. **Data logical consistency**: Business logic rules must be satisfied (e.g., maintenance type calculations, VIP level assignments, enumeration value compliance). Logical inconsistencies can lead to incorrect operational decisions.

These rules should be checked regularly and included in periodic audit reports.

## Cell Association Audit Rules

Based on the "合规率-合并.sql" script, these rules validate cell relationships and associations:

### Cell-to-Device Relationship Rules
- **AAU/RRU to Cell Association**: Each AAU/RRU must be properly associated with at least one cell through mapping tables (`wr_map_aau_cell`, `wr_map_rru_cell`)
- **Cell Count per Device**: A single RRU/AAU should not serve more than 8 cells (business rule 4.47)
- **Device Lifecycle Consistency**: Device lifecycle status should align with associated cell lifecycle status
- **Physical Device Location**: Remote units (RRU/AAU/Antenna) must have valid `room_id` linking to existing room records
- **Room to Site Association**: Rooms must have valid `station_id` linking to existing site records with coordinates
- **Base Station to Near-End Association**: Logical base stations (ENODEB/GNODEB) must associate with near-end units (BBU/DU) that have valid room associations

### Field Completeness for Cells
- **Cell Name**: Must be populated and not contain placeholder values like "未确认"
- **CGI Format**: Must follow standard format: 
  - 2G: "460-00-LAC-CI"
  - 4G: "ENODEBID-CI"  
  - 5G: "GNODEBID-CI"
- **Key Field Values**: `life_cycle_status_key`, `vip_level_key` must reference valid dimension table entries

### Dimension Table Referential Integrity
- All foreign keys to dimension tables (`dim_*`) must reference existing records
- Dimension table joins should return valid human-readable values
- Enumeration values must be within allowed ranges

### Example Audit Queries
```sql
-- Cells without valid base station association
SELECT cell_id, cellname 
FROM wr_logic_eutrancell
WHERE logic_enodeb_id NOT IN (SELECT enodeb_id FROM wr_logic_enodeb)
  AND is_del = false;

-- AAUs associated with more than 8 cells
SELECT aau_id, COUNT(DISTINCT logic_cell_id) as cell_count
FROM wr_map_aau_cell 
WHERE is_del = false
GROUP BY aau_id
HAVING COUNT(DISTINCT logic_cell_id) > 8;

-- Cells with invalid dimension table references
SELECT cell_id, life_cycle_status_key
FROM wr_logic_eutrancell
WHERE life_cycle_status_key NOT IN (SELECT life_cycle_status_key FROM dim_lifecyclestatus)
  AND is_del = false;

-- Remote units without room associations (missing location)
SELECT 'AAU' as device_type, aau_id as device_id, name
FROM npas.wr_device_aau
WHERE room_id IS NULL AND is_del = false
UNION ALL
SELECT 'RRU' as device_type, rru_id as device_id, name  
FROM npas.wr_device_rru
WHERE room_id IS NULL AND is_del = false
UNION ALL
SELECT 'Antenna' as device_type, ant_id as device_id, name
FROM npas.wr_device_ant
WHERE room_id IS NULL AND is_del = false;

-- Cells without any physical device association (missing location source)
SELECT cell.cell_id, cell.cellname
FROM npas.wr_logic_eutrancell cell
WHERE NOT EXISTS (
  SELECT 1 FROM npas.wr_map_rru_cell rc WHERE rc.logic_cell_id = cell.cell_id AND rc.is_del = false
) AND NOT EXISTS (
  SELECT 1 FROM npas.wr_map_aau_cell ac WHERE ac.logic_cell_id = cell.cell_id AND ac.is_del = false  
) AND NOT EXISTS (
  SELECT 1 FROM npas.wr_map_ant_cell antc WHERE antc.logic_cell_id = cell.cell_id AND antc.is_del = false
) AND NOT EXISTS (
  SELECT 1 FROM npas.wr_map_wids_cell wc WHERE wc.logic_cell_id = cell.cell_id AND wc.is_del = false
) AND cell.is_del = false;

-- ENODEB without BBU association (missing near-end unit)
SELECT enodeb_id, enodeb_name
FROM npas.wr_logic_enodeb
WHERE bbu_id IS NULL AND is_del = false;
```

## Mandatory Fields (必录字段)

Certain fields must be populated for each resource object:

### AAU
- AAU Identifier (AAU����)
- Installation Location (��������/λ�õ�)
- Device Detailed Installation Position (�豸��ϸ��װλ��)
- Connection Method (���뷽ʽ)
- Device Model (�豸�ͺ�)

### BBU
- BBU Identifier (BBU����)
- Installation Location (��������/��Դ��)
- Device Model (�豸�ͺ�)

### BTS
- BTS Identifier (��������������)
- Province (����ʡ)
- City (��������)

### CELL
- Optimization Identifier (�Ż�����)
- Province (����ʡ)
- City (��������)

### CU
- CU Identifier (CU����)
- Device Model (�豸�ͺ�)

### DU
- DU Identifier (DU����)
- Device Model (�豸�ͺ�)

### RRU
- RRU Identifier (RRU����)
- Installation Location (��������/λ�õ�)
- Device Detailed Installation Position (�豸��ϸ��װλ��)
- Connection Method (���뷽ʽ)
- Device Model (�豸�ͺ�)

### Antenna
- Antenna Identifier (��������)
- Installation Location (��������/λ�õ�)
- Device Detailed Installation Position (�豸��ϸ��װλ��)
- Connection Method (���뷽ʽ)
- Device Model (�豸�ͺ�)

## Compliance Rules (V1.2合规规则)

Rules are numbered and categorized:

### Category 1: Basic Rules (基础规则)
- **1.1**: Coordinates must be valid (latitude/longitude within China)
- **1.2**: Address must be complete (province, city, district, street, number)
- **1.3**: Site type must match actual deployment
- **1.4**: Maintenance level must be assigned based on scoring

### Category 2: Enumeration Rules (枚举合规)
- **2.1**: Field values must be from allowed enumeration lists
- **2.2**: Device types must match supported models
- **2.3**: Property nature must be correctly classified (owned/leased)

### Category 3: Relationship Rules (关系规则)
- **3.1**: Parent-child relationships must be valid (e.g., cell belongs to existing base station)
- **3.2**: Foreign key references must exist
- **3.3**: Circular references are prohibited

### Category 4: Business Logic Rules (业务逻辑规则)
- **4.1**: Maintenance type calculation must follow defined algorithms
- **4.2**: VIP level assignment must follow scoring rules
- **4.3**: Supporting facilities flag must be accurate based on actual equipment
- **4.4**: CRAN designation requires ≥5 active BBUs/DU

## Field Validation Rules

### Coordinate Validation
- Longitude: 73°E to 135°E (China territory)
- Latitude: 3°N to 54°N (China territory)
- Precision: At least 6 decimal places

### Address Validation
- Must contain province, city, district
- Street and number recommended
- Special characters limited

### Date Validation
- Installation date ≤ current date
- Decommissioning date ≥ installation date if present
- Maintenance dates within reasonable ranges

### Numeric Validation
- Positive values for counts, distances, heights
- Reasonable ranges for technical parameters
- Unit consistency

## Network Technology Compatibility

Fields must indicate correct network technology compatibility:

- **5G only**: 5G
- **4G only**: 4G
- **2G only**: 2G
- **Multi-mode**: Combinations like "5G&4G", "2G&4G"

## Maintenance Mode Requirements

### Collection Fields
- Must be synchronized from OMC regularly
- Update frequency: Daily for critical fields
- Source system must be documented

### System Fields
- Calculation formulas must be correct
- Inheritance chains must be complete
- No manual overrides allowed

### Manual Fields
- Must be reviewed periodically
- Change history must be maintained
- Approval workflows for critical changes

## Data Quality Scoring

Sites are scored based on:
1. **Coverage area** (30 points): Urban (30), suburban (24), town (20), rural (16)
2. **Coverage scenario** (10 points): Important scenarios (10), general scenarios (5)
3. **Network technology** (10 points): 5G (10), 4G (8), 2G (2)
4. **Traffic statistics** (20 points): 0-100Erl (10), 100-200Erl (15), >200Erl (20)
5. **Data volume** (30 points): 0-100GB (10), 100-200GB (20), >200GB (30)

**Scoring thresholds:**
- ≥80 points: VIP site
- <80 points: General site
- Special classification: VVIP sites (≤10% of total)

## Implementation Notes

- Rules are implemented in database constraints where possible
- Application logic enforces complex business rules
- Regular audit jobs run to identify violations
- Violation reports are generated for corrective action

## Rule Change Management

Rule changes follow formal process:
1. Requirement documentation
2. Impact analysis
3. Testing and validation
4. Deployment scheduling
5. Data cleanup if needed

Historical rule changes are documented in the "修改记录" sheet.