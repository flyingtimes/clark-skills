#!/usr/bin/env python3
"""
Audit cell device associations for data quality.
Checks if cells have proper associations with RRUs, AAUs, antennas, or WIDS.
Based on audit rules from "合规率-合并.sql".
"""

import argparse
import sys
from db_config import config

def audit_cell_associations(network=None, limit=100):
    """
    Audit cell device associations.
    
    Args:
        network: Filter by network type ('2G', '4G', '5G', or None for all)
        limit: Maximum number of results to return
    
    Returns:
        List of dictionaries with audit results
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
        
        # Build network filter
        network_filter = ""
        if network == '2G':
            network_filter = "AND network = '2G'"
        elif network == '4G':
            network_filter = "AND network = '4G'"
        elif network == '5G':
            network_filter = "AND network = '5G'"
        
        # Query to find cells with missing or problematic device associations
        query = f"""
            WITH cell_data AS (
                -- 2G cells
                SELECT cell_id, cellname, '2G' as network, site_id,
                       life_cycle_status_key, vip_level_key
                FROM npas.wr_logic_gsmcell 
                WHERE is_del = false
                UNION ALL
                -- 4G cells
                SELECT eutrancell_id as cell_id, eutrancell_name as cellname, '4G' as network,
                       logic_enodeb_id as site_id, life_cycle_status_key, vip_level_key
                FROM npas.wr_logic_eutrancell 
                WHERE is_del = false
                UNION ALL
                -- 5G cells
                SELECT nrcell_id as cell_id, nrcell_name as cellname, '5G' as network,
                       gnodeb_id as site_id, life_cycle_status_key, vip_level_key
                FROM npas.wr_logic_nrcell 
                WHERE is_del = false
            ),
            device_associations AS (
                SELECT 
                    cd.cell_id,
                    cd.cellname,
                    cd.network,
                    cd.site_id,
                    -- Check for each device type association
                    MAX(CASE WHEN rc.rru_id IS NOT NULL THEN 1 ELSE 0 END) as has_rru,
                    MAX(CASE WHEN ac.aau_id IS NOT NULL THEN 1 ELSE 0 END) as has_aau,
                    MAX(CASE WHEN antc.ant_id IS NOT NULL THEN 1 ELSE 0 END) as has_antenna,
                    MAX(CASE WHEN wc.wids_id IS NOT NULL THEN 1 ELSE 0 END) as has_wids,
                    -- Count total associations
                    COUNT(DISTINCT rc.rru_id) + 
                    COUNT(DISTINCT ac.aau_id) + 
                    COUNT(DISTINCT antc.ant_id) + 
                    COUNT(DISTINCT wc.wids_id) as total_associations,
                    -- Get lifecycle status
                    dl.life_cycle_status,
                    dv.vip_level
                FROM cell_data cd
                LEFT JOIN npas.wr_map_rru_cell rc ON cd.cell_id = rc.logic_cell_id AND rc.is_del = false
                LEFT JOIN npas.wr_map_aau_cell ac ON cd.cell_id = ac.logic_cell_id AND ac.is_del = false
                LEFT JOIN npas.wr_map_ant_cell antc ON cd.cell_id = antc.logic_cell_id AND antc.is_del = false
                LEFT JOIN npas.wr_map_wids_cell wc ON cd.cell_id = wc.logic_cell_id AND wc.is_del = false
                LEFT JOIN npas.dim_lifecyclestatus dl ON cd.life_cycle_status_key = dl.life_cycle_status_key
                LEFT JOIN npas.dim_viplevel dv ON cd.vip_level_key = dv.vip_level_key
                WHERE 1=1 {network_filter}
                GROUP BY cd.cell_id, cd.cellname, cd.network, cd.site_id, dl.life_cycle_status, dv.vip_level
            )
            SELECT 
                cell_id,
                cellname,
                network,
                life_cycle_status,
                vip_level,
                has_rru,
                has_aau,
                has_antenna,
                has_wids,
                total_associations,
                CASE 
                    WHEN total_associations = 0 THEN 'NO_ASSOCIATION'
                    WHEN total_associations > 1 THEN 'MULTIPLE_ASSOCIATIONS'
                    ELSE 'SINGLE_ASSOCIATION'
                END as association_status,
                CASE 
                    WHEN total_associations = 0 THEN 'Missing device association'
                    WHEN total_associations > 1 THEN 'Multiple device associations (may be correct for carrier aggregation)'
                    ELSE 'OK'
                END as status_description
            FROM device_associations
            ORDER BY 
                total_associations ASC,
                CASE WHEN life_cycle_status = '现网有业务' THEN 1 ELSE 2 END,
                network
            LIMIT %s;
        """
        
        cursor.execute(query, (limit,))
        results = cursor.fetchall()
        
        # Get summary statistics
        summary_query = """
            SELECT 
                COUNT(*) as total_cells,
                COUNT(CASE WHEN total_associations = 0 THEN 1 END) as cells_without_association,
                COUNT(CASE WHEN total_associations > 0 THEN 1 END) as cells_with_association,
                COUNT(CASE WHEN total_associations > 1 THEN 1 END) as cells_with_multiple_associations,
                ROUND(100.0 * COUNT(CASE WHEN total_associations > 0 THEN 1 END) / COUNT(*), 2) as association_rate
            FROM (
                SELECT cell_id, 
                       COUNT(DISTINCT rc.rru_id) + 
                       COUNT(DISTINCT ac.aau_id) + 
                       COUNT(DISTINCT antc.ant_id) + 
                       COUNT(DISTINCT wc.wids_id) as total_associations
                FROM (
                    SELECT cell_id FROM npas.wr_logic_gsmcell WHERE is_del = false
                    UNION ALL SELECT eutrancell_id FROM npas.wr_logic_eutrancell WHERE is_del = false
                    UNION ALL SELECT nrcell_id FROM npas.wr_logic_nrcell WHERE is_del = false
                ) cells
                LEFT JOIN npas.wr_map_rru_cell rc ON cells.cell_id = rc.logic_cell_id AND rc.is_del = false
                LEFT JOIN npas.wr_map_aau_cell ac ON cells.cell_id = ac.logic_cell_id AND ac.is_del = false
                LEFT JOIN npas.wr_map_ant_cell antc ON cells.cell_id = antc.logic_cell_id AND antc.is_del = false
                LEFT JOIN npas.wr_map_wids_cell wc ON cells.cell_id = wc.logic_cell_id AND wc.is_del = false
                GROUP BY cells.cell_id
            ) association_counts;
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
        return None

def format_results(audit_data, output_format="text"):
    """Format audit results for display."""
    if not audit_data:
        return "No audit data available."
    
    if output_format == "json":
        import json
        return json.dumps(audit_data, indent=2, ensure_ascii=False)
    
    results = audit_data["results"]
    summary = audit_data["summary"]
    
    output = []
    output.append("CELL DEVICE ASSOCIATION AUDIT")
    output.append("=" * 80)
    output.append("")
    
    # Summary section
    output.append("SUMMARY")
    output.append("-" * 40)
    output.append(f"Total cells audited: {summary.get('total_cells', 0):,}")
    output.append(f"Cells without device association: {summary.get('cells_without_association', 0):,}")
    output.append(f"Cells with association: {summary.get('cells_with_association', 0):,}")
    output.append(f"Cells with multiple associations: {summary.get('cells_with_multiple_associations', 0):,}")
    output.append(f"Association rate: {summary.get('association_rate', 0):.2f}%")
    output.append("")
    
    # Detailed results
    output.append("DETAILED RESULTS (showing cells with issues)")
    output.append("-" * 40)
    
    if not results:
        output.append("No issues found.")
    else:
        # Group by issue type
        no_assoc = [r for r in results if r["total_associations"] == 0]
        multi_assoc = [r for r in results if r["total_associations"] > 1]
        
        if no_assoc:
            output.append("\nCELLS WITHOUT DEVICE ASSOCIATIONS:")
            output.append("-" * 30)
            for cell in no_assoc[:10]:  # Show first 10
                output.append(f"  {cell['cell_id']} ({cell['network']}): {cell['cellname']} - Status: {cell['life_cycle_status']}")
            if len(no_assoc) > 10:
                output.append(f"  ... and {len(no_assoc) - 10} more")
        
        if multi_assoc:
            output.append("\nCELLS WITH MULTIPLE DEVICE ASSOCIATIONS:")
            output.append("-" * 40)
            for cell in multi_assoc[:10]:
                assoc_types = []
                if cell["has_rru"]: assoc_types.append("RRU")
                if cell["has_aau"]: assoc_types.append("AAU")
                if cell["has_antenna"]: assoc_types.append("Antenna")
                if cell["has_wids"]: assoc_types.append("WIDS")
                output.append(f"  {cell['cell_id']} ({cell['network']}): {cell['cellname']} - Associations: {', '.join(assoc_types)}")
            if len(multi_assoc) > 10:
                output.append(f"  ... and {len(multi_assoc) - 10} more")
        
        # Show a few OK cells for reference
        ok_cells = [r for r in results if r["total_associations"] == 1]
        if ok_cells and (no_assoc or multi_assoc):
            output.append("\nSAMPLE OF CELLS WITH PROPER ASSOCIATIONS:")
            output.append("-" * 45)
            for cell in ok_cells[:3]:
                assoc_type = "RRU" if cell["has_rru"] else "AAU" if cell["has_aau"] else "Antenna" if cell["has_antenna"] else "WIDS"
                output.append(f"  {cell['cell_id']} ({cell['network']}): {cell['cellname']} - Associated with: {assoc_type}")
    
    output.append("")
    output.append("RECOMMENDATIONS:")
    output.append("-" * 40)
    output.append("1. Cells without associations: Check mapping tables or device configuration")
    output.append("2. Cells with multiple associations: Verify if correct (e.g., carrier aggregation)")
    output.append("3. For cells '现网有业务' (in-service), associations are mandatory")
    output.append("4. Regular audit ensures data quality for network operations")
    
    return "\n".join(output)

def main():
    parser = argparse.ArgumentParser(description="Audit cell device associations")
    parser.add_argument("--network", choices=['2G', '4G', '5G'], help="Filter by network type")
    parser.add_argument("--limit", type=int, default=100, help="Maximum results to return (default: 100)")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    
    args = parser.parse_args()
    
    audit_data = audit_cell_associations(args.network, args.limit)
    
    if args.json:
        import json
        print(json.dumps(audit_data, indent=2, ensure_ascii=False))
    else:
        print(format_results(audit_data))

if __name__ == "__main__":
    main()