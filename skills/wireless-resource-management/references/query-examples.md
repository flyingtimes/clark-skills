# Query Examples

Common SQL queries for wireless resource management.

## Basic Resource Queries

### List all base stations in a city
```sql
SELECT s.site_name, s.address, s.longitude, s.latitude, 
       e.enodeb_id, e.device_type, e.software_version
FROM wr_space_site s
JOIN wr_sync_rc_enodeb e ON s.site_id = e.site_id
WHERE s.city = 'Guangzhou'
  AND e.lifecycle_status = '现网有业务'
ORDER BY s.site_name;
```

### Count cells per base station
```sql
SELECT e.enodeb_id, COUNT(c.cell_id) as cell_count
FROM wr_sync_rc_enodeb e
LEFT JOIN wr_sync_rc_eutrancell c ON e.enodeb_id = c.enodeb_id
WHERE e.lifecycle_status = '现网有业务'
GROUP BY e.enodeb_id
ORDER BY cell_count DESC;
```

### Find sites with missing coordinates
```sql
SELECT site_id, site_name, address
FROM wr_space_site
WHERE longitude IS NULL OR latitude IS NULL
  OR longitude = 0 OR latitude = 0;
```

### List RRUs without associated antennas
```sql
SELECT r.rru_id, r.device_model, r.installation_location
FROM wr_sync_rc_rru r
LEFT JOIN wr_sync_rc_ant a ON r.rru_id = a.rru_id
WHERE a.antenna_id IS NULL
  AND r.lifecycle_status = '现网有业务';
```

## Cell-Centric Association Examples

These examples demonstrate how to query comprehensive cell information by associating multiple tables, based on the "日常用-综合小区工参.sql" script.

### Comprehensive cell parameters across 2G/4G/5G
```sql
-- Basic cell information with station and room associations
SELECT 
  cell.cgi, cell.cell_id, cell.network, cell.cellname,
  cell.omcname, cell.ci, cell.id, cell.tac,
  cell.site_id, cell.logicsite_name,
  dl.life_cycle_status,
  station.station_id, station.station_name,
  room.room_id, room.room_name,
  station.city, station.area,
  station.latitude, station.longitude, station.address,
  db.band, ds.station_type, dc.cover_type, dn.network_type,
  sub.subordinate_area, dg.grid, dg2.grid_road,
  dv.vip_level, cell.use_time, cell.exit_time,
  dd.device_vendor
FROM (
  -- 2G cells
  SELECT cellname, '2G' as network, cell_id,
         concat('460-00-', lac, '-', ci) as cgi,
         lac as tac, ci, omc_cellname as id,
         omc_cellname as omcname, life_cycle_status_key,
         site_id, wdb.sitename as logicsite_name,
         vip_level_key, use_time, exit_time
  FROM npas.wr_logic_gsmcell cell
  LEFT JOIN npas.wr_device_bts wdb ON cell.site_id = wdb.site_id
  WHERE cell.is_del = false
  UNION ALL
  -- 4G cells
  SELECT eutrancell_name as cellname, '4G' as network,
         eutrancell_id as cell_id,
         concat(site.enodebid, '-', cell.ci) as cgi,
         tac, ci, site.enodebid as id,
         cell.omc_cell_name omcname, cell.life_cycle_status_key,
         logic_enodeb_id as site_id, site.enodeb_name as logicsite_name,
         vip_level_key, use_time, exit_time
  FROM npas.wr_logic_eutrancell cell
  LEFT JOIN npas.wr_logic_enodeb site ON cell.logic_enodeb_id = site.enodeb_id
  WHERE cell.is_del = false
  UNION ALL
  -- 5G cells
  SELECT nrcell_name as cellname, '5G' as network,
         nrcell_id as cell_id,
         concat(site.gnodebid, '-', cell.ci) as cgi,
         '' as tac, ci, site.gnodebid as id,
         omc_cell_name omcname, cell.life_cycle_status_key,
         cell.gnodeb_id as site_id, site.gnodeb_name as logicsite_name,
         vip_level_key, use_time, exit_time
  FROM npas.wr_logic_nrcell cell
  LEFT JOIN npas.wr_logic_gnodeb site ON cell.gnodeb_id = site.gnodeb_id
  WHERE cell.is_del = false
) cell
LEFT JOIN npas.wr_space_room room ON room.room_id = (
  -- Get room from associated antenna/AAU/RRU/WIDS
  SELECT a.room_id
  FROM (
    SELECT ant.room_id FROM npas.wr_device_ant ant
    LEFT JOIN npas.wr_map_ant_cell ant_cell ON ant_cell.ant_id = ant.ant_id
    WHERE ant_cell.logic_cell_id = cell.cell_id AND ant_cell.is_del = false
    LIMIT 1
    UNION
    SELECT aau.room_id FROM npas.wr_device_aau aau
    LEFT JOIN npas.wr_map_aau_cell aau_cell ON aau_cell.aau_id = aau.aau_id
    WHERE aau_cell.logic_cell_id = cell.cell_id AND aau_cell.is_del = false
    LIMIT 1
    UNION
    SELECT rru.room_id FROM npas.wr_device_rru rru
    LEFT JOIN npas.wr_map_rru_cell rru_cell ON rru_cell.rru_id = rru.rru_id
    WHERE rru_cell.logic_cell_id = cell.cell_id AND rru_cell.is_del = false
    LIMIT 1
    UNION
    SELECT wids.room_id FROM npas.wr_device_wids wids
    LEFT JOIN npas.wr_map_wids_cell wids_cell ON wids_cell.wids_id = wids.wids_id
    WHERE wids_cell.logic_cell_id = cell.cell_id AND wids_cell.is_del = false
    LIMIT 1
  ) a
  LIMIT 1
)
LEFT JOIN npas.wr_space_station station ON room.station_id = station.station_id
LEFT JOIN npas.pl_cover_point pcp ON pcp.site_planning_id = (
  -- Get planning information
  SELECT site_planning_id FROM npas.ac_access_solution aas
  LEFT JOIN npas.ac_access_batch aab ON aab.access_solution_id = aas.access_solution_id
  LEFT JOIN npas.ac_access_batch_rel_rs aabrr ON aabrr.access_batch_id = aab.access_batch_id
  WHERE cell.cell_id::text = aabrr.rs_cuid::text
  LIMIT 1
)
-- Dimension table joins for decoded values
LEFT JOIN npas.dim_band db ON pcp.band_key = db.band_key
LEFT JOIN npas.dim_lifecyclestatus dl ON cell.life_cycle_status_key = dl.life_cycle_status_key
LEFT JOIN npas.dim_stationtype ds ON pcp.station_type_key = ds.station_type_key
LEFT JOIN npas.dim_covtype dc ON pcp.cover_type_key = dc.cover_type_key
LEFT JOIN npas.dim_networktype dn ON pcp.network_type_key = dn.network_type_key
LEFT JOIN npas.meta_localinfo ml ON ml.site_planning_id = pcp.site_planning_id
LEFT JOIN npas.dim_subarea sub ON ml.subordinate_area_key = sub.subordinate_area_key
LEFT JOIN npas.dim_grid dg ON dg.grid_key = ml.grid_key
LEFT JOIN npas.dim_gridroad dg2 ON dg2.grid_road_key = ml.grid_road_key
LEFT JOIN npas.dim_viplevel dv ON cell.vip_level_key = dv.vip_level_key
LEFT JOIN npas.dim_devicevendor dd ON dd.device_vendor_key = pcp.device_vendor_key;
```

### Using dimension tables for value decoding
Dimension tables (`dim_*`) provide human-readable values for coded keys. Example:
```sql
-- Join dimension tables to decode keys
SELECT 
  cell.cell_id, cell.cellname,
  dl.life_cycle_status,  -- Decoded from life_cycle_status_key
  dv.vip_level,          -- Decoded from vip_level_key
  db.band,               -- Decoded from band_key
  ds.station_type        -- Decoded from station_type_key
FROM npas.wr_logic_eutrancell cell
LEFT JOIN npas.dim_lifecyclestatus dl ON cell.life_cycle_status_key = dl.life_cycle_status_key
LEFT JOIN npas.dim_viplevel dv ON cell.vip_level_key = dv.vip_level_key
LEFT JOIN npas.pl_cover_point pcp ON pcp.site_planning_id = (
  SELECT site_planning_id FROM npas.ac_access_solution aas
  LEFT JOIN npas.ac_access_batch aab ON aab.access_solution_id = aas.access_solution_id
  LEFT JOIN npas.ac_access_batch_rel_rs aabrr ON aabrr.access_batch_id = aab.access_batch_id
  WHERE cell.cell_id::text = aabrr.rs_cuid::text LIMIT 1
)
LEFT JOIN npas.dim_band db ON pcp.band_key = db.band_key
LEFT JOIN npas.dim_stationtype ds ON pcp.station_type_key = ds.station_type_key;
```

## Planning Point Association Examples

Based on the planning point association system, these examples demonstrate how to retrieve planning information for wireless resources through the access solution chain.

### Find planning information for a cell
```sql
-- Get planning point information for a specific cell
SELECT 
  cell.cell_id,
  cell.cellname,
  pcp.site_planning_name,
  pcp.site_planning_code,
  db.band,
  ds.station_type,
  dc.cover_type,
  dn.network_type,
  pcp.longitude as planned_longitude,
  pcp.latitude as planned_latitude,
  pcp.address as planned_address
FROM npas.wr_logic_eutrancell cell
LEFT JOIN npas.ac_access_batch_rel_rs aabrr ON cell.cell_id::text = aabrr.rs_cuid::text
LEFT JOIN npas.ac_access_batch aab ON aabrr.access_batch_id = aab.access_batch_id
LEFT JOIN npas.ac_access_solution aas ON aab.access_solution_id = aas.access_solution_id
LEFT JOIN npas.pl_cover_point pcp ON aas.site_planning_id = pcp.site_planning_id
LEFT JOIN npas.dim_band db ON pcp.band_key = db.band_key
LEFT JOIN npas.dim_stationtype ds ON pcp.station_type_key = ds.station_type_key
LEFT JOIN npas.dim_covtype dc ON pcp.cover_type_key = dc.cover_type_key
LEFT JOIN npas.dim_networktype dn ON pcp.network_type_key = dn.network_type_key
WHERE cell.cell_id = :cell_id
  AND cell.is_del = false;
```

### Compare planned vs. actual coordinates
```sql
-- Compare planning coordinates with actual deployment coordinates
SELECT 
  cell.cell_id,
  cell.cellname,
  pcp.site_planning_name,
  -- Planned coordinates
  pcp.longitude as planned_longitude,
  pcp.latitude as planned_latitude,
  pcp.address as planned_address,
  -- Actual coordinates (via device associations)
  station.longitude as actual_longitude,
  station.latitude as actual_latitude,
  station.address as actual_address,
  -- Calculate distance difference (simplified)
  ROUND(SQRT(POW(pcp.longitude - station.longitude, 2) + 
             POW(pcp.latitude - station.latitude, 2)) * 111, 2) as distance_km
FROM npas.wr_logic_eutrancell cell
LEFT JOIN npas.ac_access_batch_rel_rs aabrr ON cell.cell_id::text = aabrr.rs_cuid::text
LEFT JOIN npas.ac_access_batch aab ON aabrr.access_batch_id = aab.access_batch_id
LEFT JOIN npas.ac_access_solution aas ON aab.access_solution_id = aas.access_solution_id
LEFT JOIN npas.pl_cover_point pcp ON aas.site_planning_id = pcp.site_planning_id
LEFT JOIN (
  -- Get actual location through device associations
  SELECT DISTINCT ON (cell_id) cell_id, station.longitude, station.latitude, station.address
  FROM (
    SELECT logic_cell_id as cell_id, rru.room_id
    FROM npas.wr_map_rru_cell rc
    JOIN npas.wr_device_rru rru ON rc.rru_id = rru.rru_id
    WHERE rc.is_del = false AND rru.is_del = false
    UNION
    SELECT logic_cell_id as cell_id, aau.room_id
    FROM npas.wr_map_aau_cell ac
    JOIN npas.wr_device_aau aau ON ac.aau_id = aau.aau_id
    WHERE ac.is_del = false AND aau.is_del = false
  ) device
  JOIN npas.wr_space_room room ON device.room_id = room.room_id
  JOIN npas.wr_space_station station ON room.station_id = station.station_id
) actual ON actual.cell_id = cell.cell_id
WHERE cell.is_del = false
  AND pcp.longitude IS NOT NULL AND pcp.latitude IS NOT NULL
  AND station.longitude IS NOT NULL AND station.latitude IS NOT NULL
LIMIT 10;
```

### List all resources from a specific planning point
```sql
-- Find all wireless resources associated with a planning point
SELECT 
  pcp.site_planning_name,
  pcp.site_planning_code,
  'Cell' as resource_type,
  cell.cell_id,
  cell.cellname
FROM npas.pl_cover_point pcp
JOIN npas.ac_access_solution aas ON pcp.site_planning_id = aas.site_planning_id
JOIN npas.ac_access_batch aab ON aas.access_solution_id = aab.access_solution_id
JOIN npas.ac_access_batch_rel_rs aabrr ON aab.access_batch_id = aabrr.access_batch_id
JOIN npas.wr_logic_eutrancell cell ON cell.cell_id::text = aabrr.rs_cuid::text
WHERE pcp.site_planning_id = :planning_id
  AND cell.is_del = false

UNION ALL

SELECT 
  pcp.site_planning_name,
  pcp.site_planning_code,
  'ENODEB' as resource_type,
  e.enodeb_id,
  e.enodeb_name
FROM npas.pl_cover_point pcp
JOIN npas.ac_access_solution aas ON pcp.site_planning_id = aas.site_planning_id
JOIN npas.ac_access_batch aab ON aas.access_solution_id = aab.access_solution_id
JOIN npas.ac_access_batch_rel_rs aabrr ON aab.access_batch_id = aabrr.access_batch_id
JOIN npas.wr_logic_enodeb e ON e.enodeb_id::text = aabrr.rs_cuid::text
WHERE pcp.site_planning_id = :planning_id
  AND e.is_del = false

ORDER BY resource_type, cell_id;
```

### Find planning metadata for comprehensive cell query
```sql
-- Integration with comprehensive cell parameters query
-- This shows how planning point joins fit into complete cell information queries
SELECT 
  cell.cell_id,
  cell.cellname,
  -- Planning information
  pcp.site_planning_name,
  db.band,
  ds.station_type,
  dc.cover_type,
  dn.network_type,
  -- Location information
  station.station_name,
  station.city,
  station.latitude,
  station.longitude
FROM npas.wr_logic_eutrancell cell
-- Planning point association
LEFT JOIN npas.ac_access_batch_rel_rs aabrr ON cell.cell_id::text = aabrr.rs_cuid::text
LEFT JOIN npas.ac_access_batch aab ON aabrr.access_batch_id = aab.access_batch_id
LEFT JOIN npas.ac_access_solution aas ON aab.access_solution_id = aas.access_solution_id
LEFT JOIN npas.pl_cover_point pcp ON aas.site_planning_id = pcp.site_planning_id
-- Dimension tables for planning metadata
LEFT JOIN npas.dim_band db ON pcp.band_key = db.band_key
LEFT JOIN npas.dim_stationtype ds ON pcp.station_type_key = ds.station_type_key
LEFT JOIN npas.dim_covtype dc ON pcp.cover_type_key = dc.covtype_key
LEFT JOIN npas.dim_networktype dn ON pcp.network_type_key = dn.network_type_key
-- Physical location association
LEFT JOIN (
  SELECT logic_cell_id, rru.room_id
  FROM npas.wr_map_rru_cell rc
  JOIN npas.wr_device_rru rru ON rc.rru_id = rru.rru_id
  WHERE rc.is_del = false AND rru.is_del = false
  LIMIT 1
) device ON device.logic_cell_id = cell.cell_id
LEFT JOIN npas.wr_space_room room ON room.room_id = device.room_id
LEFT JOIN npas.wr_space_station station ON room.station_id = station.station_id
WHERE cell.is_del = false
LIMIT 10;
```

## Room-Level Summary Examples

Based on the "给韵姐_机房汇总表.sql" script, these examples show how to generate room-level summaries with device counts and associations.

### Room summary with device counts
```sql
-- Basic room information with device counts
SELECT 
  room.room_name, site.station_name, site.city, site.area,
  room.towerroom_type, room.s_ownership_id, room.owner,
  room.alldevice_power, room.air_conditioner_power,
  site.m_type, room.p_room_type, room.category,
  room.room_type, room.status,
  -- Device counts (in-service)
  bbu.bbu_count, du.du_count, aau.aau_count, rru.rru_count,
  -- Device counts (out-of-service)
  gc_bbu.bbu_count as gc_bbu_count,
  gc_du.du_count as gc_du_count,
  gc_aau.aau_count as gc_aau_count,
  gc_rru.rru_count as gc_rru_count
FROM npas.wr_space_room room
LEFT JOIN npas.wr_space_station site ON room.station_id = site.station_id
LEFT JOIN (
  SELECT room_id, COUNT(1) as bbu_count
  FROM npas.v_dw_bbu WHERE status = '现网有业务'
  GROUP BY room_id
) bbu ON bbu.room_id = room.room_id
LEFT JOIN (
  SELECT room_id, COUNT(1) as bbu_count
  FROM npas.v_dw_bbu WHERE status LIKE '%退网%'
  GROUP BY room_id
) gc_bbu ON gc_bbu.room_id = room.room_id
LEFT JOIN (
  SELECT related_room_cuid as room_id, COUNT(1) as du_count
  FROM npas.v_dw_du WHERE status = '现网有业务'
  GROUP BY related_room_cuid
) du ON du.room_id = room.room_id
LEFT JOIN (
  SELECT related_room_cuid as room_id, COUNT(1) as du_count
  FROM npas.v_dw_du WHERE status LIKE '%退网%'
  GROUP BY related_room_cuid
) gc_du ON gc_du.room_id = room.room_id
LEFT JOIN (
  SELECT aau.room_id, COUNT(DISTINCT aau.aau_id) as aau_count
  FROM npas.wr_device_aau aau
  LEFT JOIN dim_lifecyclestatus dl ON aau.life_cycle_status_key = dl.life_cycle_status_key
  WHERE dl.life_cycle_status = '现网有业务' AND aau.is_del = false
  GROUP BY aau.room_id
) aau ON aau.room_id = room.room_id
LEFT JOIN (
  SELECT aau.room_id, COUNT(DISTINCT aau.aau_id) as aau_count
  FROM npas.wr_device_aau aau
  LEFT JOIN dim_lifecyclestatus dl ON aau.life_cycle_status_key = dl.life_cycle_status_key
  WHERE dl.life_cycle_status LIKE '%退网%' AND aau.is_del = false
  GROUP BY aau.room_id
) gc_aau ON gc_aau.room_id = room.room_id;
```

### Room with CRAN remote site counts
```sql
-- Count remote sites (CRAN) associated with rooms
SELECT 
  room.room_name,
  COUNT(DISTINCT CASE WHEN cran.station_type = '宏站' THEN cran.remote_station END) as macro_remote_count,
  COUNT(DISTINCT CASE WHEN cran.station_type = '室分' THEN cran.remote_station END) as indoor_remote_count,
  COUNT(DISTINCT CASE WHEN cran.station_type = '微小区' THEN cran.remote_station END) as micro_remote_count
FROM npas.wr_space_room room
LEFT JOIN temp.cran_table cran ON cran.bbu_room = room.room_name
GROUP BY room.room_name;
```

## Location Query Patterns for Distributed Architecture

Based on the distributed deployment model, these queries demonstrate how to find location information for logical elements through physical device associations.

### Find cell location through device associations
```sql
-- Get cell location by tracing through RRU/AAU associations
SELECT 
  cell.cell_id,
  cell.cellname,
  cell.network,
  device.device_type,
  device.device_id,
  room.room_name,
  station.station_name,
  station.city,
  station.area,
  station.latitude,
  station.longitude,
  station.address
FROM (
  -- 4G cell
  SELECT eutrancell_id as cell_id, eutrancell_name as cellname, '4G' as network
  FROM npas.wr_logic_eutrancell WHERE eutrancell_id = :cell_id AND is_del = false
  UNION ALL
  -- 5G cell  
  SELECT nrcell_id as cell_id, nrcell_name as cellname, '5G' as network
  FROM npas.wr_logic_nrcell WHERE nrcell_id = :cell_id AND is_del = false
) cell
CROSS JOIN LATERAL (
  -- Try to find associated device in priority order
  SELECT 'RRU' as device_type, rru.rru_id as device_id, rru.room_id
  FROM npas.wr_map_rru_cell rc
  JOIN npas.wr_device_rru rru ON rc.rru_id = rru.rru_id
  WHERE rc.logic_cell_id = cell.cell_id AND rc.is_del = false AND rru.is_del = false
  LIMIT 1
  
  UNION ALL
  
  SELECT 'AAU' as device_type, aau.aau_id as device_id, aau.room_id
  FROM npas.wr_map_aau_cell ac
  JOIN npas.wr_device_aau aau ON ac.aau_id = aau.aau_id
  WHERE ac.logic_cell_id = cell.cell_id AND ac.is_del = false AND aau.is_del = false
  LIMIT 1
  
  UNION ALL
  
  SELECT 'Antenna' as device_type, ant.ant_id as device_id, ant.room_id
  FROM npas.wr_map_ant_cell antc
  JOIN npas.wr_device_ant ant ON antc.ant_id = ant.ant_id
  WHERE antc.logic_cell_id = cell.cell_id AND antc.is_del = false AND ant.is_del = false
  LIMIT 1
  
  UNION ALL
  
  SELECT 'WIDS' as device_type, wids.wids_id as device_id, wids.room_id
  FROM npas.wr_map_wids_cell wc
  JOIN npas.wr_device_wids wids ON wc.wids_id = wids.wids_id
  WHERE wc.logic_cell_id = cell.cell_id AND wc.is_del = false AND wids.is_del = false
  LIMIT 1
) device
LEFT JOIN npas.wr_space_room room ON room.room_id = device.room_id
LEFT JOIN npas.wr_space_station station ON room.station_id = station.station_id;
```

### Find base station (ENODEB/GNODEB) location through BBU/DU associations
```sql
-- ENODEB location through BBU association
SELECT 
  e.enodeb_id,
  e.enodeb_name,
  bbu.bbu_id,
  room.room_name,
  station.station_name,
  station.city,
  station.latitude,
  station.longitude
FROM npas.wr_logic_enodeb e
JOIN npas.wr_device_bbu bbu ON e.bbu_id = bbu.bbu_id
JOIN npas.wr_space_room room ON bbu.room_id = room.room_id
JOIN npas.wr_space_station station ON room.station_id = station.station_id
WHERE e.enodeb_id = :enodeb_id AND e.is_del = false AND bbu.is_del = false;

-- GNODEB location through DU association
SELECT 
  g.gnodeb_id,
  g.gnodeb_name,
  du.du_id,
  room.room_name,
  station.station_name,
  station.city,
  station.latitude,
  station.longitude
FROM npas.wr_logic_gnodeb g
JOIN npas.v_dw_du du ON g.related_du_cuid = du.cuid::uuid
JOIN npas.wr_space_room room ON du.related_room_cuid = room.room_id
JOIN npas.wr_space_station station ON room.station_id = station.station_id
WHERE g.gnodeb_id = :gnodeb_id AND g.is_del = false;
```

### Find all cells served by a specific room (CRAN scenario)
```sql
-- Cells served by BBUs in a specific room
SELECT DISTINCT
  cell.cell_id,
  cell.cellname,
  cell.network,
  'BBU' as source_type,
  bbu.bbu_id
FROM npas.wr_space_room room
JOIN npas.wr_device_bbu bbu ON room.room_id = bbu.room_id
JOIN npas.wr_logic_enodeb e ON bbu.bbu_id = e.bbu_id
JOIN npas.wr_logic_eutrancell cell ON e.enodeb_id = cell.logic_enodeb_id
WHERE room.room_id = :room_id AND bbu.is_del = false AND e.is_del = false AND cell.is_del = false
UNION ALL
-- Cells served by DUs in a specific room
SELECT DISTINCT
  cell.cell_id,
  cell.nrcell_name as cellname,
  '5G' as network,
  'DU' as source_type,
  du.cuid as device_id
FROM npas.wr_space_room room
JOIN npas.v_dw_du du ON room.room_id = du.related_room_cuid
JOIN npas.wr_logic_gnodeb g ON du.cuid::uuid = g.related_du_cuid
JOIN npas.wr_logic_nrcell cell ON g.gnodeb_id = cell.gnodeb_id
WHERE room.room_id = :room_id AND g.is_del = false AND cell.is_del = false;
```

## Data Quality Check Queries

### Find mandatory field violations
```sql
-- AAU without installation location
SELECT aau_id, device_model
FROM wr_sync_rc_aau
WHERE installation_location IS NULL 
  OR installation_location = ''
  AND lifecycle_status = '现网有业务';
```

### Identify invalid coordinate ranges
```sql
SELECT site_id, site_name, longitude, latitude
FROM wr_space_site
WHERE longitude < 73 OR longitude > 135
   OR latitude < 3 OR latitude > 54;
```

### Check relationship consistency
```sql
-- Cells referencing non-existent base stations
SELECT c.cell_id, c.enodeb_id
FROM wr_sync_rc_eutrancell c
LEFT JOIN wr_sync_rc_enodeb e ON c.enodeb_id = e.enodeb_id
WHERE e.enodeb_id IS NULL;
```

## Statistical Queries

### Count resources by type
```sql
SELECT 'Base Station' as resource_type, COUNT(*) as count
FROM wr_sync_rc_enodeb
WHERE lifecycle_status = '现网有业务'
UNION ALL
SELECT 'Cell', COUNT(*)
FROM wr_sync_rc_eutrancell
WHERE lifecycle_status = '现网有业务'
UNION ALL
SELECT 'RRU', COUNT(*)
FROM wr_sync_rc_rru
WHERE lifecycle_status = '现网有业务'
UNION ALL
SELECT 'Antenna', COUNT(*)
FROM wr_sync_rc_ant
WHERE lifecycle_status = '现网有业务';
```

### Maintenance type distribution
```sql
SELECT maintenance_type, COUNT(*) as site_count
FROM wr_space_site
WHERE maintenance_type IS NOT NULL
GROUP BY maintenance_type
ORDER BY site_count DESC;
```

### VIP level distribution
```sql
SELECT vip_level, COUNT(*) as site_count
FROM wr_space_site
GROUP BY vip_level
ORDER BY 
  CASE vip_level
    WHEN 'VVIP' THEN 1
    WHEN 'VIP' THEN 2
    WHEN '一般' THEN 3
    ELSE 4
  END;
```

## Planning vs Actual Comparison

### Planned vs deployed cells
```sql
SELECT p.city, 
       COUNT(DISTINCT p.cell_id) as planned_cells,
       COUNT(DISTINCT a.cell_id) as actual_cells,
       COUNT(DISTINCT p.cell_id) - COUNT(DISTINCT a.cell_id) as difference
FROM pl_cell p
LEFT JOIN wr_sync_rc_eutrancell a ON p.cell_id = a.cell_id
GROUP BY p.city
ORDER BY difference DESC;
```

### Sites with pending modifications
```sql
SELECT s.site_id, s.site_name, s.maintenance_type,
       COUNT(m.modification_id) as pending_changes
FROM wr_space_site s
JOIN wr_modification_queue m ON s.site_id = m.site_id
WHERE m.status = 'pending'
GROUP BY s.site_id, s.site_name, s.maintenance_type
HAVING COUNT(m.modification_id) > 0;
```

## Hardware Inventory Queries

### Device counts by model
```sql
SELECT device_model, device_vendor, COUNT(*) as quantity
FROM wr_device
WHERE lifecycle_status = '现网有业务'
GROUP BY device_model, device_vendor
ORDER BY quantity DESC;
```

### Age analysis of equipment
```sql
SELECT 
  CASE 
    WHEN installation_date >= CURRENT_DATE - INTERVAL '1 year' THEN '0-1 year'
    WHEN installation_date >= CURRENT_DATE - INTERVAL '3 years' THEN '1-3 years'
    WHEN installation_date >= CURRENT_DATE - INTERVAL '5 years' THEN '3-5 years'
    ELSE '>5 years'
  END as age_range,
  COUNT(*) as device_count
FROM wr_device
WHERE installation_date IS NOT NULL
GROUP BY age_range
ORDER BY MIN(installation_date);
```

## Performance Optimization

### Large tables analysis
```sql
SELECT table_name, 
       pg_size_pretty(pg_total_relation_size('"' || table_name || '"')) as total_size,
       pg_size_pretty(pg_relation_size('"' || table_name || '"')) as table_size,
       pg_size_pretty(pg_total_relation_size('"' || table_name || '"') - 
                     pg_relation_size('"' || table_name || '"')) as index_size
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_type = 'BASE TABLE'
ORDER BY pg_total_relation_size('"' || table_name || '"') DESC
LIMIT 20;
```

## Export Queries

### Export site data for GIS
```sql
COPY (
  SELECT site_id, site_name, longitude, latitude, address, 
         maintenance_type, vip_level, city, district
  FROM wr_space_site
  WHERE longitude IS NOT NULL AND latitude IS NOT NULL
) TO '/tmp/sites_export.csv' WITH CSV HEADER;
```

### Generate data quality report
```sql
SELECT 
  'Missing Coordinates' as issue_type,
  COUNT(*) as issue_count
FROM wr_space_site
WHERE longitude IS NULL OR latitude IS NULL
UNION ALL
SELECT 
  'Invalid Relationships',
  COUNT(*)
FROM wr_sync_rc_eutrancell c
LEFT JOIN wr_sync_rc_enodeb e ON c.enodeb_id = e.enodeb_id
WHERE e.enodeb_id IS NULL
UNION ALL
SELECT 
  'Mandatory Field Missing',
  COUNT(*)
FROM wr_sync_rc_aau
WHERE installation_location IS NULL 
  AND lifecycle_status = '现网有业务';
```

## Materialized View Queries

基于 `mv_logic_element_device_room_station` 物化视图的查询示例。该视图整合了逻辑资源、硬件资源和位置资源，是日常查询最方便的数据源。

### 基本查询
```sql
-- 1. 查找小区完整信息
SELECT element_id, element_name, device_uuid, device_name,
       room_name, station_name, city, longitude, latitude,
       net_type, element_type, life_cycle_status
FROM npas.mv_logic_element_device_room_station
WHERE element_type IN ('gsmcell', 'eutrancell', 'nrcell')
  AND element_id = '小区ID';

-- 2. 按城市统计各网络类型设备数量
SELECT city, net_type, element_type, 
       COUNT(DISTINCT element_id) as element_count,
       COUNT(DISTINCT device_uuid) as device_count
FROM npas.mv_logic_element_device_room_station
WHERE device_uuid IS NOT NULL
GROUP BY city, net_type, element_type
ORDER BY city, net_type;

-- 3. 查找未关联设备的元素（数据质量检查）
SELECT element_id, element_name, net_type, element_type,
       city, station_name, life_cycle_status
FROM npas.mv_logic_element_device_room_station
WHERE device_uuid IS NULL
  AND life_cycle_status = '现网有业务'
ORDER BY net_type, city;

-- 4. 获取机房设备清单
SELECT room_name, station_name, city,
       COUNT(DISTINCT element_id) as element_count,
       COUNT(DISTINCT device_uuid) as device_count,
       STRING_AGG(DISTINCT net_type, ',') as net_types,
       STRING_AGG(DISTINCT element_type, ',') as element_types
FROM npas.mv_logic_element_device_room_station
WHERE room_id = '机房ID'
GROUP BY room_name, station_name, city;

-- 5. 规划信息查询
SELECT element_id, element_name, net_type, element_type,
       element_planid, device_planid,
       element_solutionid, device_solutionid,
       element_batchid, device_batchid,
       setup_time
FROM npas.mv_logic_element_device_room_station
WHERE element_planid IS NOT NULL
   OR device_planid IS NOT NULL
ORDER BY setup_time DESC;
```

### 高级分析查询
```sql
-- 1. 网络类型分布统计
SELECT net_type, element_type,
       COUNT(DISTINCT element_id) as element_count,
       COUNT(DISTINCT device_uuid) as device_count,
       COUNT(DISTINCT room_id) as room_count,
       COUNT(DISTINCT station_id) as station_count
FROM npas.mv_logic_element_device_room_station
WHERE life_cycle_status = '现网有业务'
GROUP BY net_type, element_type
ORDER BY net_type, element_type;

-- 2. 虚拟机房资源统计
SELECT city, room_name, station_name,
       COUNT(DISTINCT element_id) as element_count,
       COUNT(DISTINCT device_uuid) as device_count,
       is_virtual_room
FROM npas.mv_logic_element_device_room_station
WHERE room_id IS NOT NULL
GROUP BY city, room_name, station_name, is_virtual_room
HAVING COUNT(DISTINCT element_id) > 0
ORDER BY city, element_count DESC;

-- 3. 生命周期状态分析
SELECT life_cycle_status, net_type,
       COUNT(DISTINCT element_id) as element_count,
       COUNT(DISTINCT device_uuid) as device_count
FROM npas.mv_logic_element_device_room_station
GROUP BY life_cycle_status, net_type
ORDER BY life_cycle_status, net_type;

-- 4. 坐标完整性检查
SELECT city, station_name,
       COUNT(*) as total_records,
       SUM(CASE WHEN longitude IS NULL OR latitude IS NULL THEN 1 ELSE 0 END) as missing_coords
FROM npas.mv_logic_element_device_room_station
GROUP BY city, station_name
HAVING SUM(CASE WHEN longitude IS NULL OR latitude IS NULL THEN 1 ELSE 0 END) > 0
ORDER BY missing_coords DESC;

-- 5. 同步ID映射分析（跨系统集成）
SELECT city, station_name,
       COUNT(*) as total_records,
       SUM(CASE WHEN station_cuid IS NOT NULL THEN 1 ELSE 0 END) as has_station_cuid,
       SUM(CASE WHEN room_cuid IS NOT NULL THEN 1 ELSE 0 END) as has_room_cuid,
       SUM(CASE WHEN station_cuid IS NULL AND room_cuid IS NULL THEN 1 ELSE 0 END) as missing_all_cuid
FROM npas.mv_logic_element_device_room_station
WHERE life_cycle_status = '现网有业务'
GROUP BY city, station_name
ORDER BY missing_all_cuid DESC, city;

-- 6. 时间维度分析（启用/退网时间）
SELECT 
  EXTRACT(YEAR FROM use_time) as use_year,
  EXTRACT(YEAR FROM exit_time) as exit_year,
  net_type,
  COUNT(DISTINCT element_id) as element_count
FROM npas.mv_logic_element_device_room_station
WHERE use_time IS NOT NULL
GROUP BY EXTRACT(YEAR FROM use_time), EXTRACT(YEAR FROM exit_time), net_type
ORDER BY use_year DESC, exit_year, net_type;

-- 7. 设备关联完整性深度分析
SELECT 
  net_type, element_type,
  COUNT(*) as total_records,
  SUM(CASE WHEN device_uuid IS NULL THEN 1 ELSE 0 END) as no_device_count,
  ROUND(100.0 * SUM(CASE WHEN device_uuid IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) as no_device_percent,
  -- 按生命周期状态细分
  SUM(CASE WHEN device_uuid IS NULL AND life_cycle_status = '现网有业务' THEN 1 ELSE 0 END) as active_no_device,
  SUM(CASE WHEN device_uuid IS NULL AND life_cycle_status LIKE '%退网%' THEN 1 ELSE 0 END) as decommissioned_no_device
FROM npas.mv_logic_element_device_room_station
GROUP BY net_type, element_type
ORDER BY no_device_percent DESC;

-- 8. 规划信息完整性分析
SELECT 
  net_type, element_type,
  COUNT(*) as total_records,
  SUM(CASE WHEN element_planid IS NOT NULL OR device_planid IS NOT NULL THEN 1 ELSE 0 END) as has_planning_info,
  SUM(CASE WHEN element_solutionid IS NOT NULL OR device_solutionid IS NOT NULL THEN 1 ELSE 0 END) as has_solution_info,
  SUM(CASE WHEN element_batchid IS NOT NULL OR device_batchid IS NOT NULL THEN 1 ELSE 0 END) as has_batch_info
FROM npas.mv_logic_element_device_room_station
WHERE life_cycle_status = '现网有业务'
GROUP BY net_type, element_type
ORDER BY net_type, element_type;

-- 9. 机房类型与设备密度分析
SELECT 
  room_type, is_virtual_room,
  COUNT(DISTINCT room_id) as room_count,
  COUNT(DISTINCT station_id) as station_count,
  COUNT(DISTINCT element_id) as element_count,
  COUNT(DISTINCT device_uuid) as device_count,
  ROUND(1.0 * COUNT(DISTINCT device_uuid) / COUNT(DISTINCT room_id), 2) as devices_per_room
FROM npas.mv_logic_element_device_room_station
WHERE room_id IS NOT NULL
GROUP BY room_type, is_virtual_room
ORDER BY devices_per_room DESC;

-- 10. 铁塔信息聚合分析
SELECT 
  city, station_name,
  COUNT(DISTINCT tower_id) as tower_count,
  STRING_AGG(DISTINCT tower_name, '; ') as tower_names,
  STRING_AGG(DISTINCT tower_add_code, '; ') as tower_codes
FROM npas.mv_logic_element_device_room_station
WHERE tower_id IS NOT NULL
GROUP BY city, station_name
HAVING COUNT(DISTINCT tower_id) > 1  -- 仅显示多个铁塔的站点
ORDER BY tower_count DESC, city;
```

### 查询模板
```sql
-- 模板1：资源定位查询
SELECT [字段列表]
FROM npas.mv_logic_element_device_room_station
WHERE [元素ID/设备ID/机房ID/站点ID] = '[ID值]';

-- 模板2：分组统计查询
-- 注意：统计元素数量必须使用COUNT(DISTINCT element_id)
SELECT [分组字段], 
       COUNT(DISTINCT element_id) as 元素数量,
       COUNT(DISTINCT device_uuid) as 设备数量,
       [聚合函数] as 指标
FROM npas.mv_logic_element_device_room_station
WHERE [过滤条件]
GROUP BY [分组字段]
ORDER BY [排序字段];

-- 模板3：数据质量检查
SELECT [检查维度], 
       COUNT(DISTINCT element_id) as 问题元素数量,
       COUNT(*) as 问题记录数量
FROM npas.mv_logic_element_device_room_station
WHERE [问题条件]
GROUP BY [检查维度]
ORDER BY 问题元素数量 DESC;
```

### 使用建议
1. **性能优化**：在 `element_id`, `device_uuid`, `room_id`, `station_id` 等常用过滤字段上创建索引。
2. **数据时效性**：物化视图需要定期刷新，使用 `REFRESH MATERIALIZED VIEW npas.mv_logic_element_device_room_station;` 更新数据。
3. **字段说明**：详细字段说明参见 [mv-logic-element-device-room-station.md](mv-logic-element-device-room-station.md)。
4. **优先使用**：对于需要关联多种资源类型的查询，优先使用此视图而非复杂多表连接。

## 物化视图高级应用查询

基于 `mv_logic_element_device_room_station` 视图的更多实用业务场景查询示例。

**重要统计原则**：物化视图通过UNION ALL合并多个数据源，同一元素可能因关联多个设备而出现多次。统计元素数量时**必须使用`COUNT(DISTINCT element_id)`**，否则会严重高估实际数量。以下示例已根据此原则优化。

### 1. 故障排查与应急响应
```sql
-- 1.1 根据小区CGI快速定位物理位置和设备信息（故障定位）
SELECT element_id, element_name, cgi, net_type, device_uuid, device_name,
       room_name, station_name, city, longitude, latitude, address,
       life_cycle_status, use_time, nodeb_name
FROM npas.mv_logic_element_device_room_station
WHERE cgi = '460-00-1234-56789'  -- 替换为实际CGI
   OR element_id = '小区ID';

-- 1.2 查找特定站点下所有小区和设备（站点故障影响分析）
SELECT element_id, element_name, net_type, element_type,
       device_uuid, device_name, device_type,
       room_name, life_cycle_status, use_time
FROM npas.mv_logic_element_device_room_station
WHERE station_id = '站点ID'
ORDER BY net_type, element_type;

-- 1.3 机房断电影响范围分析（查找特定机房的所有资源）
SELECT element_id, element_name, net_type, element_type,
       device_uuid, device_name, device_type,
       nodeb_name, life_cycle_status, vip_level
FROM npas.mv_logic_element_device_room_station
WHERE room_id = '机房ID'
  AND life_cycle_status = '现网有业务'
ORDER BY element_type, net_type;
```

### 2. 容量规划与资源优化
```sql
-- 2.1 机房设备密度分析（识别高密度机房）
SELECT room_name, station_name, city,
       COUNT(DISTINCT element_id) as element_count,
       COUNT(DISTINCT device_uuid) as device_count,
       STRING_AGG(DISTINCT net_type, ', ') as supported_nets,
       ROUND(1.0 * COUNT(DISTINCT device_uuid) / NULLIF(COUNT(DISTINCT element_id), 0), 2) as devices_per_element
FROM npas.mv_logic_element_device_room_station
WHERE room_id IS NOT NULL
  AND life_cycle_status = '现网有业务'
GROUP BY room_name, station_name, city
HAVING COUNT(DISTINCT device_uuid) > 10  -- 设备数量阈值
ORDER BY device_count DESC;

-- 2.2 站点多网络覆盖分析（识别2G/4G/5G共站址站点）
SELECT station_id, station_name, city,
       COUNT(DISTINCT CASE WHEN net_type = '2G' THEN element_id END) as 2g_count,
       COUNT(DISTINCT CASE WHEN net_type = '4G' THEN element_id END) as 4g_count,
       COUNT(DISTINCT CASE WHEN net_type = '5G' THEN element_id END) as 5g_count,
       COUNT(DISTINCT element_id) as total_elements,
       STRING_AGG(DISTINCT net_type, '+') as coverage_types
FROM npas.mv_logic_element_device_room_station
WHERE life_cycle_status = '现网有业务'
GROUP BY station_id, station_name, city
HAVING COUNT(DISTINCT net_type) >= 2  -- 多网络共站
ORDER BY total_elements DESC;

-- 2.3 虚拟机房资源分析（云化资源统计）
SELECT room_name, station_name, city, owner,
       COUNT(DISTINCT element_id) as element_count,
       COUNT(DISTINCT device_uuid) as device_count,
       STRING_AGG(DISTINCT net_type, ', ') as net_types,
       STRING_AGG(DISTINCT element_type, ', ') as element_types
FROM npas.mv_logic_element_device_room_station
WHERE is_virtual_room = '是'
  AND life_cycle_status = '现网有业务'
GROUP BY room_name, station_name, city, owner
ORDER BY element_count DESC;
```

### 3. 网络演进与升级分析
```sql
-- 3.1 4G向5G演进站点分析（识别已部署5G的4G站点）
SELECT s.station_id, s.station_name, s.city,
       COUNT(DISTINCT CASE WHEN mv.net_type = '4G' THEN mv.element_id END) as 4g_count,
       COUNT(DISTINCT CASE WHEN mv.net_type = '5G' THEN mv.element_id END) as 5g_count,
       MAX(CASE WHEN mv.net_type = '5G' THEN mv.setup_time END) as latest_5g_deploy,
       COUNT(DISTINCT CASE WHEN mv.net_type = '5G' THEN mv.device_uuid END) as 5g_device_count
FROM npas.wr_space_station s
JOIN npas.mv_logic_element_device_room_station mv ON s.station_id = mv.station_id
WHERE mv.life_cycle_status = '现网有业务'
GROUP BY s.station_id, s.station_name, s.city
HAVING COUNT(DISTINCT CASE WHEN mv.net_type = '4G' THEN mv.element_id END) > 0
   AND COUNT(DISTINCT CASE WHEN mv.net_type = '5G' THEN mv.element_id END) > 0
ORDER BY 5g_count DESC, city;

-- 3.2 老旧设备识别（基于启用时间）
SELECT device_uuid, device_name, device_type,
       element_id, element_name, net_type,
       room_name, station_name, city,
       use_time, 
       EXTRACT(YEAR FROM CURRENT_DATE) - EXTRACT(YEAR FROM use_time) as years_in_service
FROM npas.mv_logic_element_device_room_station
WHERE device_uuid IS NOT NULL
  AND life_cycle_status = '现网有业务'
  AND use_time IS NOT NULL
  AND EXTRACT(YEAR FROM use_time) < EXTRACT(YEAR FROM CURRENT_DATE) - 5  -- 使用超过5年
ORDER BY use_time;

-- 3.3 NSA/SA架构分析（通过设备类型推断）
SELECT station_id, station_name, city,
       COUNT(DISTINCT CASE WHEN device_uuid LIKE 'AAU-%' THEN element_id END) as aau_cells,
       COUNT(DISTINCT CASE WHEN device_uuid LIKE 'RRU-%' THEN element_id END) as rru_cells,
       COUNT(DISTINCT CASE WHEN device_uuid LIKE 'DU-%' THEN element_id END) as du_count,
       CASE 
         WHEN COUNT(DISTINCT CASE WHEN device_uuid LIKE 'AAU-%' THEN element_id END) > 0 
          AND COUNT(DISTINCT CASE WHEN device_uuid LIKE 'DU-%' THEN element_id END) > 0 
         THEN 'SA' 
         WHEN COUNT(DISTINCT CASE WHEN device_uuid LIKE 'AAU-%' THEN element_id END) > 0 
          AND COUNT(DISTINCT CASE WHEN device_uuid LIKE 'DU-%' THEN element_id END) = 0 
         THEN 'NSA' 
         ELSE '其他' 
       END as architecture_type
FROM npas.mv_logic_element_device_room_station
WHERE net_type = '5G'
  AND life_cycle_status = '现网有业务'
GROUP BY station_id, station_name, city
HAVING COUNT(DISTINCT element_id) > 0;
```

### 4. 业务质量与VIP保障
```sql
-- 4.1 VIP站点资源清单
SELECT station_id, station_name, city, address,
       COUNT(DISTINCT element_id) as total_elements,
       COUNT(DISTINCT CASE WHEN net_type = '2G' THEN element_id END) as 2g_count,
       COUNT(DISTINCT CASE WHEN net_type = '4G' THEN element_id END) as 4g_count,
       COUNT(DISTINCT CASE WHEN net_type = '5G' THEN element_id END) as 5g_count,
       COUNT(DISTINCT device_uuid) as device_count,
       STRING_AGG(DISTINCT owner, ', ') as room_owners
FROM npas.mv_logic_element_device_room_station mv
JOIN npas.wr_space_station s ON mv.station_id = s.station_id
WHERE mv.life_cycle_status = '现网有业务'
  AND s.vip_level IN ('VVIP', 'VIP')
GROUP BY station_id, station_name, city, address, s.vip_level
ORDER BY s.vip_level, total_elements DESC;

-- 4.2 高价值业务保障分析（高铁、机场、政府区域）
SELECT mv.city, mv.station_name, s.address,
       COUNT(DISTINCT mv.element_id) as element_count,
       STRING_AGG(DISTINCT mv.net_type, ', ') as coverage,
       MAX(CASE WHEN s.address LIKE '%高铁%' OR s.address LIKE '%火车站%' THEN '铁路' 
                WHEN s.address LIKE '%机场%' THEN '机场'
                WHEN s.address LIKE '%政府%' OR s.address LIKE '%市委%' THEN '政府'
                WHEN s.address LIKE '%医院%' THEN '医院'
                WHEN s.address LIKE '%学校%' OR s.address LIKE '%大学%' THEN '教育'
                ELSE '其他' END) as site_category
FROM npas.mv_logic_element_device_room_station mv
JOIN npas.wr_space_station s ON mv.station_id = s.station_id
WHERE mv.life_cycle_status = '现网有业务'
  AND (s.address LIKE '%高铁%' OR s.address LIKE '%机场%' OR s.address LIKE '%政府%'
       OR s.address LIKE '%医院%' OR s.address LIKE '%大学%')
GROUP BY mv.city, mv.station_name, s.address
ORDER BY mv.city, element_count DESC;

-- 4.3 双路由/冗余度检查（同一站点多个机房）
SELECT station_id, station_name, city,
       COUNT(DISTINCT room_id) as room_count,
       STRING_AGG(DISTINCT room_name, ', ') as room_names,
       COUNT(DISTINCT element_id) as element_count,
       COUNT(DISTINCT device_uuid) as device_count
FROM npas.mv_logic_element_device_room_station
WHERE life_cycle_status = '现网有业务'
GROUP BY station_id, station_name, city
HAVING COUNT(DISTINCT room_id) > 1  -- 多机房站点
ORDER BY room_count DESC, element_count DESC;
```

### 5. 数据质量监控与告警
```sql
-- 5.1 关键字段完整性监控日报
-- 注意：此处COUNT(*)统计问题记录数（含重复），如需统计问题元素数应使用COUNT(DISTINCT element_id)
SELECT 
  '坐标缺失' as check_item,
  COUNT(*) as problem_records,
  COUNT(DISTINCT element_id) as problem_elements,
  ROUND(100.0 * COUNT(*) / total.total_records, 2) as problem_record_percent,
  ROUND(100.0 * COUNT(DISTINCT element_id) / total.distinct_elements, 2) as problem_element_percent
FROM npas.mv_logic_element_device_room_station,
     (SELECT COUNT(*) as total_records, 
             COUNT(DISTINCT element_id) as distinct_elements 
      FROM npas.mv_logic_element_device_room_station 
      WHERE life_cycle_status = '现网有业务') total
WHERE life_cycle_status = '现网有业务'
  AND (longitude IS NULL OR latitude IS NULL)
UNION ALL
SELECT 
  '设备关联缺失',
  COUNT(*) as problem_records,
  COUNT(DISTINCT element_id) as problem_elements,
  ROUND(100.0 * COUNT(*) / total.total_records, 2) as problem_record_percent,
  ROUND(100.0 * COUNT(DISTINCT element_id) / total.distinct_elements, 2) as problem_element_percent
FROM npas.mv_logic_element_device_room_station,
     (SELECT COUNT(*) as total_records, 
             COUNT(DISTINCT element_id) as distinct_elements 
      FROM npas.mv_logic_element_device_room_station 
      WHERE life_cycle_status = '现网有业务' AND element_type LIKE '%cell') total
WHERE life_cycle_status = '现网有业务'
  AND element_type LIKE '%cell'
  AND device_uuid IS NULL
UNION ALL
SELECT 
  '规划信息缺失',
  COUNT(*) as problem_records,
  COUNT(DISTINCT element_id) as problem_elements,
  ROUND(100.0 * COUNT(*) / total.total_records, 2) as problem_record_percent,
  ROUND(100.0 * COUNT(DISTINCT element_id) / total.distinct_elements, 2) as problem_element_percent
FROM npas.mv_logic_element_device_room_station,
     (SELECT COUNT(*) as total_records, 
             COUNT(DISTINCT element_id) as distinct_elements 
      FROM npas.mv_logic_element_device_room_station 
      WHERE life_cycle_status = '现网有业务') total
WHERE life_cycle_status = '现网有业务'
  AND element_planid IS NULL
  AND device_planid IS NULL;

-- 5.2 异常关联检测（如5G小区关联4G设备）
SELECT element_id, element_name, net_type, element_type,
       device_uuid, device_name, 
       CASE 
         WHEN net_type = '5G' AND device_uuid LIKE 'RRU-%' THEN '5G小区关联4G RRU'
         WHEN net_type = '4G' AND device_uuid LIKE 'AAU-%' THEN '4G小区关联5G AAU'
         ELSE '其他异常'
       END as anomaly_type,
       room_name, station_name, city
FROM npas.mv_logic_element_device_room_station
WHERE (net_type = '5G' AND device_uuid LIKE 'RRU-%')
   OR (net_type = '4G' AND device_uuid LIKE 'AAU-%')
   AND life_cycle_status = '现网有业务';

-- 5.3 生命周期状态异常检测
SELECT element_id, element_name, net_type, element_type,
       life_cycle_status, use_time, exit_time,
       room_name, station_name, city,
       CASE 
         WHEN life_cycle_status = '现网有业务' AND exit_time IS NOT NULL THEN '有业务但有退网时间'
         WHEN life_cycle_status LIKE '%退网%' AND use_time > CURRENT_DATE - INTERVAL '30 days' THEN '最近启用但已退网'
         WHEN life_cycle_status = '现网有业务' AND use_time IS NULL THEN '有业务但无启用时间'
         ELSE '其他异常'
       END as status_anomaly
FROM npas.mv_logic_element_device_room_station
WHERE (life_cycle_status = '现网有业务' AND exit_time IS NOT NULL)
   OR (life_cycle_status LIKE '%退网%' AND use_time > CURRENT_DATE - INTERVAL '30 days')
   OR (life_cycle_status = '现网有业务' AND use_time IS NULL)
ORDER BY status_anomaly, net_type;
```

### 6. 铁塔与基础设施分析
```sql
-- 6.1 铁塔资源共享分析（同一铁塔服务多个站点）
SELECT tower_id, tower_name, 
       COUNT(DISTINCT station_id) as station_count,
       COUNT(DISTINCT room_id) as room_count,
       COUNT(DISTINCT element_id) as element_count,
       STRING_AGG(DISTINCT station_name, ', ') as station_names,
       STRING_AGG(DISTINCT net_type, ', ') as network_types
FROM npas.mv_logic_element_device_room_station
WHERE tower_id IS NOT NULL
GROUP BY tower_id, tower_name
HAVING COUNT(DISTINCT station_id) > 1  -- 共享铁塔
ORDER BY station_count DESC, element_count DESC;

-- 6.2 铁塔地址编码标准化检查
SELECT tower_id, tower_name, tower_add_code,
       station_name, city,
       CASE 
         WHEN tower_add_code ~ '^[A-Z]{2}-\d{4}-\d{3}$' THEN '标准格式'
         WHEN tower_add_code IS NULL THEN '缺失'
         WHEN tower_add_code = '' THEN '空值'
         ELSE '非标准格式'
       END as code_format,
       LENGTH(tower_add_code) as code_length
FROM npas.mv_logic_element_device_room_station
WHERE tower_id IS NOT NULL
  AND life_cycle_status = '现网有业务'
ORDER BY code_format, city, station_name;

-- 6.3 基础设施容量分析（铁塔承载能力）
SELECT city,
       COUNT(DISTINCT tower_id) as tower_count,
       COUNT(DISTINCT station_id) as station_count,
       COUNT(DISTINCT element_id) as element_count,
       COUNT(DISTINCT device_uuid) as device_count,
       ROUND(1.0 * COUNT(DISTINCT station_id) / NULLIF(COUNT(DISTINCT tower_id), 0), 2) as stations_per_tower,
       ROUND(1.0 * COUNT(DISTINCT element_id) / NULLIF(COUNT(DISTINCT tower_id), 0), 2) as elements_per_tower
FROM npas.mv_logic_element_device_room_station
WHERE tower_id IS NOT NULL
  AND life_cycle_status = '现网有业务'
GROUP BY city
ORDER BY elements_per_tower DESC;
```

### 7. 跨系统集成查询
```sql
-- 7.1 资源中心(RC)同步状态检查
SELECT station_id, station_name, station_cuid,
       room_id, room_name, room_cuid,
       CASE 
         WHEN station_cuid IS NOT NULL AND room_cuid IS NOT NULL THEN '完全同步'
         WHEN station_cuid IS NOT NULL AND room_cuid IS NULL THEN '仅站点同步'
         WHEN station_cuid IS NULL AND room_cuid IS NOT NULL THEN '仅机房同步'
         ELSE '未同步'
       END as sync_status,
       COUNT(DISTINCT element_id) as element_count
FROM npas.mv_logic_element_device_room_station
WHERE life_cycle_status = '现网有业务'
GROUP BY station_id, station_name, station_cuid, room_id, room_name, room_cuid
ORDER BY sync_status, element_count DESC;

-- 7.2 规划与实施一致性检查
SELECT mv.element_id, mv.element_name, mv.net_type,
       mv.element_planid, mv.device_planid,
       pcp.site_planning_name, pcp.site_planning_code,
       mv.station_name, mv.city,
       CASE 
         WHEN mv.element_planid IS NOT NULL AND pcp.site_planning_id IS NOT NULL THEN '规划一致'
         WHEN mv.element_planid IS NOT NULL AND pcp.site_planning_id IS NULL THEN '规划缺失'
         WHEN mv.element_planid IS NULL AND pcp.site_planning_id IS NOT NULL THEN '实施缺失'
         ELSE '无规划信息'
       END as planning_status
FROM npas.mv_logic_element_device_room_station mv
LEFT JOIN npas.pl_cover_point pcp ON mv.element_planid = pcp.site_planning_id::text
WHERE mv.life_cycle_status = '现网有业务'
  AND (mv.element_planid IS NOT NULL OR pcp.site_planning_id IS NOT NULL)
LIMIT 50;

-- 7.3 OMC网管系统数据一致性检查
SELECT mv.element_id, mv.element_name, mv.cgi,
       cell.omc_cell_name, cell.administrative_state,
       mv.life_cycle_status, mv.use_time,
       CASE 
         WHEN cell.omc_cell_name IS NULL THEN 'OMC无记录'
         WHEN mv.life_cycle_status = '现网有业务' AND cell.administrative_state != '1' THEN '状态不一致'
         ELSE '一致'
       END as consistency_status
FROM npas.mv_logic_element_device_room_station mv
LEFT JOIN npas.wr_logic_eutrancell cell ON mv.element_id = cell.eutrancell_id::text
WHERE mv.net_type = '4G'
  AND mv.element_type = 'eutrancell'
  AND mv.life_cycle_status = '现网有业务'
LIMIT 100;
```

## 查询性能优化建议

1. **索引策略**：
   ```sql
   -- 为常用查询条件创建组合索引
   CREATE INDEX idx_mv_business_query ON npas.mv_logic_element_device_room_station 
   (life_cycle_status, net_type, city, station_id);
   
   CREATE INDEX idx_mv_location_query ON npas.mv_logic_element_device_room_station 
   (city, station_name, room_name);
   
   CREATE INDEX idx_mv_device_query ON npas.mv_logic_element_device_room_station 
   (device_uuid, element_id, net_type);
   ```

2. **分区建议**：对于超大规模数据，考虑按`city`或`net_type`进行分区。

3. **物化视图刷新策略**：
   - 业务低峰期刷新：`REFRESH MATERIALIZED VIEW CONCURRENTLY npas.mv_logic_element_device_room_station;`
   - 增量刷新：根据`use_time`或`setup_time`进行增量更新

4. **查询优化技巧**：
   - 使用`EXPLAIN ANALYZE`分析查询计划
   - 避免在WHERE子句中使用函数计算
   - 合理使用`LIMIT`限制返回行数
   - 优先使用已索引字段进行过滤和排序

## 业务场景查询模板

### 模板A：故障应急定位
```sql
-- 输入：小区ID/CGI/基站ID
SELECT [所需字段]
FROM npas.mv_logic_element_device_room_station
WHERE element_id = :element_id 
   OR cgi = :cgi 
   OR nodeb_uuid = :nodeb_id
   OR device_uuid = :device_id;
```

### 模板B：区域资源统计
```sql
-- 输入：城市/区域/网络类型
-- 注意：统计元素数量必须使用COUNT(DISTINCT element_id)
SELECT city, [统计维度], 
       COUNT(DISTINCT element_id) as element_count,
       COUNT(DISTINCT device_uuid) as device_count,
       [聚合指标]
FROM npas.mv_logic_element_device_room_station
WHERE city = :city 
   AND net_type = :net_type
   AND life_cycle_status = '现网有业务'
GROUP BY city, [统计维度]
ORDER BY element_count DESC;
```

### 模板C：数据质量检查
```sql
-- 输入：检查类型/阈值
-- 注意：problem_count统计问题记录数，problem_elements统计问题元素数（去重）
SELECT [检查项], 
       COUNT(*) as problem_records,
       COUNT(DISTINCT element_id) as problem_elements
FROM npas.mv_logic_element_device_room_station
WHERE [问题条件]
   AND life_cycle_status = '现网有业务'
GROUP BY [检查项]
HAVING COUNT(DISTINCT element_id) > :threshold
ORDER BY problem_elements DESC;
```

### 模板D：规划实施跟踪
```sql
-- 输入：规划ID/时间范围
-- 注意：统计实施元素数量应使用COUNT(DISTINCT element_id)
SELECT [规划相关字段], 
       COUNT(DISTINCT element_id) as implementation_elements,
       COUNT(DISTINCT device_uuid) as implementation_devices
FROM npas.mv_logic_element_device_room_station
WHERE (element_planid = :plan_id OR device_planid = :plan_id)
   AND setup_time BETWEEN :start_date AND :end_date
   AND life_cycle_status = '现网有业务'
GROUP BY [规划相关字段]
ORDER BY implementation_elements DESC;
```

## Notes

- Replace table and column names with actual names from your database
- Adjust filters based on your data characteristics
- Use appropriate indexes for performance
- Consider partitioning large tables by date or region
- Regular query optimization recommended