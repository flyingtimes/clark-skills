# Wireless Resource Management Tutorial

This tutorial walks through a typical workflow for telecom engineers using the wireless resource management skill. We'll locate a problematic cell, find its physical equipment, check planning information, and audit data quality.

## Scenario

You receive an alarm for cell `EUT-123456` with performance issues. You need to:

1. **Locate the physical equipment** associated with this cell
2. **Check planning information** to understand deployment context
3. **Audit data quality** to ensure records are complete and accurate
4. **Generate a report** for maintenance teams

## Prerequisites

- Python 3.8+ installed
- Wireless resource database accessible (or use offline mode)
- Dependencies installed: `psycopg2-binary`, `pandas` (optional)

## Step 1: Set Up Environment

First, ensure you have the necessary scripts and configuration:

```bash
cd wireless-resource-management/scripts

# Test imports
python test_imports.py

# Configure database connection (if not already configured)
# Edit db_config.py or set environment variables:
# export DB_HOST=localhost
# export DB_PORT=5432
# export DB_NAME=wireless_db
# export DB_USER=postgres
# export DB_PASSWORD=your_password
```

## Step 2: Find Cell Location

Use the `find_cell_location.py` script to trace the cell's physical location:

```bash
python find_cell_location.py "EUT-123456"
```

Sample output:
```
Cell Information:
  ID: EUT-123456
  Name: City_Center_4G_01
  Network Type: 4G
  Cell Table: wr_logic_eutrancell

Device Associations:
  RRU ID: RRU-789012 (Primary)
  Device Type: RRU
  Room: Central_Equipment_Room_1
  Station: City_Center_Tower
  Coordinates: 31.2304, 121.4737

Location Details:
  Room ID: ROOM-001
  Station ID: STATION-001
  Address: 123 Main Street, Downtown
  City: Shanghai
```

If you need JSON format for integration:
```bash
python find_cell_location.py "EUT-123456" --json
```

## Step 3: Check Planning Information

Use the `find_rru_planning.py` script to find planning point associations. Since we found the RRU ID is `RRU-789012`, we can query its planning information:

```bash
python find_rru_planning.py --serial "RRU-789012"
```

Or directly query planning for the cell:
```bash
python find_rru_planning.py --cell "EUT-123456"
```

Sample output:
```
Planning Information:
  RRU Serial: RRU-789012
  Planning Point: PLAN-2023-0456
  Site Planning Name: City_Center_5G_Expansion
  Band: 2.6GHz
  Station Type: 宏站 (Macro Station)
  Coverage Type: 室外覆盖 (Outdoor Coverage)
  Network Technology: 5G
  Planning Date: 2023-05-15
  Implementation Status: 已实施 (Implemented)
```

This tells you the cell was deployed as part of the "City_Center_5G_Expansion" project, planned for 5G but actually deployed as 4G (note the cell is 4G while planning was for 5G - a potential discrepancy to investigate).

## Step 4: Audit Cell Associations

Check if the cell has proper device associations using `audit_cell_associations.py`:

```bash
python audit_cell_associations.py --cell "EUT-123456"
```

Or check all 4G cells in a batch:
```bash
python audit_cell_associations.py --network 4G --limit 10
```

Sample output:
```
Cell Association Audit for EUT-123456:
  ✓ Has RRU association: RRU-789012
  ✗ Missing AAU association (expected for 5G cells)
  ✓ Has valid room association: Central_Equipment_Room_1
  ✓ Has valid station association: City_Center_Tower
  ✓ Coordinates present: 31.2304, 121.4737

Data Quality Issues:
  - No AAU association (but cell is 4G, so this is expected)
  - Planning mismatch: Planned as 5G, deployed as 4G
```

## Step 5: Run Comprehensive Data Quality Checks

Validate mandatory fields and relationships:

```bash
# Check mandatory fields
python check_mandatory_fields.py

# Validate relationships
python validate_relationships.py

# Generate comprehensive report
python generate_report.py --output cell_audit_report.html --format html
```

The report will highlight:
- Missing mandatory fields
- Broken relationships
- Orphaned records
- Data consistency issues

## Step 6: Investigate Using SQL Queries

For deeper investigation, use the PostgreSQL tool with queries from `query-examples.md`. The recommended approach is to use the materialized view `mv_logic_element_device_room_station` as the primary data source, which provides pre-joined information about cells, devices, rooms, and stations.

### Using the Materialized View (Recommended)
```sql
-- Get complete cell information using the materialized view
SELECT 
  mv.element_id, mv.element_name,
  mv.life_cycle_status,
  mv.room_name, mv.station_name,
  mv.latitude, mv.longitude,
  mv.city, mv.net_type,
  mv.device_uuid, mv.device_name,
  mv.tower_add_code,
  mv.station_cuid, mv.room_cuid
FROM npas.mv_logic_element_device_room_station mv
WHERE mv.element_id = 'EUT-123456'
  AND mv.element_type IN ('eutrancell', 'nrcell', 'gsmcell');
```

### Using Traditional Joins (Legacy)
If you need fields not included in the materialized view, you can use traditional joins:

```sql
-- Get complete cell information with all joins
SELECT 
  cell.eutrancell_id, cell.eutrancell_name,
  dl.life_cycle_status, dv.vip_level,
  room.room_name, station.station_name,
  station.latitude, station.longitude,
  pcp.site_planning_name, db.band,
  ds.station_type, dc.cover_type
FROM npas.wr_logic_eutrancell cell
LEFT JOIN npas.dim_lifecyclestatus dl ON cell.life_cycle_status_key = dl.life_cycle_status_key
LEFT JOIN npas.dim_viplevel dv ON cell.vip_level_key = dv.vip_level_key
LEFT JOIN npas.wr_map_rru_cell rc ON cell.eutrancell_id = rc.logic_cell_id
LEFT JOIN npas.wr_device_rru rru ON rc.rru_id = rru.rru_id
LEFT JOIN npas.wr_space_room room ON rru.room_id = room.room_id
LEFT JOIN npas.wr_space_station station ON room.station_id = station.station_id
LEFT JOIN npas.ac_access_batch_rel_rs aabrr ON cell.cell_id::text = aabrr.rs_cuid::text
LEFT JOIN npas.ac_access_batch aab ON aabrr.access_batch_id = aab.access_batch_id
LEFT JOIN npas.ac_access_solution aas ON aab.access_solution_id = aas.access_solution_id
LEFT JOIN npas.pl_cover_point pcp ON aas.site_planning_id = pcp.site_planning_id
LEFT JOIN npas.dim_band db ON pcp.band_key = db.band_key
LEFT JOIN npas.dim_stationtype ds ON pcp.station_type_key = ds.station_type_key
LEFT JOIN npas.dim_covtype dc ON pcp.cover_type_key = dc.covtype_key
WHERE cell.eutrancell_id = 'EUT-123456';
```

## Step 7: Create Maintenance Ticket

Based on findings, create a maintenance ticket:

1. **Issue**: Cell EUT-123456 shows performance degradation
2. **Location**: City_Center_Tower, 123 Main Street
3. **Equipment**: RRU-789012 in Central_Equipment_Room_1
4. **Planning Context**: Part of City_Center_5G_Expansion project (planned as 5G, deployed as 4G)
5. **Data Quality**: All associations valid, but planning mismatch noted
6. **Action Required**: 
   - Physical inspection of RRU-789012
   - Verify radio configuration matches planning
   - Update records if deployment differs from planning

## Step 8: Update Records (If Needed)

If you discover incorrect data, you can update records:

```sql
-- Example: Update cell VIP level
UPDATE npas.wr_logic_eutrancell
SET vip_level_key = (SELECT vip_level_key FROM npas.dim_viplevel WHERE vip_level = 'VIP')
WHERE eutrancell_id = 'EUT-123456';

-- Example: Add missing association
INSERT INTO npas.wr_map_rru_cell (map_id, rru_id, logic_cell_id, create_time)
VALUES (gen_random_uuid(), 'RRU-789012', 'EUT-123456', NOW());
```

**Always backup before making changes and follow your organization's change management procedures.**

## Common Troubleshooting

### Cell Not Found
- Check if cell exists in correct table (2G/4G/5G)
- Verify `is_del = false` filter
- Check data synchronization status

### Missing Location Information
- Trace through alternative device associations (AAU, antenna, WIDS)
- Check if mapping table entries exist
- Verify room and station records are not deleted

### Performance Issues with Queries
- Add indexes on frequently joined columns
- Use `EXPLAIN ANALYZE` to identify bottlenecks
- Consider partitioning large tables

## Next Steps

1. **Automate regular audits**: Schedule daily/weekly data quality checks
2. **Build dashboards**: Create visualization of cell locations and status
3. **Integrate with alarm systems**: Link cell information with performance monitoring
4. **Train team members**: Share this skill with colleagues

## Additional Resources

- [Quick Reference](quick-reference.md) - Essential information for daily operations
- [Query Examples](query-examples.md) - Sample SQL queries for common tasks
- [Audit Rules](audit-rules.md) - Data quality validation rules
- [Process Guide](process-guide.md) - Operational workflows and best practices