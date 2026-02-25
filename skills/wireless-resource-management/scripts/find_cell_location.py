#!/usr/bin/env python3
"""
Find physical location of a wireless cell by tracing through device associations.
Supports 2G (GSM), 4G (LTE), and 5G (NR) cells.
"""

import argparse
import sys
from db_config import config

def find_cell_location(cell_id):
    """
    Find the physical location of a cell by tracing through device associations.
    
    Args:
        cell_id: The cell ID to locate (can be GSM cell ID, EUTRAN cell ID, or NR cell ID)
    
    Returns:
        Dictionary with location information or None if not found
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
        
        # Query to find cell location through device associations
        # This follows the pattern from "日常用-综合小区工参.sql"
        query = """
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
                station.address,
                dl.life_cycle_status,
                dv.vip_level
            FROM (
                -- Try to find cell in all network types
                SELECT cell_id, cellname, '2G' as network, site_id
                FROM npas.wr_logic_gsmcell 
                WHERE cell_id = %s AND is_del = false
                UNION ALL
                SELECT eutrancell_id as cell_id, eutrancell_name as cellname, '4G' as network, logic_enodeb_id as site_id
                FROM npas.wr_logic_eutrancell 
                WHERE eutrancell_id = %s AND is_del = false
                UNION ALL
                SELECT nrcell_id as cell_id, nrcell_name as cellname, '5G' as network, gnodeb_id as site_id
                FROM npas.wr_logic_nrcell 
                WHERE nrcell_id = %s AND is_del = false
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
                
                UNION ALL
                
                -- Fallback: try to get room from station if no device association found
                SELECT 'Station' as device_type, cell.site_id as device_id, room.room_id
                FROM npas.wr_space_room room
                WHERE room.station_id = cell.site_id AND room.is_del = false
                LIMIT 1
            ) device
            LEFT JOIN npas.wr_space_room room ON room.room_id = device.room_id
            LEFT JOIN npas.wr_space_station station ON room.station_id = station.station_id
            LEFT JOIN npas.dim_lifecyclestatus dl ON (
                -- Get lifecycle status from appropriate cell table
                SELECT life_cycle_status_key FROM (
                    SELECT life_cycle_status_key FROM npas.wr_logic_gsmcell WHERE cell_id = %s AND is_del = false
                    UNION ALL
                    SELECT life_cycle_status_key FROM npas.wr_logic_eutrancell WHERE eutrancell_id = %s AND is_del = false
                    UNION ALL
                    SELECT life_cycle_status_key FROM npas.wr_logic_nrcell WHERE nrcell_id = %s AND is_del = false
                ) status LIMIT 1
            ) ON true
            LEFT JOIN npas.dim_viplevel dv ON (
                -- Get VIP level from appropriate cell table
                SELECT vip_level_key FROM (
                    SELECT vip_level_key FROM npas.wr_logic_gsmcell WHERE cell_id = %s AND is_del = false
                    UNION ALL
                    SELECT vip_level_key FROM npas.wr_logic_eutrancell WHERE eutrancell_id = %s AND is_del = false
                    UNION ALL
                    SELECT vip_level_key FROM npas.wr_logic_nrcell WHERE nrcell_id = %s AND is_del = false
                ) vip LIMIT 1
            ) ON true
            WHERE cell.cell_id IS NOT NULL
            LIMIT 1;
        """
        
        # Execute with cell_id repeated for all placeholders
        params = [cell_id] * 9  # 9 placeholders in the query
        cursor.execute(query, params)
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return dict(result) if result else None
        
    except Exception as e:
        print(f"Database error: {e}")
        return None

def format_location_info(location):
    """Format location information for display."""
    if not location:
        return "Cell not found or no location information available."
    
    output = []
    output.append(f"Cell Information:")
    output.append(f"  Cell ID: {location.get('cell_id', 'N/A')}")
    output.append(f"  Cell Name: {location.get('cellname', 'N/A')}")
    output.append(f"  Network: {location.get('network', 'N/A')}")
    output.append(f"  Status: {location.get('life_cycle_status', 'N/A')}")
    output.append(f"  VIP Level: {location.get('vip_level', 'N/A')}")
    output.append("")
    output.append(f"Device Association:")
    output.append(f"  Device Type: {location.get('device_type', 'N/A')}")
    output.append(f"  Device ID: {location.get('device_id', 'N/A')}")
    output.append("")
    output.append(f"Location:")
    output.append(f"  Room: {location.get('room_name', 'N/A')}")
    output.append(f"  Station: {location.get('station_name', 'N/A')}")
    output.append(f"  City/Area: {location.get('city', 'N/A')}/{location.get('area', 'N/A')}")
    output.append(f"  Coordinates: {location.get('latitude', 'N/A')}, {location.get('longitude', 'N/A')}")
    output.append(f"  Address: {location.get('address', 'N/A')}")
    
    return "\n".join(output)

def main():
    parser = argparse.ArgumentParser(description="Find physical location of a wireless cell")
    parser.add_argument("cell_id", help="Cell ID to locate")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    
    args = parser.parse_args()
    
    location = find_cell_location(args.cell_id)
    
    if args.json:
        import json
        if location:
            print(json.dumps(location, indent=2, ensure_ascii=False))
        else:
            print(json.dumps({"error": "Cell not found"}))
    else:
        print(format_location_info(location))

if __name__ == "__main__":
    main()