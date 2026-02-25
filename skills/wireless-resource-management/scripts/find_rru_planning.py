#!/usr/bin/env python3
"""
Find RRU serial numbers and their associated planning point information.
Query RRU devices and trace their planning associations through the access solution chain.
"""

import argparse
import sys
from db_config import config

def find_rru_planning(rru_id=None, planning_id=None, serial_number=None, sn_field="serial_number", limit=100):
    """
    Find RRU devices with their serial numbers and planning point information.
    
    Args:
        rru_id: Filter by specific RRU ID
        planning_id: Filter by planning point ID
        serial_number: Filter by RRU serial number (partial match)
        sn_field: Name of the serial number field in wr_device_rru table
        limit: Maximum number of results to return
    
    Returns:
        List of dictionaries with RRU and planning information
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
    except ImportError:
        print("Error: psycopg2 not installed. Install with: pip install psycopg2-binary")
        sys.exit(1)
    
    try:
        conn = psycopg2.connect(**config.psycopg2_params())
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Build WHERE clause based on filters
        where_conditions = []
        params = []
        
        if rru_id:
            where_conditions.append("rru.rru_id = %s")
            params.append(rru_id)
        
        if planning_id:
            where_conditions.append("pcp.site_planning_id = %s")
            params.append(planning_id)
        
        if serial_number:
            where_conditions.append(f"rru.{sn_field} ILIKE %s")
            params.append(f"%{serial_number}%")
        
        # Always exclude deleted records
        where_conditions.append("rru.is_del = false")
        
        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        # Query to find RRU information with planning point associations
        # Note: Field names may need adjustment based on actual schema
        query = f"""
            SELECT 
                -- RRU information
                rru.rru_id,
                rru.name as rru_name,
                rru.device_model,
                rru.serial_number,
                rru.manufacturer,
                rru.installation_date,
                rru.life_cycle_status_key,
                dl.life_cycle_status,
                
                -- Room and location information
                room.room_id,
                room.room_name,
                station.station_id,
                station.station_name,
                station.city,
                station.area,
                station.latitude,
                station.longitude,
                station.address,
                
                -- Planning point information
                pcp.site_planning_id,
                pcp.site_planning_code,
                pcp.site_planning_name,
                pcp.longitude as planned_longitude,
                pcp.latitude as planned_latitude,
                pcp.address as planned_address,
                
                -- Planning metadata from dimension tables
                db.band,
                ds.station_type,
                dc.cover_type,
                dn.network_type,
                dv.device_vendor,
                
                -- Cell associations count
                cell_count.cell_count
                
            FROM npas.wr_device_rru rru
            
            -- Join dimension tables for decoded values
            LEFT JOIN npas.dim_lifecyclestatus dl ON rru.life_cycle_status_key = dl.life_cycle_status_key
            LEFT JOIN npas.dim_devicevendor dv ON rru.device_vendor_key = dv.device_vendor_key
            
            -- Room and station associations for physical location
            LEFT JOIN npas.wr_space_room room ON rru.room_id = room.room_id
            LEFT JOIN npas.wr_space_station station ON room.station_id = station.station_id
            
            -- Planning point associations through access solution chain
            LEFT JOIN npas.ac_access_batch_rel_rs aabrr ON rru.rru_id::text = aabrr.rs_cuid::text
            LEFT JOIN npas.ac_access_batch aab ON aabrr.access_batch_id = aab.access_batch_id
            LEFT JOIN npas.ac_access_solution aas ON aab.access_solution_id = aas.access_solution_id
            LEFT JOIN npas.pl_cover_point pcp ON aas.site_planning_id = pcp.site_planning_id
            
            -- Planning metadata dimension tables
            LEFT JOIN npas.dim_band db ON pcp.band_key = db.band_key
            LEFT JOIN npas.dim_stationtype ds ON pcp.station_type_key = ds.station_type_key
            LEFT JOIN npas.dim_covtype dc ON pcp.cover_type_key = dc.covtype_key
            LEFT JOIN npas.dim_networktype dn ON pcp.network_type_key = dn.network_type_key
            
            -- Count associated cells
            LEFT JOIN (
                SELECT rru_id, COUNT(DISTINCT logic_cell_id) as cell_count
                FROM npas.wr_map_rru_cell
                WHERE is_del = false
                GROUP BY rru_id
            ) cell_count ON cell_count.rru_id = rru.rru_id
            
            {where_clause}
            
            ORDER BY 
                CASE WHEN rru.life_cycle_status_key IN (
                    SELECT life_cycle_status_key FROM npas.dim_lifecyclestatus 
                    WHERE life_cycle_status = '现网有业务'
                ) THEN 1 ELSE 2 END,
                rru.installation_date DESC NULLS LAST,
                rru.rru_id
            
            LIMIT %s;
        """
        
        params.append(limit)
        
        # Replace serial_number field with the specified field name, keep column name as 'serial_number'
        query = query.replace("rru.serial_number", f"rru.{sn_field} as serial_number")
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        # Get summary statistics
        summary_query = """
            SELECT 
                COUNT(*) as total_rrus,
                COUNT(DISTINCT rru.rru_id) as rrus_with_planning,
                COUNT(DISTINCT pcp.site_planning_id) as unique_planning_points,
                ROUND(100.0 * COUNT(DISTINCT CASE WHEN pcp.site_planning_id IS NOT NULL THEN rru.rru_id END) / 
                      COUNT(DISTINCT rru.rru_id), 2) as planning_coverage_rate
            FROM npas.wr_device_rru rru
            LEFT JOIN npas.ac_access_batch_rel_rs aabrr ON rru.rru_id::text = aabrr.rs_cuid::text
            LEFT JOIN npas.ac_access_batch aab ON aabrr.access_batch_id = aab.access_batch_id
            LEFT JOIN npas.ac_access_solution aas ON aab.access_solution_id = aas.access_solution_id
            LEFT JOIN npas.pl_cover_point pcp ON aas.site_planning_id = pcp.site_planning_id
            WHERE rru.is_del = false;
        """
        
        cursor.execute(summary_query)
        summary = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return {
            "results": results,
            "summary": summary
        }
        
    except Exception as e:
        print(f"Database error: {e}")
        import traceback
        traceback.print_exc()
        return None

def format_results(rru_data, output_format="text"):
    """Format RRU and planning information for display."""
    if not rru_data:
        return "No RRU data available."
    
    if output_format == "json":
        import json
        return json.dumps(rru_data, indent=2, ensure_ascii=False)
    
    results = rru_data["results"]
    summary = rru_data["summary"]
    
    output = []
    output.append("RRU SERIAL NUMBERS AND PLANNING POINT INFORMATION")
    output.append("=" * 80)
    output.append("")
    
    # Summary section
    output.append("SUMMARY")
    output.append("-" * 40)
    output.append(f"Total RRUs in database: {summary.get('total_rrus', 0):,}")
    output.append(f"RRUs with planning associations: {summary.get('rrus_with_planning', 0):,}")
    output.append(f"Unique planning points referenced: {summary.get('unique_planning_points', 0):,}")
    output.append(f"Planning coverage rate: {summary.get('planning_coverage_rate', 0):.2f}%")
    output.append("")
    
    # Detailed results
    if not results:
        output.append("No RRUs found matching the criteria.")
    else:
        output.append(f"DETAILED RESULTS (showing {len(results)} RRUs)")
        output.append("-" * 40)
        
        for i, rru in enumerate(results, 1):
            output.append(f"\n{i}. RRU: {rru.get('rru_id', 'N/A')}")
            output.append(f"   Name: {rru.get('rru_name', 'N/A')}")
            output.append(f"   Device Model: {rru.get('device_model', 'N/A')}")
            output.append(f"   Serial Number: {rru.get('serial_number', 'N/A')}")
            output.append(f"   Manufacturer: {rru.get('manufacturer', 'N/A')}")
            output.append(f"   Status: {rru.get('life_cycle_status', 'N/A')}")
            output.append(f"   Installation Date: {rru.get('installation_date', 'N/A')}")
            output.append(f"   Associated Cells: {rru.get('cell_count', 0)}")
            
            # Location information
            if rru.get('room_name'):
                output.append(f"   Location: {rru.get('room_name', 'N/A')} → {rru.get('station_name', 'N/A')}")
                output.append(f"   Coordinates: {rru.get('latitude', 'N/A')}, {rru.get('longitude', 'N/A')}")
                output.append(f"   Address: {rru.get('address', 'N/A')}")
            
            # Planning information
            if rru.get('site_planning_id'):
                output.append(f"   Planning Point: {rru.get('site_planning_code', 'N/A')} - {rru.get('site_planning_name', 'N/A')}")
                output.append(f"   Planning Metadata: {rru.get('band', 'N/A')} {rru.get('station_type', 'N/A')} {rru.get('cover_type', 'N/A')} {rru.get('network_type', 'N/A')}")
                if rru.get('planned_latitude') and rru.get('planned_longitude'):
                    output.append(f"   Planned Coordinates: {rru.get('planned_latitude', 'N/A')}, {rru.get('planned_longitude', 'N/A')}")
            else:
                output.append(f"   Planning Point: No planning association found")
    
    output.append("")
    output.append("NOTES:")
    output.append("-" * 40)
    output.append("1. Planning association requires complete chain: RRU → ac_access_batch_rel_rs → ac_access_batch → ac_access_solution → pl_cover_point")
    output.append("2. Missing planning associations may indicate data synchronization issues")
    output.append("3. Serial numbers are crucial for hardware inventory tracking")
    output.append("4. Field names (e.g., 'serial_number') may vary based on actual database schema")
    
    return "\n".join(output)

def main():
    parser = argparse.ArgumentParser(description="Find RRU serial numbers and planning point information")
    parser.add_argument("--rru-id", help="Filter by specific RRU ID")
    parser.add_argument("--planning-id", help="Filter by planning point ID")
    parser.add_argument("--serial", help="Filter by RRU serial number (partial match)")
    parser.add_argument("--sn-field", default="serial_number", help="Name of serial number field in wr_device_rru table (default: serial_number)")
    parser.add_argument("--limit", type=int, default=100, help="Maximum results to return (default: 100)")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    
    args = parser.parse_args()
    
    # Validate that at least one filter is provided if limit is high
    if args.limit > 1000 and not (args.rru_id or args.planning_id or args.serial):
        print("Warning: Large query without filters may impact performance.")
        confirm = input("Continue? (y/n): ")
        if confirm.lower() != 'y':
            return
    
    rru_data = find_rru_planning(
        rru_id=args.rru_id,
        planning_id=args.planning_id,
        serial_number=args.serial,
        sn_field=args.sn_field,
        limit=args.limit
    )
    
    if args.json:
        import json
        print(json.dumps(rru_data, indent=2, ensure_ascii=False))
    else:
        print(format_results(rru_data))

if __name__ == "__main__":
    main()