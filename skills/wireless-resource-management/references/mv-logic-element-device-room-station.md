# MV视图：mv_logic_element_device_room_station

## 概述

`mv_logic_element_device_room_station` 是一个综合性的物化视图，它将三大类资源信息关联在一起，是日常统计和查询最方便的视图表。

**整合的资源类型：**
1. **逻辑资源**：小区（2G/4G/5G）、基站（ENODEB/GNODEB/BTS）
2. **硬件资源**：RRU、AAU、天线、室分系统（WIDS）、直放站、AP、BBU、DU等
3. **位置资源**：机房、站点、铁塔

## 主要用途

- **快速定位**：通过一个视图查询即可获取元素的完整位置和设备信息
- **统计分析**：便于按网络类型、设备类型、位置等维度进行统计
- **数据质量检查**：检查元素与设备的关联完整性
- **规划信息关联**：包含规划点、解决方案、批次等规划系统信息

## 视图构建原理

该视图通过精心设计的CTE（公共表表达式）和UNION ALL合并多个数据源构建，确保数据完整性：

### 1. 数据源结构
视图由三大部分组成：
- **有设备关联的记录**：来自12个`v_dw_*_room_station`子视图
- **无设备关联的记录**：来自`a`和`b` CTE，确保即使没有设备关联的资源也能出现在视图中
- **补充关联信息**：最终关联机房、站点和同步ID映射表

### 2. 关键CTE设计原理
#### a_1 / a CTE：无设备关联的ENODEB记录
- **目的**：查找`wr_logic_enodeb`中未关联任何设备（BBU、DU、AP）的ENODEB记录
- **逻辑**：
  - 左连接`wr_logic_eutrancell`获取关联的小区信息
  - 左连接`wr_device_bbu`、`wr_device_du`、`wr_device_ap`检查设备关联
  - WHERE条件：`ap.ap_id IS NULL AND bbu.bbu_id IS NULL AND du.du_id IS NULL`
  - 通过`dim_lifecyclestatus`获取生命周期状态（使用`MAX`聚合多个小区的状态）
  - 使用`MIN(eutrancell.use_time)`获取最早的启用时间
- **输出**：保留ENODEB基本信息、机房站点信息、生命周期状态等

#### b CTE：无设备关联的小区记录（2G/4G/5G）
- **目的**：查找各类小区中未关联任何设备（AAU、天线、直放站、RRU、WIDS、AP）的记录
- **逻辑**：
  - 分别处理`wr_logic_nrcell`、`wr_logic_eutrancell`、`wr_logic_gsmcell`
  - 左连接所有可能的设备映射表：`wr_map_aau_cell`、`wr_map_ant_cell`、`wr_map_rru_cell`、`wr_wids_object_rela`等
  - 左连接对应的设备表：`wr_device_aau`、`wr_device_ant`、`wr_device_rru`、`wr_device_wids`等
  - WHERE条件：所有设备ID字段均为NULL
  - 关联对应的基站表获取节点B信息
- **技术特点**：使用`UNION ALL`合并三类小区的查询结果，保持字段结构一致

### 3. 子视图整合（project CTE）
通过`UNION ALL`合并以下12个数据源，每个数据源已预计算特定类型的资源关联链：

| 序号 | 子视图名称 | 关联类型 | 描述 |
|------|------------|----------|------|
| 1 | `v_dw_cell_rru_room_station` | 小区 ↔ RRU | 小区通过RRU关联到机房和站点 |
| 2 | `v_dw_cell_ant_room_station` | 小区 ↔ 天线 | 小区通过天线关联到机房和站点 |
| 3 | `v_dw_cell_aau_room_station` | 小区 ↔ AAU | 小区通过AAU关联到机房和站点 |
| 4 | `v_dw_cell_repeater_room_station` | 小区 ↔ 直放站 | 小区通过直放站关联到机房和站点 |
| 5 | `v_dw_cell_wids_room_station` | 小区 ↔ 室分系统 | 小区通过室分系统关联到机房和站点 |
| 6 | `v_dw_enb_bbu_room_station` | ENODEB ↔ BBU | ENODEB通过BBU关联到机房和站点 |
| 7 | `v_dw_enb_du_room_station` | ENODEB ↔ DU | ENODEB通过DU关联到机房和站点 |
| 8 | `v_dw_gnb_du_room_station` | GNODEB ↔ DU | GNODEB通过DU关联到机房和站点 |
| 9 | `v_dw_bts_room_station` | BTS关联 | BTS直接关联到机房和站点 |
| 10 | `v_dw_cell_ap_room_station` | 小区 ↔ AP | 小区通过AP关联到机房和站点 |
| 11 | `v_dw_enb_ap_room_station` | ENODEB ↔ AP | ENODEB通过AP关联到机房和站点 |
| 12 | `a` CTE结果 | 无设备ENODEB | 补充无设备关联的ENODEB记录 |
| 13 | `b` CTE结果 | 无设备小区 | 补充无设备关联的小区记录 |

### 4. 最终关联与数据增强
主查询将`project` CTE的结果与以下表进行关联和增强：

#### 机房信息关联 (`wr_space_room`)
- 获取机房详细信息：`owner`、`room_type`、`p_room_type`
- 计算虚拟机房标志：`CASE WHEN room.p_room_type = '虚拟机房' THEN '是' ELSE '否' END`
- 过滤已删除记录：`room.is_delete = false`

#### 站点信息关联 (`wr_space_station`)
- 获取站点详细信息：`station_name`、`city`、`longitude`、`latitude`
- 聚合铁塔地址编码：`string_agg(station.tower_add_code, ',')`

#### 同步ID映射关联 (`rc_sync_id_map`)
- **关键集成字段**：提供与其他系统（如资源中心RC）的ID映射
- 通过两个子查询分别获取`station_cuid`和`room_cuid`：
  ```sql
  -- 站点同步ID
  SELECT rc_cuid, wr_cuid FROM npas.rc_sync_id_map WHERE res_type = 'station'
  -- 机房同步ID  
  SELECT rc_cuid, wr_cuid FROM npas.rc_sync_id_map WHERE res_type = 'room'
  ```
- `wr_cuid`匹配`station.station_id`或`room.room_id`，`rc_cuid`为对应RC系统中的ID

### 5. 数据完整性设计特点
1. **软删除处理**：所有关联包含`is_del = false`或`is_delete = false`条件
2. **维度表关联**：通过`dim_lifecyclestatus`获取生命周期状态，使用`curr_flag = true`过滤当前有效值
3. **时间字段处理**：`use_time`（启用时间）、`exit_time`（退网时间）、`setup_time`（安装时间）
4. **规划信息保留**：保留`element_planid`、`device_planid`、`element_solutionid`、`device_solutionid`等规划系统字段
5. **虚拟机房识别**：基于`p_room_type`自动计算`is_virtual_room`标志
6. **铁塔信息聚合**：使用`string_agg`聚合多个铁塔地址编码

## 字段结构

| 字段名 | 类型 | 描述 | 来源 |
|--------|------|------|------|
| `element_id` | VARCHAR | 元素ID（小区ID、基站ID） | 各子视图 |
| `element_name` | VARCHAR | 元素名称（小区名、基站名） | 各子视图 |
| `device_uuid` | VARCHAR | 设备UUID（RRU_ID、AAU_ID等） | 各子视图 |
| `device_name` | VARCHAR | 设备名称 | 各子视图 |
| `room_id` | VARCHAR | 机房ID | 各子视图 |
| `room_name` | VARCHAR | 机房名称 | 各子视图 |
| `station_id` | VARCHAR | 站点ID | 各子视图 |
| `station_name` | VARCHAR | 站点名称 | 各子视图 |
| `city` | VARCHAR | 城市 | 各子视图 |
| `net_type` | VARCHAR | 网络类型（'2G','4G','5G'） | 各子视图 |
| `element_type` | VARCHAR | 元素类型（'gsmcell','eutrancell','nrcell','enb','gnb','bts'） | 各子视图 |
| `device_type` | VARCHAR | 设备类型（NULL - 由device_uuid可推断） | 各子视图 |
| `life_cycle_status` | VARCHAR | 生命周期状态 | `dim_lifecyclestatus` |
| `use_time` | TIMESTAMP | 启用时间 | 元素表 |
| `exit_time` | TIMESTAMP | 退网时间 | 元素表 |
| `nodeb_uuid` | VARCHAR | 基站UUID（ENODEB_ID/GNODEB_ID/SITE_ID） | 各子视图 |
| `nodeb_name` | VARCHAR | 基站名称 | 各子视图 |
| `owner` | VARCHAR | 机房归属方 | `wr_space_room.owner` |
| `is_virtual_room` | VARCHAR | 是否虚拟机房（'是','否'） | 根据`wr_space_room.p_room_type`计算 |
| `tower_add_code` | TEXT | 铁塔地址编码（聚合多个） | `wr_space_station.tower_add_code` |
| `cgi` | VARCHAR | 小区全球标识（仅小区有） | 部分子视图 |
| `nodeb_id` | VARCHAR | 基站ID（冗余字段） | 部分子视图 |
| `station_cuid` | VARCHAR | 站点CUID（同步ID） | `rc_sync_id_map` |
| `room_cuid` | VARCHAR | 机房CUID（同步ID） | `rc_sync_id_map` |
| `element_planid` | VARCHAR | 元素规划ID | 部分子视图 |
| `device_planid` | VARCHAR | 设备规划ID | 部分子视图 |
| `room_type` | VARCHAR | 机房类型 | `wr_space_room.room_type` |
| `longitude` | NUMERIC | 经度 | `wr_space_station.longitude` |
| `latitude` | NUMERIC | 纬度 | `wr_space_station.latitude` |
| `element_solutionid` | VARCHAR | 元素解决方案ID | 部分子视图 |
| `element_batchid` | VARCHAR | 元素批次ID | 部分子视图 |
| `device_solutionid` | VARCHAR | 设备解决方案ID | 部分子视图 |
| `device_batchid` | VARCHAR | 设备批次ID | 部分子视图 |
| `setup_time` | TIMESTAMP | 安装时间 | 部分子视图 |
| `tower_id` | VARCHAR | 铁塔ID | 部分子视图 |
| `tower_name` | VARCHAR | 铁塔名称 | 部分子视图 |

## 元素类型与网络类型对应关系

| 元素类型 (element_type) | 网络类型 (net_type) | 描述 |
|-------------------------|---------------------|------|
| `gsmcell` | `2G` | 2G小区 |
| `eutrancell` | `4G` | 4G小区 |
| `nrcell` | `5G` | 5G小区 |
| `enb` | `4G` | 4G基站（ENODEB） |
| `gnb` | `5G` | 5G基站（GNODEB） |
| `bts` | `2G` | 2G基站（BTS） |

## 设备类型推断

虽然`device_type`字段通常为NULL，但可以通过`device_uuid`前缀推断设备类型：

| device_uuid 前缀 | 设备类型 | 描述 |
|-----------------|----------|------|
| `RRU-` | RRU | 远程射频单元 |
| `AAU-` | AAU | 有源天线单元 |
| `ANT-` | 天线 | 天线 |
| `WIDS-` | 室分系统 | 无线室内分布系统 |
| `BBU-` | BBU | 基带处理单元 |
| `DU-` | DU | 分布式单元 |
| `AP-` | AP | 接入点 |
| `REPEATER-` | 直放站 | 直放站 |

## 常用查询示例

**重要提示**：物化视图通过UNION ALL合并多个数据源，同一元素可能因关联多个设备而出现多次。统计元素数量时**必须使用`COUNT(DISTINCT element_id)`**，否则会严重高估实际数量。统计设备数量时，根据业务需求决定是否使用`COUNT(DISTINCT device_uuid)`。

### 1. 查找小区完整信息
```sql
SELECT * 
FROM npas.mv_logic_element_device_room_station
WHERE element_type IN ('gsmcell', 'eutrancell', 'nrcell')
  AND element_id = '小区ID';
```

### 2. 按城市统计设备数量
```sql
-- 注意：统计元素数量必须去重，统计设备数量可根据需要决定是否去重
SELECT city, net_type, element_type, 
       COUNT(DISTINCT element_id) as element_count,  -- 去重统计元素数量
       COUNT(DISTINCT device_uuid) as device_count   -- 去重统计设备数量
FROM npas.mv_logic_element_device_room_station
WHERE device_uuid IS NOT NULL
GROUP BY city, net_type, element_type
ORDER BY city, net_type;
```

### 3. 查找未关联设备的元素
```sql
SELECT element_id, element_name, net_type, element_type, city, station_name
FROM npas.mv_logic_element_device_room_station
WHERE device_uuid IS NULL
  AND life_cycle_status = '现网有业务'
ORDER BY net_type, city;
```

### 4. 获取机房设备清单
```sql
SELECT room_name, station_name, city,
       COUNT(DISTINCT element_id) as element_count,
       COUNT(DISTINCT device_uuid) as device_count,
       STRING_AGG(DISTINCT net_type, ',') as net_types
FROM npas.mv_logic_element_device_room_station
WHERE room_id = '机房ID'
GROUP BY room_name, station_name, city;
```

### 5. 规划信息查询
```sql
SELECT element_id, element_name, net_type,
       element_planid, device_planid,
       element_solutionid, device_solutionid,
       element_batchid, device_batchid,
       setup_time
FROM npas.mv_logic_element_device_room_station
WHERE element_planid IS NOT NULL
   OR device_planid IS NOT NULL
ORDER BY setup_time DESC;
```

**更多业务场景查询示例**：包括故障排查、容量规划、网络演进分析、VIP保障、数据质量监控、铁塔基础设施分析等详细查询示例，请参见 [query-examples.md#物化视图高级应用查询](../query-examples.md#物化视图高级应用查询)。

## 数据质量检查

### 1. 检查元素-设备关联完整性
```sql
-- 现网有业务但未关联设备的元素
SELECT COUNT(*) as missing_device_count
FROM npas.mv_logic_element_device_room_station
WHERE device_uuid IS NULL
  AND life_cycle_status = '现网有业务'
  AND element_type LIKE '%cell';  -- 只检查小区
```

### 2. 检查位置信息完整性
```sql
-- 缺少坐标信息的记录
SELECT COUNT(*) as missing_coords_count
FROM npas.mv_logic_element_device_room_station
WHERE longitude IS NULL OR latitude IS NULL;
```

### 3. 检查规划信息完整性
```sql
-- 现网有业务但缺少规划信息的记录
SELECT net_type, element_type, COUNT(*) as count
FROM npas.mv_logic_device_room_station
WHERE life_cycle_status = '现网有业务'
  AND element_planid IS NULL
  AND device_planid IS NULL
GROUP BY net_type, element_type;
```

## 性能优化建议

1. **创建索引**：
   ```sql
   CREATE INDEX idx_mv_element_id ON npas.mv_logic_element_device_room_station(element_id);
   CREATE INDEX idx_mv_device_uuid ON npas.mv_logic_element_device_room_station(device_uuid);
   CREATE INDEX idx_mv_room_id ON npas.mv_logic_element_device_room_station(room_id);
   CREATE INDEX idx_mv_station_id ON npas.mv_logic_element_device_room_station(station_id);
   CREATE INDEX idx_mv_net_type ON npas.mv_logic_element_device_room_station(net_type, element_type);
   ```

2. **定期刷新**：该视图是物化视图，需要定期刷新以保持数据最新：
   ```sql
   REFRESH MATERIALIZED VIEW npas.mv_logic_element_device_room_station;
   ```

3. **查询优化**：尽量使用已索引字段进行过滤，避免全表扫描。

## 与其他视图的关系

该视图是多个 `v_dw_*_room_station` 视图的整合，这些子视图本身已经关联了：
- 逻辑元素表（`wr_logic_*`）
- 设备表（`wr_device_*`）
- 映射表（`wr_map_*`）
- 机房表（`wr_space_room`）
- 站点表（`wr_space_station`）

## 关键技术与设计原则

通过对`MV视图脚本.sql`的深入分析，总结出以下重要的技术实现原则和设计模式：

### 1. 数据完整性优先设计
- **无设备关联记录保留**：即使资源没有关联任何物理设备，仍通过`a`和`b` CTE保留在视图中，确保数据完整性
- **软删除统一处理**：所有表关联都包含`is_del = false`或`is_delete = false`条件，避免误用已删除数据
- **维度表当前值过滤**：使用`dim_lifecyclestatus.curr_flag = true`确保获取最新的生命周期状态

### 2. 系统集成关键字段
- **同步ID映射**：`rc_sync_id_map`表提供`station_cuid`和`room_cuid`，是实现跨系统（无线资源系统↔资源中心RC）数据同步的核心机制
- **规划系统关联**：保留`element_planid`、`device_planid`等字段，支持从规划到实施的全程追溯
- **虚拟机房标识**：通过`p_room_type`自动计算`is_virtual_room`，支持虚拟化资源管理

### 3. 性能优化设计
- **物化视图预计算**：复杂关联在视图刷新时预计算，查询时直接使用结果
- **CTE分层处理**：将复杂逻辑分解为`a_1`、`a`、`b`、`project`等CTE，提高可维护性
- **聚合字段预计算**：`tower_add_code`使用`string_agg`预聚合，减少查询时计算开销

### 4. 时间维度管理
- **启用时间**：`use_time` - 资源投入业务使用的时间
- **退网时间**：`exit_time` - 资源退出服务的时间  
- **安装时间**：`setup_time` - 设备物理安装的时间
- **多时间点支持**：不同业务场景使用不同的时间字段，支持精细化的生命周期管理

### 5. 网络技术演进支持
- **2G/4G/5G统一视图**：通过`net_type`和`element_type`区分不同网络技术，但保持统一的查询接口
- **设备类型兼容**：支持RRU（4G）、AAU（5G）、BBU、DU等多种设备类型
- **基站类型统一**：将ENODEB（4G）、GNODEB（5G）、BTS（2G）统一为`nodeb_uuid`和`nodeb_name`

### 6. 实际应用启示
1. **查询优先使用此视图**：对于涉及资源位置、设备关联的查询，优先使用此物化视图而非原始表连接
2. **数据质量监控**：利用`device_uuid IS NULL`条件监控未关联设备的资源
3. **跨系统集成**：通过`station_cuid`和`room_cuid`实现与其他系统的数据交换
4. **虚拟资源管理**：通过`is_virtual_room`标识支持云化、虚拟化资源管理
5. **规划实施跟踪**：利用规划相关字段跟踪资源从规划到部署的全过程

## 使用注意事项

1. **数据时效性**：物化视图需要定期刷新，查询时需注意数据可能不是实时的
2. **NULL值处理**：部分字段可能为NULL，特别是没有关联设备或规划信息的记录
3. **性能考虑**：虽然查询方便，但复杂聚合查询仍可能较慢，建议创建必要索引
4. **字段一致性**：不同来源的记录字段可能不完全一致，需注意NULL值处理
5. **统计去重要求**：物化视图通过UNION ALL合并多个数据源（12个子视图+2个CTE），同一元素可能因关联多个设备而出现多次。**统计元素数量时必须使用`COUNT(DISTINCT element_id)`而非`COUNT(*)`**，否则会严重高估实际数量。例如，一个小区关联RRU、天线、室分系统时，在视图中可能有3条记录。

## 常见使用场景

1. **故障定位**：通过小区ID快速定位到具体设备、机房和站点
2. **容量分析**：分析机房设备密度和站点覆盖情况
3. **规划核查**：检查实际部署与规划的一致性
4. **资源统计**：按区域、网络类型统计资源分布
5. **数据质量监控**：检查关联完整性和数据一致性