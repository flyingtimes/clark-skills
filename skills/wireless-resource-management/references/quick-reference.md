# Wireless Resource Management Quick Reference

## Core Concepts

### Distributed Deployment Architecture
- **Near-end units**: BBU/DU located in equipment rooms
- **Far-end units**: RRU/AAU/antennas located at physical sites
- **Mapping tables**: Connect logical cells to physical devices (`wr_map_*_cell`)
- **Location hierarchy**: Cell → Device → Room → Station → Coordinates

### Dimension Table System
- All enumeration fields use `_key` references to `dim_*` tables
- Centralized value management for consistency
- Examples: `dim_lifecyclestatus`, `dim_viplevel`, `dim_band`
- Always join dimension tables to get human-readable values

### Planning Point Association System
- Every wireless resource associates with a planning point (`pl_cover_point`)
- Tracks how resources enter network from planning stages
- Association chain: Resource → `ac_access_batch_rel_rs` → `ac_access_batch` → `ac_access_solution` → `pl_cover_point`
- Planning points contain critical metadata: band, station type, coverage type, network technology
- Essential for complete cell information and audit compliance

### Cell Types and Tables
| Network | Cell Table | Station Table | Key Relationships |
|---------|------------|---------------|-------------------|
| 2G | `wr_logic_gsmcell` | `wr_device_bts` | `site_id` → BTS |
| 4G | `wr_logic_eutrancell` | `wr_logic_enodeb` | `logic_enodeb_id` → ENODEB |
| 5G | `wr_logic_nrcell` | `wr_logic_gnodeb` | `gnodeb_id` → GNODEB |

## Essential Queries

### 1. Find Cell Location
```sql
-- Trace through device associations to find physical location
SELECT cell.cell_id, cell.cellname, device.device_type,
       room.room_name, station.station_name, station.latitude, station.longitude
FROM (
    SELECT cell_id, cellname FROM wr_logic_gsmcell WHERE cell_id = 'cell_id'
    UNION ALL SELECT eutrancell_id, eutrancell_name FROM wr_logic_eutrancell WHERE eutrancell_id = 'cell_id'
    UNION ALL SELECT nrcell_id, nrcell_name FROM wr_logic_nrcell WHERE nrcell_id = 'cell_id'
) cell
CROSS JOIN LATERAL (
    SELECT 'RRU' as device_type, rru.room_id FROM wr_map_rru_cell rc
    JOIN wr_device_rru rru ON rc.rru_id = rru.rru_id WHERE rc.logic_cell_id = cell.cell_id LIMIT 1
    UNION ALL SELECT 'AAU', aau.room_id FROM wr_map_aau_cell ac JOIN wr_device_aau aau ON ac.aau_id = aau.aau_id WHERE ac.logic_cell_id = cell.cell_id LIMIT 1
) device
LEFT JOIN wr_space_room room ON room.room_id = device.room_id
LEFT JOIN wr_space_station station ON room.station_id = station.station_id;
```

### 2. Get Planning Information for Cell
```sql
-- Retrieve planning point information for a cell
SELECT cell.cell_id, cell.cellname,
       pcp.site_planning_name,
       db.band, ds.station_type, dc.cover_type, dn.network_type
FROM wr_logic_eutrancell cell
LEFT JOIN ac_access_batch_rel_rs aabrr ON cell.cell_id::text = aabrr.rs_cuid::text
LEFT JOIN ac_access_batch aab ON aabrr.access_batch_id = aab.access_batch_id
LEFT JOIN ac_access_solution aas ON aab.access_solution_id = aas.access_solution_id
LEFT JOIN pl_cover_point pcp ON aas.site_planning_id = pcp.site_planning_id
LEFT JOIN dim_band db ON pcp.band_key = db.band_key
LEFT JOIN dim_stationtype ds ON pcp.station_type_key = ds.station_type_key
LEFT JOIN dim_covtype dc ON pcp.cover_type_key = dc.covtype_key
LEFT JOIN dim_networktype dn ON pcp.network_type_key = dn.network_type_key
WHERE cell.cell_id = 'cell_id';
```

### 3. Get Complete Cell Information
```sql
-- Join dimension tables for decoded values
SELECT cell.cell_id, cell.cellname,
       dl.life_cycle_status, dv.vip_level,
       room.room_name, station.station_name
FROM wr_logic_eutrancell cell
LEFT JOIN dim_lifecyclestatus dl ON cell.life_cycle_status_key = dl.life_cycle_status_key
LEFT JOIN dim_viplevel dv ON cell.vip_level_key = dv.vip_level_key
LEFT JOIN (
    SELECT room_id FROM wr_map_rru_cell rc
    JOIN wr_device_rru rru ON rc.rru_id = rru.rru_id
    WHERE rc.logic_cell_id = cell.eutrancell_id LIMIT 1
) device ON true
LEFT JOIN wr_space_room room ON room.room_id = device.room_id
LEFT JOIN wr_space_station station ON room.station_id = station.station_id;
```

### 4. Room Device Inventory
```sql
-- Count devices by type in a room
SELECT room.room_name,
       COUNT(DISTINCT bbu.bbu_id) as bbu_count,
       COUNT(DISTINCT rru.rru_id) as rru_count,
       COUNT(DISTINCT aau.aau_id) as aau_count
FROM wr_space_room room
LEFT JOIN wr_device_bbu bbu ON room.room_id = bbu.room_id AND bbu.is_del = false
LEFT JOIN wr_device_rru rru ON room.room_id = rru.room_id AND rru.is_del = false
LEFT JOIN wr_device_aau aau ON room.room_id = aau.room_id AND aau.is_del = false
WHERE room.room_id = 'room_id'
GROUP BY room.room_name;
```

### 5. Data Quality Checks
```sql
-- Mandatory field validation
SELECT 'Missing coordinates' as issue, COUNT(*) as count
FROM wr_space_station WHERE latitude IS NULL OR longitude IS NULL
UNION ALL
SELECT 'Orphaned cells', COUNT(*)
FROM wr_logic_eutrancell c
LEFT JOIN wr_logic_enodeb e ON c.logic_enodeb_id = e.enodeb_id
WHERE e.enodeb_id IS NULL;
```

## Python Scripts Reference

### find_cell_location.py
```bash
# Find location of a cell
python find_cell_location.py "cell_id"
python find_cell_location.py "cell_id" --json  # JSON output
```

### validate_relationships.py
```bash
# Check referential integrity
python validate_relationships.py
```

### check_mandatory_fields.py
```bash
# Validate mandatory fields
python check_mandatory_fields.py
```

### generate_report.py
```bash
# Generate data quality report
python generate_report.py --output report.csv
```

## Common Workflows

### 1. Cell Troubleshooting
1. Identify cell ID from alarms or performance data
2. Use `find_cell_location.py` to locate physical equipment
3. Check device associations in mapping tables
4. Verify room and station information

### 2. Data Quality Audit
1. Run `validate_relationships.py` to check referential integrity
2. Run `check_mandatory_fields.py` for mandatory field validation
3. Generate comprehensive report with `generate_report.py`
4. Review and fix issues identified

### 3. Room Capacity Planning
1. Query device counts per room
2. Check power and space utilization
3. Identify rooms needing expansion
4. Plan equipment redistribution

### 4. Planning Point Verification
1. Check planning associations for new resources
2. Verify planning vs. actual deployment consistency
3. Audit planning metadata completeness
4. Track resources to original planning projects

## Key Tables Reference

### Logical Elements
- `wr_logic_gsmcell` - 2G cells
- `wr_logic_eutrancell` - 4G cells  
- `wr_logic_nrcell` - 5G cells
- `wr_logic_enodeb` - 4G base stations
- `wr_logic_gnodeb` - 5G base stations

### Physical Devices
- `wr_device_bbu` - Baseband units
- `wr_device_du` - Distributed units (5G)
- `wr_device_rru` - Remote radio units
- `wr_device_aau` - Active antenna units
- `wr_device_ant` - Antennas
- `wr_device_wids` - Wireless distribution systems

### Space/Location
- `wr_space_room` - Equipment rooms
- `wr_space_station` - Physical stations/sites
- `wr_space_site` - Site information (deprecated in newer models)

### Mapping Tables
- `wr_map_rru_cell` - RRU to cell associations
- `wr_map_aau_cell` - AAU to cell associations
- `wr_map_ant_cell` - Antenna to cell associations
- `wr_map_wids_cell` - WIDS to cell associations

### Dimension Tables
- `dim_lifecyclestatus` - Life cycle status codes
- `dim_viplevel` - VIP level codes
- `dim_band` - Frequency band codes
- `dim_stationtype` - Station type codes
- `dim_networktype` - Network type codes

### Planning Tables
- `pl_cover_point` - Planning points (规划工单)
- `ac_access_solution` - Access solutions
- `ac_access_batch` - Implementation batches
- `ac_access_batch_rel_rs` - Resource-batch relationships

## Troubleshooting Tips

### Cell Not Found
1. Check if cell exists in appropriate table (2G/4G/5G)
2. Verify `is_del = false` filter
3. Check for data synchronization issues

### Missing Location Information
1. Trace through device associations (RRU → AAU → Antenna → WIDS)
2. Verify mapping table entries exist
3. Check room and station records are not deleted

### Performance Issues
1. Add indexes on frequently joined columns
2. Use `EXPLAIN ANALYZE` to identify bottlenecks
3. Consider partitioning large tables by date/region

## Best Practices

1. **Always join dimension tables** to get human-readable values
2. **Include `is_del = false`** filter to exclude deleted records
3. **Use parameterized queries** to prevent SQL injection
4. **Regularly validate relationships** to maintain data integrity
5. **Backup before bulk operations** on production data

## Materialized View Quick Reference

### mv_logic_element_device_room_station
**核心物化视图**：整合逻辑资源、硬件资源和位置资源，是日常查询最方便的数据源。基于对`MV视图脚本.sql`的深入分析，以下是关键知识点：

#### 1. 数据完整性设计
- **无设备关联记录保留**：通过`a`和`b` CTE确保即使没有关联设备的资源也出现在视图中
- **软删除统一处理**：所有关联包含`is_del = false`或`is_delete = false`条件
- **维度表当前值**：使用`dim_lifecyclestatus.curr_flag = true`获取最新生命周期状态

#### 2. 关键系统集成字段
- **同步ID映射**：`station_cuid`, `room_cuid`来自`rc_sync_id_map`，是无线资源系统与资源中心(RC)集成的关键
- **规划系统追溯**：`element_planid`, `device_planid`, `element_solutionid`, `device_solutionid`等字段支持规划→实施全程追溯
- **虚拟机房标识**：`is_virtual_room`基于`wr_space_room.p_room_type`自动计算

#### 3. 时间维度管理
- **启用时间**：`use_time` - 资源投入业务使用时间
- **退网时间**：`exit_time` - 资源退出服务时间  
- **安装时间**：`setup_time` - 设备物理安装时间
- **时间分析**：支持按年、月进行资源投入/退网分析

#### 4. 关键字段扩展说明
| 字段 | 说明 | 重要性 |
|------|------|--------|
| `element_id`, `element_name` | 逻辑资源ID和名称（小区/基站） | 资源标识 |
| `device_uuid`, `device_name` | 硬件设备ID和名称（RRU/AAU等） | 设备标识 |
| `room_id`, `room_name` | 机房信息 | 位置层级1 |
| `station_id`, `station_name`, `city` | 站点信息和城市 | 位置层级2 |
| `longitude`, `latitude` | 地理坐标 | 空间定位 |
| `net_type` ('2G','4G','5G') | 网络类型 | 技术区分 |
| `element_type` | 元素类型（gsmcell/eutrancell/nrcell/enb/gnb/bts） | 资源类型 |
| `life_cycle_status` | 生命周期状态（现网有业务/退网等） | 业务状态 |
| `station_cuid`, `room_cuid` | 同步ID（RC系统映射） | **跨系统集成关键** |
| `is_virtual_room` ('是','否') | 虚拟机房标识 | 虚拟化资源管理 |
| `tower_add_code` | 铁塔地址编码（聚合多个） | 铁塔关联 |
| `tower_id`, `tower_name` | 铁塔信息 | 铁塔资源 |

#### 5. 常用查询模式（增强版）
```sql
-- 1. 定位查询：通过元素ID查找完整信息（包含同步ID）
SELECT element_id, element_name, device_name, room_name, station_name, 
       station_cuid, room_cuid, longitude, latitude
FROM npas.mv_logic_element_device_room_station 
WHERE element_id = 'ID';

-- 2. 统计查询：按城市和网络类型统计（包含虚拟机房）
-- 注意：统计元素数量必须使用COUNT(DISTINCT element_id)
SELECT city, net_type, is_virtual_room, 
       COUNT(DISTINCT element_id) as element_count,
       COUNT(DISTINCT device_uuid) as device_count
FROM npas.mv_logic_element_device_room_station 
WHERE device_uuid IS NOT NULL
GROUP BY city, net_type, is_virtual_room;

-- 3. 数据质量：检查未关联设备的元素（区分虚拟机房）
SELECT element_id, element_name, net_type, city, station_name, is_virtual_room
FROM npas.mv_logic_element_device_room_station 
WHERE device_uuid IS NULL 
  AND life_cycle_status = '现网有业务'
ORDER BY is_virtual_room, city;

-- 4. 同步ID完整性检查
SELECT city, station_name,
       COUNT(*) as total_records,  -- 总记录数（含重复）
       COUNT(DISTINCT element_id) as distinct_elements,  -- 去重元素数
       SUM(CASE WHEN station_cuid IS NULL THEN 1 ELSE 0 END) as missing_station_cuid,
       SUM(CASE WHEN room_cuid IS NULL THEN 1 ELSE 0 END) as missing_room_cuid
FROM npas.mv_logic_element_device_room_station
WHERE life_cycle_status = '现网有业务'
GROUP BY city, station_name
HAVING SUM(CASE WHEN station_cuid IS NULL OR room_cuid IS NULL THEN 1 ELSE 0 END) > 0;

-- 5. 时间维度分析（年度投入统计）
SELECT EXTRACT(YEAR FROM use_time) as year, net_type, 
       COUNT(DISTINCT element_id) as new_elements
FROM npas.mv_logic_element_device_room_station
WHERE use_time IS NOT NULL
GROUP BY EXTRACT(YEAR FROM use_time), net_type
ORDER BY year DESC;
```

**更多业务场景查询**：包括故障排查、容量规划、网络演进分析、VIP保障、数据质量监控等详细示例，请参见 [query-examples.md#物化视图高级应用查询](query-examples.md#物化视图高级应用查询)。

#### 6. 使用原则（增强版）
1. **优先使用此视图**：对于涉及资源位置、设备关联、系统集成的查询，优先使用此视图
2. **定期刷新**：`REFRESH MATERIALIZED VIEW npas.mv_logic_element_device_room_station;`
3. **索引优化**：在`element_id`, `device_uuid`, `room_id`, `station_id`, `station_cuid`, `room_cuid`上创建索引
4. **数据质量监控**：利用`device_uuid IS NULL`监控未关联设备，利用`station_cuid IS NULL`监控同步问题
5. **跨系统集成**：通过`station_cuid`和`room_cuid`实现与其他系统（如RC）的数据交换
6. **统计去重要求**：同一元素可能因关联多个设备而出现多次，统计元素数量必须使用`COUNT(DISTINCT element_id)`，否则会严重高估实际数量

#### 7. 从MV脚本学到的重要设计模式
- **CTE分层处理**：复杂逻辑分解为`a_1`、`a`、`b`、`project`等CTE，提高可维护性
- **UNION ALL整合**：12个子视图 + 2个CTE通过UNION ALL合并，保持字段结构一致
- **多设备关联导致重复**：同一元素可能因关联多个设备（RRU、天线、室分等）而在不同子视图中出现，导致记录重复
- **聚合字段预计算**：`tower_add_code`使用`string_agg`预聚合，减少查询时计算
- **软删除统一过滤**：所有表关联都包含删除标志过滤，确保数据一致性

**详细文档**：[mv-logic-element-device-room-station.md](mv-logic-element-device-room-station.md)

## Useful SQL Functions

### Get human-readable value from key
```sql
CREATE OR REPLACE FUNCTION get_dim_value(key_value text, dim_table text, value_column text)
RETURNS text AS $$
BEGIN
    EXECUTE format('SELECT %I FROM %I WHERE %I_key = $1', 
                   value_column, dim_table, value_column)
    INTO value_column
    USING key_value;
    RETURN value_column;
END;
$$ LANGUAGE plpgsql;
```

### Format coordinates for GIS
```sql
SELECT station_name, 
       ST_MakePoint(longitude, latitude) as geom,
       CONCAT(latitude, ',', longitude) as lat_lon
FROM wr_space_station
WHERE latitude IS NOT NULL AND longitude IS NOT NULL;
```