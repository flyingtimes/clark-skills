---
name: wireless-resource-management
description: Comprehensive skill for managing wireless base station databases, supporting query, statistics, data quality checking, report generation, and process guidance. Use when working with wireless resource data including base stations, cells, RRUs, antennas, towers, rooms, sites, etc. This skill provides domain knowledge, database schema, audit rules, and practical scripts for telecom engineers.
---

# Wireless Resource Management Skill

## Overview

This skill assists telecom engineers in managing wireless base station databases, particularly for provincial wireless network resource management. It covers resource models, database schema, audit rules, common queries, data quality checks, report generation, and process guidance.

## Key Features

- **Query and Statistics**: Classification statistics of base station information (macro站, 室分数量, high-speed rail, subway coverage scenarios)
- **Data Quality Checks**: Focus on periodic reporting with key audit rules:
  - Cell must关联 valid base station (relationship integrity)
  - Mandatory field completeness
  - Data logical consistency
- **Report Generation**: Output in **HTML and Word** formats (in addition to Excel and text)
- **Database Connection**: Support for local PostgreSQL instances (manually synchronized from internal network)
- **Process Guidance**: Data entry, modification, and decommissioning workflows
- **Security**: Password encryption, access control, data masking, audit logging
- **Future Extensibility**: Accommodates new device types, new audit rules, enhanced data analysis
- **Deployment Options**: Can be used as independent application or API service model for integration

## Resource Model

Wireless resource management involves 36 resource objects with 684 fields. Key objects include:

- **机房 (Room)**: Bridge between wireless resources and spatial resource sites
- **站点 (Site)**: Represents location information (coordinates, address)
- **室分系统 (Indoor Distribution System)**
- **铁塔 (Tower)**
- **BTS/ENODEB/G-NODEB**: Base station equipment
- **CELL/EUTRANCELL/NRCELL**: Cells
- **RRU/AAU**: Remote radio units
- **天线 (Antenna)**
- **板卡 (Card)**
- **CU/DU**: Centralized/ Distributed units

Each object has fields categorized as:
- **主键 (Primary Key)**: Unique identifier
- **外键 (Foreign Key)**: Relationships to other objects
- **专业字段 (Professional Fields)**: Resource attributes
- **显示字段 (Display Fields)**: Calculated or inherited fields

Maintenance modes:
- **采集 (Collection)**: Updated via OMC or other sources
- **系统 (System)**: Calculated or inherited automatically
- **人工 (Manual)**: Manually maintained

Detailed resource model documentation: [resource-model.md](references/resource-model.md)

## Distributed Deployment Architecture

In 4G/5G networks, base stations use distributed architecture with separation of near-end and far-end units:

### Near-End Units (Hosted in Rooms)
- **BBU (Baseband Unit)**: Processes baseband signals, typically installed in equipment rooms
- **DU (Distributed Unit)**: In 5G networks, handles lower-layer processing, also installed in rooms
- **CU (Centralized Unit)**: In 5G networks, handles higher-layer processing and control

### Far-End Units (Remote Radio Units - Physical Location)
- **RRU (Remote Radio Unit)**: 4G remote radio unit, includes radio components, installed at antenna sites
- **AAU (Active Antenna Unit)**: 5G integrated antenna and radio unit, installed at antenna sites
- **Antenna**: Traditional passive antennas, installed on towers or rooftops
- **Tower**: Physical structure supporting antennas and RRUs/AAUs

### Location Information Flow
Logical elements (cells, base stations) obtain location information through associations with physical devices:

1. **Cells (EUTRANCELL/NRCELL)** are logical entities without direct location information
2. **Cells associate** with RRUs/AAUs through mapping tables (`wr_map_rru_cell`, `wr_map_aau_cell`)
3. **RRUs/AAUs have** room associations (`room_id`) pointing to equipment rooms
4. **Rooms belong** to sites (`station_id`) which contain actual geographic coordinates
5. **Alternative path**: Cells can also associate with antennas (`wr_map_ant_cell`) or indoor systems (`wr_map_wids_cell`)

### Key Principles
- **Physical devices** (RRU, AAU, Antenna, Tower) have direct spatial associations (room, site coordinates)
- **Logical elements** (Cell, ENODEB, GNODEB) obtain location indirectly through device associations
- **Room** serves as the bridge between wireless resources and spatial location
- **Site** contains the actual geographic coordinates (latitude, longitude, address)

This architecture enables flexible deployment where baseband processing can be centralized (CRAN) while radio units are distributed across coverage areas.

## Database Schema

The database contains numerous tables and views. Key tables include:

- `cm_enodeb_enbfunction` - ENODEB functions
- `cm_cell_eutrancell` - EUTRAN cells
- `cm_com_gnbcucp_nrcellcu` - NR cells
- `de_cell` - Cell details
- `de_macro_station` - Macro station details
- `de_indoor` - Indoor system details
- `wr_device` - Hardware devices
- `wr_logic_eutrancell` - Logical EUTRAN cells
- `wr_sync_rc_*` - Synchronized resource tables
- `pl_cover_point` - Planning points (规划工单)
- `ac_access_solution`, `ac_access_batch`, `ac_access_batch_rel_rs` - Access solution and batch tables for planning associations

Full table dictionary: [table-dictionary.md](references/table-dictionary.md)

## Materialized View: mv_logic_element_device_room_station

**重要物化视图**：这是日常统计和查询最方便的综合性视图，将三大类资源信息关联在一起：

### 整合的资源类型
1. **逻辑资源**：小区（2G/4G/5G）、基站（ENODEB/GNODEB/BTS）
2. **硬件资源**：RRU、AAU、天线、室分系统（WIDS）、直放站、AP、BBU、DU等
3. **位置资源**：机房、站点、铁塔
4. **规划信息**：规划点、解决方案、批次等规划系统信息

### 主要字段
- `element_id`, `element_name` - 元素ID和名称（小区ID、基站ID）
- `device_uuid`, `device_name` - 设备UUID和名称（RRU_ID、AAU_ID等）
- `room_id`, `room_name` - 机房信息
- `station_id`, `station_name`, `city` - 站点信息
- `net_type` - 网络类型（'2G','4G','5G'）
- `element_type` - 元素类型（'gsmcell','eutrancell','nrcell','enb','gnb','bts'）
- `life_cycle_status` - 生命周期状态
- `longitude`, `latitude` - 地理坐标
- `element_planid`, `device_planid` - 规划信息
- `element_solutionid`, `device_solutionid` - 解决方案ID
- `element_batchid`, `device_batchid` - 批次ID

### 构建原理
该视图通过精心设计的CTE（公共表表达式）和UNION ALL合并多个数据源构建，确保数据完整性：

#### 1. 数据源结构
视图由三大部分组成：
- **有设备关联的记录**：来自12个`v_dw_*_room_station`子视图
- **无设备关联的记录**：来自`a`和`b` CTE，确保即使没有设备关联的资源也能出现在视图中
- **补充关联信息**：最终关联机房、站点和同步ID映射表

#### 2. 关键CTE设计
- **`a_1` / `a` CTE**：处理**没有设备关联的ENODEB记录**
  - 查找`wr_logic_enodeb`中未关联BBU、DU、AP的记录
  - 通过小区表获取生命周期状态（取最大值）和启用时间（取最小值）
  - 保留退网时间等关键字段
- **`b` CTE**：处理**没有设备关联的小区记录**（2G/4G/5G）
  - 分别处理`wr_logic_nrcell`、`wr_logic_eutrancell`、`wr_logic_gsmcell`
  - 左连接所有可能的设备关联表（AAU、天线、直放站、RRU、WIDS、AP）
  - WHERE条件确保所有设备ID为NULL，即无任何设备关联
  - 关联基站表获取节点B信息

#### 3. 子视图整合
`project` CTE通过UNION ALL合并以下12个子视图，每个子视图已预计算特定设备类型的关联链：
1. `v_dw_cell_rru_room_station` - 小区与RRU关联
2. `v_dw_cell_ant_room_station` - 小区与天线关联  
3. `v_dw_cell_aau_room_station` - 小区与AAU关联
4. `v_dw_cell_repeater_room_station` - 小区与直放站关联
5. `v_dw_cell_wids_room_station` - 小区与室分系统关联
6. `v_dw_enb_bbu_room_station` - ENODEB与BBU关联
7. `v_dw_enb_du_room_station` - ENODEB与DU关联
8. `v_dw_gnb_du_room_station` - GNODEB与DU关联
9. `v_dw_bts_room_station` - BTS关联
10. `v_dw_cell_ap_room_station` - 小区与AP关联
11. `v_dw_enb_ap_room_station` - ENODEB与AP关联
12. 补充`a`和`b` CTE的结果（无设备关联记录）

#### 4. 最终关联与增强
主查询将`project`结果与以下表关联：
- `wr_space_room`：获取机房详细信息，包括`owner`、`room_type`、`p_room_type`（用于计算`is_virtual_room`）
- `wr_space_station`：获取站点详细信息，包括`longitude`、`latitude`、`tower_add_code`
- `rc_sync_id_map`：获取**同步ID映射**，通过两个子查询分别获取`station_cuid`和`room_cuid`
  - 这是与其他系统（如资源中心RC）集成的关键字段
  - `res_type`字段区分'station'和'room'类型

#### 5. 数据完整性设计
- **软删除处理**：所有关联都包含`is_del = false`或`is_delete = false`条件
- **维度表关联**：通过`dim_lifecyclestatus`获取生命周期状态，使用`curr_flag = true`过滤当前有效值
- **虚拟机房识别**：基于`wr_space_room.p_room_type`计算`is_virtual_room`字段
- **聚合处理**：使用`string_agg`聚合多个铁塔地址编码

### 使用优势
1. **查询简便**：单表查询即可获取完整资源链信息
2. **统计方便**：便于按网络类型、设备类型、位置等维度统计
3. **数据完整**：包含规划系统和生命周期状态信息
4. **性能优化**：物化视图提供较好的查询性能

### 典型查询示例
```sql
-- 查找小区完整信息
SELECT * FROM npas.mv_logic_element_device_room_station
WHERE element_type IN ('gsmcell', 'eutrancell', 'nrcell')
  AND element_id = '小区ID';

-- 按城市统计设备数量（注意：统计元素数量必须去重）
SELECT city, net_type, 
       COUNT(DISTINCT element_id) as element_count,  -- 去重统计元素数量
       COUNT(DISTINCT device_uuid) as device_count   -- 去重统计设备数量
FROM npas.mv_logic_element_device_room_station
WHERE device_uuid IS NOT NULL
GROUP BY city, net_type;
```

**更多实用查询示例**：更多基于业务场景的MV视图查询示例，包括故障排查、容量规划、网络演进分析、业务质量保障、数据质量监控等，请参见 [query-examples.md#物化视图高级应用查询](references/query-examples.md#物化视图高级应用查询)。

### 作为查询脚本的主要数据源

在回答用户关于生成查询脚本的问题时，应优先使用此物化视图作为数据源，因为它提供了最完整的资源关联信息。以下指导原则适用于基于此视图的查询生成：

1. **优先使用MV表**：对于需要关联逻辑资源、硬件资源和位置资源的查询，直接使用`mv_logic_element_device_room_station`视图，避免复杂的多表连接。
2. **字段选择策略**：
   - 使用`element_id`, `element_name`获取逻辑资源信息
   - 使用`device_uuid`, `device_name`获取硬件资源信息  
   - 使用`room_id`, `room_name`, `station_id`, `station_name`, `longitude`, `latitude`获取位置信息
   - 使用`net_type`, `element_type`进行网络类型和元素类型过滤
   - 使用`life_cycle_status`过滤生命周期状态
   - 使用`element_planid`, `device_planid`等字段获取规划信息
3. **常见查询模式**：
   - **定位查询**：通过`element_id`或`device_uuid`查找完整资源链
   - **统计查询**：按`city`, `net_type`, `element_type`等字段分组统计
   - **数据质量检查**：检查`device_uuid`为NULL的记录（未关联设备的元素）
   - **规划信息查询**：通过`element_planid`等字段关联规划系统
4. **性能优化**：
   - 物化视图已预计算关联，查询性能较好
   - 在`element_id`, `device_uuid`, `room_id`, `station_id`等字段上创建索引
   - 定期刷新物化视图以保持数据最新：`REFRESH MATERIALIZED VIEW npas.mv_logic_element_device_room_station;`

**示例脚本生成模板**：
```sql
-- 模板：根据[维度]统计[指标]
-- 注意：统计元素数量必须使用COUNT(DISTINCT element_id)，统计设备数量根据需求决定是否去重
SELECT [维度字段], 
       COUNT(DISTINCT element_id) as 元素数量,  -- 去重统计元素
       COUNT(DISTINCT device_uuid) as 设备数量, -- 去重统计设备（可选）
       [聚合函数] as 指标
FROM npas.mv_logic_element_device_room_station
WHERE [过滤条件]
GROUP BY [维度字段]
ORDER BY [排序字段];

-- 模板：查找[元素]的完整信息
SELECT element_id, element_name, device_uuid, device_name, 
       room_name, station_name, city, longitude, latitude
FROM npas.mv_logic_element_device_room_station
WHERE element_type = '[元素类型]' AND element_id = '[元素ID]';
```

### 物化视图脚本工具
基于此物化视图，提供了专门的Python脚本工具：

- **`find_rru_planning_mv.py`**：使用物化视图查询RRU序列号和PL规划点编号
  - 相比传统多表连接，查询更简单、性能更好
  - 支持序列号、规划点编码、城市等多维度过滤
  - 提供模拟数据模式用于测试
  - 支持JSON和文本格式输出

**主要优势**：
1. **查询简化**：将复杂的12表连接简化为单表查询
2. **性能优化**：物化视图预计算关联，查询速度更快
3. **数据完整**：包含规划信息、同步ID、虚拟机房标识等丰富字段
4. **易于使用**：提供命令行接口和详细的帮助信息

**使用示例**：
```bash
# 按序列号查询
python scripts/find_rru_planning_mv.py --serial "SN2024"

# 按规划点编码和城市查询
python scripts/find_rru_planning_mv.py --planning-code "PLAN-001" --city "上海"

# 使用模拟数据测试
python scripts/find_rru_planning_mv.py --mock

# JSON格式输出
python scripts/find_rru_planning_mv.py --serial "SN2024" --json
```

详细文档： [mv-logic-element-device-room-station.md](references/mv-logic-element-device-room-station.md)

## Planning Point Association System (规划点关联系统)

Every wireless resource (cell, base station, device) is associated with a planning point (`pl_cover_point`) that represents the original planning information for the site where the resource was deployed. This system tracks how resources enter the network from planning stages.

### Key Tables for Planning Associations
- **`pl_cover_point`**: Main planning point table containing site planning information, geographic details, and planning parameters
- **`ac_access_solution`**: Access solutions linking planning to implementation
- **`ac_access_batch`**: Implementation batches grouping multiple resources
- **`ac_access_batch_rel_rs`**: Relationship table connecting batches to actual resources (RS = Resource)

### Association Path
Wireless resources obtain planning information through this chain:
```
无线资源 (cell/enodeb/etc.) → ac_access_batch_rel_rs → ac_access_batch → ac_access_solution → pl_cover_point
```

### Key Fields
- `site_planning_id`: Primary key in `pl_cover_point`, links to `ac_access_solution.site_planning_id`
- `rs_cuid`: Resource CUID in `ac_access_batch_rel_rs`, matches resource IDs (e.g., `cell_id::text`)
- `access_batch_id`: Links `ac_access_batch_rel_rs` to `ac_access_batch`
- `access_solution_id`: Links `ac_access_batch` to `ac_access_solution`

### Purpose and Use Cases
1. **Traceability**: Track which planning project each resource belongs to
2. **Quality Control**: Compare planned vs. actual deployment parameters
3. **Historical Analysis**: Understand network evolution from planning stages
4. **Audit Compliance**: Verify resources were properly authorized through planning process

This association is essential for complete cell information queries, as planning points contain critical metadata like band, station type, coverage type, and network technology that may not be directly stored in resource tables.

## Enumeration Field Management (Key-Value System)

In the wireless resource database, most enumeration fields use a key-value management system through dimension tables (`dim_*` tables). This design ensures data consistency and allows centralized management of allowed values.

### Key Concepts
- **Key Fields**: Business tables contain fields ending with `_key` (e.g., `life_cycle_status_key`, `vip_level_key`, `device_model_key`)
- **Dimension Tables**: Tables prefixed with `dim_` store the mapping between keys and human-readable values
- **Referential Integrity**: All key fields must reference valid entries in corresponding dimension tables
- **Centralized Maintenance**: Enumeration values are maintained in dimension tables, ensuring consistency across the system

### Common Dimension Tables
Based on the "维护字段解析v3.xlsx" documentation, key dimension tables include:
- `dim_lifecyclestatus` - Life cycle status values (现网有业务, 退网, 预分配, etc.)
- `dim_viplevel` - VIP level classifications (VVIP, VIP, 一般)
- `dim_device_model` - Device models and specifications
- `dim_device_vendor` - Equipment manufacturers
- `dim_room_type` - Room type classifications (无线机房, 综合机房, 室外柜, etc.)
- `dim_site_type` - Site type categories (宏站, 室分, 微站, etc.)
- `dim_tower_type` - Tower structure types (单管塔, 角钢塔, 楼面塔, etc.)
- `dim_antenna_type` - Antenna type classifications
- `dim_maintenance_level` - Maintenance difficulty levels (高, 中, 一般)
- `dim_band` - Frequency band designations (800MHz, 900MHz, 1800MHz, etc.)
- `dim_covtype` - Coverage type classifications
- `dim_networktype` - Network technology types (2G, 4G, 5G)
- `dim_grid` - Geographic grid divisions
- `dim_subarea` - Subordinate area classifications

### Query Pattern for Value Decoding
To retrieve human-readable values, always join with dimension tables:
```sql
SELECT 
  cell.cell_id,
  cell.cellname,
  dl.life_cycle_status,  -- Decoded from life_cycle_status_key
  dv.vip_level,          -- Decoded from vip_level_key
  db.band                -- Decoded from band_key
FROM npas.wr_logic_eutrancell cell
LEFT JOIN npas.dim_lifecyclestatus dl ON cell.life_cycle_status_key = dl.life_cycle_status_key
LEFT JOIN npas.dim_viplevel dv ON cell.vip_level_key = dv.vip_level_key
LEFT JOIN npas.pl_cover_point pcp ON pcp.site_planning_id = (...)
LEFT JOIN npas.dim_band db ON pcp.band_key = db.band_key;
```

### Data Quality Implications
- **Mandatory Validation**: All key fields must reference existing dimension table entries
- **Enumeration Compliance**: Field values must be from allowed lists defined in dimension tables
- **Audit Rule 2.1**: Enumeration values must conform to allowed enumeration lists (from audit rules)
- **Referential Integrity**: Broken dimension references indicate data quality issues

### Maintenance Considerations
- **Change Management**: Updates to dimension tables affect all referencing records
- **Historical Values**: Dimension tables may include historical values with `curr_flag` indicators
- **Multi-language Support**: Some dimension tables may contain labels in multiple languages
- **Hierarchical Values**: Certain dimensions (like `dim_grid`) may have hierarchical relationships

Detailed enumeration field definitions and allowed values are documented in "维护字段解析v3.xlsx".

## Audit Rules (Data Quality Checks)

Common audit rules include:

1. **Mandatory fields**: Certain fields must be populated (e.g., coordinates, address)
2. **Data consistency**: Relationships between objects must be valid (especially cell-to-base station associations)
3. **Enumeration values**: Field values must conform to allowed enumerations
4. **Business logic**: Maintenance type calculations, VIP level assignments

**Key audit rules** (high priority):
- **Cell-to-base station relationship**: Every cell must关联 a valid base station record
- **Mandatory field completeness**: Required fields must be populated for each resource type
- **Data logical consistency**: Business logic rules must be satisfied (e.g., maintenance type calculations)

Detailed audit rules: [audit-rules.md](references/audit-rules.md)

## Common Queries

Use PostgreSQL queries to retrieve resource information. Examples:

- List all base stations in a city
- Count cells per base station
- Find RRUs without associated antennas
- Identify sites with missing coordinates

Query examples: [query-examples.md](references/query-examples.md)

## Data Quality Checking

Run automated data quality checks using Python scripts:

```bash
python scripts/check_mandatory_fields.py
python scripts/validate_relationships.py
python scripts/check_coordinates.py
python scripts/audit_cell_associations.py
```

Scripts are in the `scripts/` directory.

### Advanced Scripts

Additional specialized scripts for common operations:

- **`find_cell_location.py`**: Trace cell location through device associations
  ```bash
  python scripts/find_cell_location.py "cell_id"
  python scripts/find_cell_location.py "cell_id" --json
  ```

- **`audit_cell_associations.py`**: Audit cell device associations for data quality
  ```bash
  python scripts/audit_cell_associations.py --network 4G --limit 50
  python scripts/audit_cell_associations.py --json
  ```

- **`find_rru_planning.py`**: Find RRU serial numbers and planning point associations (traditional joins)
  ```bash
  python scripts/find_rru_planning.py --serial "SN12345"
  python scripts/find_rru_planning.py --planning-id "PLAN001" --limit 20
  python scripts/find_rru_planning.py --json
  ```

- **`find_rru_planning_mv.py`**: Find RRU serial numbers using materialized view (recommended)
  ```bash
  python scripts/find_rru_planning_mv.py --serial "SN2024"
  python scripts/find_rru_planning_mv.py --planning-code "PLAN-001" --city "上海"
  python scripts/find_rru_planning_mv.py --mock  # Use mock data for testing
  python scripts/find_rru_planning_mv.py --json
  ```

These scripts implement complex query patterns from the original SQL scripts, making them accessible for daily operations.

## Report Generation

Generate reports in multiple formats:

- **Text**: Simple console output
- **Excel**: Spreadsheet with multiple sheets
- **HTML**: Web-friendly formatted report
- **Word**: Professional document format

Use `scripts/generate_report.py` with format parameters. For HTML and Word reports, additional packages may be required.

## Database Connection

If you have a local PostgreSQL database with wireless resource data, configure connection in `scripts/db_config.py` or use environment variables.

Default connection parameters:
- Host: localhost
- Port: 5432
- Database: wireless_db
- Username: postgres

Use the PostgreSQL tool via `postgresql_postgresql_execute_query` for direct queries.

## Offline Usage

When database connectivity is not available, you can work with exported data:

1. **Export data to CSV**: Use PostgreSQL COPY command or pgAdmin export feature to create CSV files of key tables.

2. **Use pandas for analysis**: Load CSV files into pandas DataFrames for analysis and reporting.

Example:
```python
import pandas as pd
sites_df = pd.read_csv('wr_space_site.csv')
cells_df = pd.read_csv('wr_sync_rc_eutrancell.csv')
```

3. **Modify scripts for offline use**: Update the scripts to accept a `--data-dir` parameter pointing to CSV files.

A sample offline adaptation is provided in `scripts/generate_report_offline.py` (to be created).

## Security Considerations

When deploying this skill or related scripts:

- **Password encryption**: Store database credentials encrypted using keyring or environment variables
- **Access control**: Limit database access to authorized users only
- **Data masking**: Mask sensitive information in reports (e.g., site addresses, coordinates)
- **Audit logging**: Log all data access and modification activities
- **Network security**: Ensure database connections use SSL/TLS when possible

See [security.md](references/security.md) for detailed security guidelines.

## Deployment Options

This skill can be deployed in different ways:

1. **Standalone CLI Tool**: Run scripts directly on a workstation with database access
2. **Web Application**: Build a Flask/FastAPI service with HTML frontend
3. **API Service**: Expose functionality as REST API for integration with other systems
4. **Scheduled Jobs**: Automate report generation and data quality checks via cron or task scheduler

Reference implementation examples: [api-service-example.md](references/api-service-example.md)

## Process Guidance

Guidance for data entry, modification, and decommissioning processes based on organizational workflows. See [process-guide.md](references/process-guide.md).

## Quick Start

1. Review resource model in `references/resource-model.md`
2. Examine database schema in `references/table-dictionary.md`
3. Run data quality checks: `python scripts/check_mandatory_fields.py`
4. Execute workflow demo: `python scripts/workflow_demo.py "cell_id"`

## Tutorial and Workflow Demo

A comprehensive tutorial is available to help you get started with common tasks:

- [tutorial.md](references/tutorial.md) - Step-by-step tutorial for cell troubleshooting
- `workflow_demo.py` - Combined workflow script that integrates location finding, planning lookup, and data quality audit

The tutorial walks through a typical scenario:
1. Locate a problematic cell's physical equipment
2. Check planning information for deployment context
3. Audit data quality for completeness
4. Generate maintenance reports

Use the workflow demo script for quick analysis:
```bash
python scripts/workflow_demo.py "EUT-123456"
python scripts/workflow_demo.py "NR-789012" --json
```

## References

- [resource-model.md](references/resource-model.md) - Detailed resource object definitions
- [table-dictionary.md](references/table-dictionary.md) - Database table structures
- [audit-rules.md](references/audit-rules.md) - Data quality audit rules
- [query-examples.md](references/query-examples.md) - SQL query examples
- [quick-reference.md](references/quick-reference.md) - Quick reference for telecom engineers
- [tutorial.md](references/tutorial.md) - Step-by-step tutorial for cell troubleshooting
- [process-guide.md](references/process-guide.md) - Operational process guidance
- [security.md](references/security.md) - Security best practices
- [api-service-example.md](references/api-service-example.md) - API service implementation examples