# Database Table Dictionary

Based on NPAS全量视图和表字典20250625(1).xlsx

## Overview

The database contains hundreds of tables and views covering wireless resources, hardware, logical elements, planning, and operational data.

## Key Tables by Category

### Resource Tables
- `cm_enodeb_enbfunction` - ENODEB functions
- `cm_cell_eutrancell` - EUTRAN cells
- `cm_com_gnbcucp_nrcellcu` - NR cells
- `cm_com_managede_gnbcucpfunction` - Managed GNBCUCP functions
- `de_cell` - Cell details
- `de_macro_station` - Macro station details
- `de_indoor` - Indoor system details
- `de_micro_station` - Micro station details
- `de_pullout_station` - Pullout station details
- `de_repeater_station` - Repeater station details
- `de_score` - Site scoring

### Hardware Device Tables
- `wr_device` - Hardware devices master table
- `wr_device_ac_distribution` - AC distribution devices
- `wr_device_accumulator` - Accumulator devices
- `wr_device_air_conditioner` - Air conditioner devices
- `wr_device_switching_power` - Switching power devices
- `wr_device_ups` - UPS devices
- `hw_hardware_allot` - Hardware allocation
- `hw_hardware_allot` - Hardware warehouse

### Logical Element Tables
- `wr_logic_eutrancell` - Logical EUTRAN cells (4G小区主表)
- `wr_logic_gsmcell` - Logical GSM cells (2G小区主表)
- `wr_logic_nrcell` - Logical NR cells (5G小区主表)
- `wr_logic_eutrancell_temp` - Temporary EUTRAN cells

**Cell Table Relationships:**
- 2G cells (`wr_logic_gsmcell`) associate with BTS via `site_id` linking to `wr_device_bts`
- 4G cells (`wr_logic_eutrancell`) associate with ENODEB via `logic_enodeb_id` linking to `wr_logic_enodeb`
- 5G cells (`wr_logic_nrcell`) associate with GNODEB via `gnodeb_id` linking to `wr_logic_gnodeb`
- Cells can only associate with logical station tables (not directly with spatial tables)
- **Device associations through mapping tables**: Logical cells obtain location information by associating with physical devices:
  - `wr_map_rru_cell` - RRU to cell associations (4G remote units)
  - `wr_map_aau_cell` - AAU to cell associations (5G active antenna units)  
  - `wr_map_ant_cell` - Antenna to cell associations (passive antennas)
  - `wr_map_wids_cell` - Indoor system to cell associations (室分系统)
- **Physical device location**: RRU/AAU/Antenna devices have `room_id` linking to `wr_space_room`
- **Room to site**: Rooms have `station_id` linking to `wr_space_station` for geographic coordinates
- **Base station associations**: Logical base stations (ENODEB/GNODEB) associate with near-end units:
  - ENODEB links to BBU via `bbu_id`
  - GNODEB links to DU via `related_du_cuid`
  - BBU/DU have `room_id` for location

### Spatial Resource Tables
- `wr_space_room` - Rooms
- `wr_space_site` - Sites
- `wr_space_tower` - Towers
- `wr_space_station` - Stations

### Synchronized Resource Tables
- `wr_sync_rc_aau` - Synchronized AAU resources
- `wr_sync_rc_ant` - Synchronized antenna resources
- `wr_sync_rc_bbu` - Synchronized BBU resources
- `wr_sync_rc_cell` - Synchronized cell resources
- `wr_sync_rc_enodeb` - Synchronized ENODEB resources
- `wr_sync_rc_eutrancell` - Synchronized EUTRAN cell resources
- `wr_sync_rc_gnodeb` - Synchronized GNODEB resources
- `wr_sync_rc_rru` - Synchronized RRU resources
- `wr_sync_rc_tower` - Synchronized tower resources

### Planning Tables
- `pl_cell` - Planning cells
- `pl_macro_station` - Planning macro stations
- `pl_indoor` - Planning indoor systems
- `pl_micro_station` - Planning micro stations
- `pl_pullout_station` - Planning pullout stations
- `pl_plan` - Planning master
- `pl_report_stats_default` - Planning statistics
- `pl_cover_point` - Planning points (规划工单), containing site planning information, geographic details, and planning parameters

**Planning Point Association Tables:**
- `ac_access_solution` - Access solutions linking planning points to implementation batches
- `ac_access_batch` - Implementation batches grouping multiple resources for deployment
- `ac_access_batch_rel_rs` - Relationship table connecting batches to actual resources (RS = Resource)

**Planning Association System:**
Every wireless resource is associated with a planning point through the following chain:
```
无线资源 (cell/enodeb/etc.) → ac_access_batch_rel_rs → ac_access_batch → ac_access_solution → pl_cover_point
```

**Key Relationships:**
- Resources link to `ac_access_batch_rel_rs` via `rs_cuid` matching resource IDs (e.g., `cell_id::text`)
- `ac_access_batch_rel_rs.access_batch_id` links to `ac_access_batch.access_batch_id`
- `ac_access_batch.access_solution_id` links to `ac_access_solution.access_solution_id`
- `ac_access_solution.site_planning_id` links to `pl_cover_point.site_planning_id`

**Purpose:** This association system tracks how resources enter the network from planning stages, enabling traceability, quality control, and historical analysis of network deployment.

### Audit and Quality Tables
- `wr_audit_sys_config` - Audit system configuration
- `wr_audit_sys_config_field` - Audit field configuration
- `meta_check_enodeb` - ENODEB metadata check
- `meta_check_*` - Various metadata check tables

### Dimension Tables (`dim_*`)

Dimension tables implement the key-value enumeration system used throughout the database. Business tables store keys (fields ending with `_key`) that reference these dimension tables to obtain human-readable values.

**Core Dimension Tables:**
- `dim_lifecyclestatus` - Life cycle status values (现网有业务, 退网, 预分配, 工程中, etc.)
- `dim_viplevel` - VIP level classifications (VVIP, VIP, 一般)
- `dim_device_model` - Device models and technical specifications
- `dim_device_vendor` - Equipment manufacturers and vendors
- `dim_room_type` - Room type classifications (无线机房, 综合机房, 室外柜, 壁挂, 简易杆, etc.)
- `dim_site_type` - Site type categories (宏站, 室分, 微站, 拉远站, 直放站)
- `dim_tower_type` - Tower structure types (单管塔, 角钢塔, 楼面塔, 增高架, etc.)
- `dim_antenna_type` - Antenna type classifications
- `dim_maintenance_level` - Maintenance difficulty levels (高, 中, 一般)

**Additional Dimension Tables:**
- `dim_band` - Frequency band designations (800MHz, 900MHz, 1800MHz, 2100MHz, 2600MHz, etc.)
- `dim_covtype` - Coverage type classifications
- `dim_networktype` - Network technology types (2G, 4G, 5G, 多模)
- `dim_grid` - Geographic grid divisions for planning
- `dim_gridroad` - Road-based grid divisions
- `dim_subarea` - Subordinate area classifications (城区, 县城, 农村, 主城区, 一般城区, etc.)
- `dim_stationtype` - Station type details
- `dim_towersharer` - Tower sharing arrangements
- `dim_towerowner` - Tower ownership entities
- `dim_devicevendor` - Device vendor information (may overlap with dim_device_vendor)

**Key Characteristics:**
1. **Primary Key**: Usually `{table_name}_key` (e.g., `life_cycle_status_key`, `vip_level_key`)
2. **Display Fields**: Contain human-readable values (Chinese labels)
3. **Current Flag**: Some tables include `curr_flag` to indicate active vs. historical values
4. **Order Fields**: Some include `lifecycle_order` or similar for sorting
5. **Code Fields**: May include standardized codes in addition to descriptive labels

**Usage Pattern:**
```sql
-- Decode keys to human-readable values
SELECT 
  cell.cell_id,
  cell.cellname,
  dl.life_cycle_status,  -- From dim_lifecyclestatus
  dv.vip_level,          -- From dim_viplevel
  db.band                -- From dim_band
FROM wr_logic_eutrancell cell
LEFT JOIN dim_lifecyclestatus dl ON cell.life_cycle_status_key = dl.life_cycle_status_key
LEFT JOIN dim_viplevel dv ON cell.vip_level_key = dv.vip_level_key
LEFT JOIN pl_cover_point pcp ON ...
LEFT JOIN dim_band db ON pcp.band_key = db.band_key;
```

**Data Quality Requirements:**
- All `_key` fields in business tables must reference valid dimension table entries
- Dimension table joins should never return NULL for required fields
- Enumeration values must be from allowed lists defined in dimension tables
- Referential integrity must be maintained for all key references

### Materialized View: mv_logic_element_device_room_station

**重要物化视图**：这是日常使用最方便的综合性视图，将逻辑资源、硬件资源和位置资源关联在一起。

**包含的资源类型**：
1. **逻辑资源**：小区（2G/4G/5G）、基站（ENODEB/GNODEB/BTS）
2. **硬件资源**：RRU、AAU、天线、室分系统（WIDS）、直放站、AP、BBU、DU等
3. **位置资源**：机房、站点、铁塔
4. **规划信息**：规划点、解决方案、批次等

**主要字段**：
- `element_id`, `element_name` - 元素ID和名称
- `device_uuid`, `device_name` - 设备UUID和名称
- `room_id`, `room_name` - 机房信息
- `station_id`, `station_name`, `city` - 站点信息
- `net_type` - 网络类型（'2G','4G','5G'）
- `element_type` - 元素类型（'gsmcell','eutrancell','nrcell','enb','gnb','bts'）
- `life_cycle_status` - 生命周期状态
- `longitude`, `latitude` - 地理坐标
- `element_planid`, `device_planid` - 规划信息
- `element_solutionid`, `device_solutionid` - 解决方案ID
- `element_batchid`, `device_batchid` - 批次ID

**构建原理**：通过UNION ALL合并多个`v_dw_*_room_station`视图和CTE结果，最终关联机房、站点和同步ID映射表。

**使用优势**：
1. **查询简便**：单表查询即可获取完整资源链信息
2. **统计方便**：便于按网络类型、设备类型、位置等维度统计
3. **数据完整**：包含规划系统和生命周期状态信息
4. **性能优化**：物化视图提供较好的查询性能

**详细文档**：[mv-logic-element-device-room-station.md](mv-logic-element-device-room-station.md)

### View Tables
Many views prefixed with `v_`, `v_dw_`, `v_wr_`, `v_de_`, `v_pl_`, `v_re_`, `v_st_` providing aggregated and transformed data.

## Table Structure Pattern

Most tables follow a similar structure with:
- Primary key field (usually ending with `_id` or `_key`)
- Foreign key fields linking to related tables
- Business attribute fields
- Maintenance metadata (created time, updated time, operator)
- Lifecycle status fields

## Relationships

Key relationships:
- Sites contain rooms
- Rooms contain devices (BBU, RRU, etc.)
- Cells belong to base stations (ENODEB/GNODEB)
- RRUs/AAUs serve cells
- Antennas connect to RRUs/AAUs
- Towers host antennas
- Wireless resources associate with planning points through access solution chain

**Planning Point Associations:**
- Every wireless resource (cell, base station, device) is associated with a planning point (`pl_cover_point`)
- Association path: Resource → `ac_access_batch_rel_rs` → `ac_access_batch` → `ac_access_solution` → `pl_cover_point`
- Planning points contain critical metadata: band, station type, coverage type, network technology

**Complete Location Tracing:**
For complete cell information, trace through both physical and planning associations:
1. **Physical location**: Cell → RRU/AAU/Antenna → Room → Station → Coordinates
2. **Planning information**: Cell → Access batch relations → Planning point → Planning metadata
3. **Dimension decoding**: Join `dim_*` tables for human-readable values of all `_key` fields

## Field Naming Conventions

- Chinese field names for business attributes
- English field names for technical identifiers
- Suffixes like `_id`, `_name`, `_type`, `_date`, `_status` indicate field purpose

## Data Sources

- OMC collection for equipment data
- Manual entry for business attributes
- System calculation for derived fields
- Synchronization from external systems

## Usage Notes

- Tables with prefix `wr_` are part of the wireless resource system
- Tables with prefix `cm_` are configuration management tables
- Tables with prefix `de_` are data entry tables
- Tables with prefix `pl_` are planning tables
- Views with prefix `v_` are for reporting and analysis

For detailed field-level information, refer to the original Excel file or query the database schema directly.