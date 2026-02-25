#!/usr/bin/env python3
"""
Workflow demonstration for wireless resource management.
Combines cell location finding, planning information lookup, and data quality audit.
Run this script with a cell ID to get comprehensive information for troubleshooting.
"""

import argparse
import sys
import json

# Import functions from other scripts
try:
    from find_cell_location import find_cell_location
    from find_rru_planning import find_rru_planning
    from audit_cell_associations import audit_cell_associations
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure you're running from the scripts directory and all required scripts are present.")
    sys.exit(1)

def get_cell_workflow_info(cell_id, output_format="text"):
    """
    Get comprehensive workflow information for a cell.
    
    Args:
        cell_id: Cell ID to analyze
        output_format: 'text' or 'json'
    
    Returns:
        Dictionary with all collected information
    """
    results = {
        "cell_id": cell_id,
        "location": None,
        "planning": None,
        "audit": None,
        "summary": {}
    }
    
    print(f"Starting workflow analysis for cell: {cell_id}", file=sys.stderr)
    
    # Step 1: Find cell location
    print("  Step 1/3: Finding cell location...", file=sys.stderr)
    location = find_cell_location(cell_id)
    results["location"] = location
    
    # Step 2: Find planning information
    print("  Step 2/3: Looking up planning information...", file=sys.stderr)
    if location and location.get("device_id"):
        # Try to find planning info using device ID
        rru_data = find_rru_planning(rru_id=location.get("device_id"), limit=5)
        results["planning"] = rru_data
    else:
        # Try with cell ID directly
        # Note: find_rru_planning doesn't support cell ID directly, so we'll query differently
        # For now, we'll skip planning if no device ID found
        results["planning"] = None
    
    # Step 3: Audit cell associations
    print("  Step 3/3: Auditing cell associations...", file=sys.stderr)
    audit_data = audit_cell_associations(limit=100)
    # Filter for this specific cell
    if audit_data and audit_data.get("results"):
        cell_audit = None
        for result in audit_data["results"]:
            if result["cell_id"] == cell_id:
                cell_audit = result
                break
        results["audit"] = cell_audit
    results["audit_summary"] = audit_data.get("summary") if audit_data else None
    
    # Generate summary
    generate_summary(results)
    
    return results

def generate_summary(results):
    """Generate summary metrics and recommendations."""
    summary = {}
    
    # Location status
    if results["location"]:
        summary["location_found"] = True
        summary["device_type"] = results["location"].get("device_type")
        summary["device_id"] = results["location"].get("device_id")
        summary["coordinates"] = f"{results['location'].get('latitude')}, {results['location'].get('longitude')}"
    else:
        summary["location_found"] = False
    
    # Planning status
    if results["planning"] and results["planning"].get("results"):
        summary["planning_found"] = True
        planning_result = results["planning"]["results"][0] if results["planning"]["results"] else None
        if planning_result:
            summary["planning_point"] = planning_result.get("site_planning_name")
            summary["band"] = planning_result.get("band")
    else:
        summary["planning_found"] = False
    
    # Audit status
    if results["audit"]:
        summary["has_associations"] = results["audit"]["total_associations"] > 0
        summary["association_count"] = results["audit"]["total_associations"]
        summary["association_status"] = results["audit"]["association_status"]
    
    # Overall assessment
    if summary.get("location_found") and summary.get("has_associations", True):
        summary["data_quality"] = "GOOD"
        summary["recommendation"] = "Cell data appears complete. Focus on physical equipment if experiencing issues."
    elif not summary.get("location_found"):
        summary["data_quality"] = "POOR"
        summary["recommendation"] = "Cell location not found. Check device associations in mapping tables."
    elif not summary.get("has_associations", False):
        summary["data_quality"] = "WARNING"
        summary["recommendation"] = "Cell lacks device associations. May affect location accuracy."
    else:
        summary["data_quality"] = "UNKNOWN"
    
    results["summary"] = summary

def format_workflow_results(results, output_format="text"):
    """Format workflow results for display."""
    if output_format == "json":
        # Convert non-serializable objects to strings
        json_safe = {}
        for key, value in results.items():
            if isinstance(value, dict):
                json_safe[key] = {}
                for k, v in value.items():
                    if hasattr(v, '__dict__'):
                        json_safe[key][k] = str(v)
                    else:
                        json_safe[key][k] = v
            else:
                json_safe[key] = value
        return json.dumps(json_safe, indent=2, ensure_ascii=False)
    
    # Text format
    output = []
    cell_id = results["cell_id"]
    
    output.append("=" * 80)
    output.append(f"WIRELESS RESOURCE WORKFLOW ANALYSIS")
    output.append(f"Cell ID: {cell_id}")
    output.append("=" * 80)
    output.append("")
    
    # Location section
    output.append("1. LOCATION INFORMATION")
    output.append("-" * 40)
    if results["location"]:
        loc = results["location"]
        output.append(f"   Cell Name: {loc.get('cellname', 'N/A')}")
        output.append(f"   Network: {loc.get('network', 'N/A')}")
        output.append(f"   Status: {loc.get('life_cycle_status', 'N/A')}")
        output.append(f"   VIP Level: {loc.get('vip_level', 'N/A')}")
        output.append("")
        output.append(f"   Device Association:")
        output.append(f"     Type: {loc.get('device_type', 'N/A')}")
        output.append(f"     ID: {loc.get('device_id', 'N/A')}")
        output.append("")
        output.append(f"   Physical Location:")
        output.append(f"     Room: {loc.get('room_name', 'N/A')}")
        output.append(f"     Station: {loc.get('station_name', 'N/A')}")
        output.append(f"     City/Area: {loc.get('city', 'N/A')}/{loc.get('area', 'N/A')}")
        output.append(f"     Coordinates: {loc.get('latitude', 'N/A')}, {loc.get('longitude', 'N/A')}")
        output.append(f"     Address: {loc.get('address', 'N/A')}")
    else:
        output.append("   No location information found.")
        output.append("   Cell may not exist or may have no device associations.")
    output.append("")
    
    # Planning section
    output.append("2. PLANNING INFORMATION")
    output.append("-" * 40)
    if results["planning"] and results["planning"].get("results"):
        planning = results["planning"]["results"][0]  # First matching result
        output.append(f"   Planning Point: {planning.get('site_planning_name', 'N/A')}")
        output.append(f"   Planning Code: {planning.get('site_planning_code', 'N/A')}")
        output.append(f"   Band: {planning.get('band', 'N/A')}")
        output.append(f"   Station Type: {planning.get('station_type', 'N/A')}")
        output.append(f"   Coverage Type: {planning.get('cover_type', 'N/A')}")
        output.append(f"   Network Type: {planning.get('network_type', 'N/A')}")
        output.append(f"   Planned Coordinates: {planning.get('planned_latitude', 'N/A')}, {planning.get('planned_longitude', 'N/A')}")
        output.append(f"   Planned Address: {planning.get('planned_address', 'N/A')}")
        
        # Planning summary
        if results["planning"].get("summary"):
            summ = results["planning"]["summary"]
            output.append("")
            output.append(f"   Planning Coverage: {summ.get('planning_coverage_rate', 0):.2f}% of RRUs have planning associations")
    else:
        output.append("   No planning information found.")
        output.append("   RRU may not be associated with a planning point, or cell may not have RRU association.")
    output.append("")
    
    # Audit section
    output.append("3. DATA QUALITY AUDIT")
    output.append("-" * 40)
    if results["audit"]:
        audit = results["audit"]
        output.append(f"   Device Associations: {audit.get('total_associations', 0)}")
        assoc_types = []
        if audit.get("has_rru"): assoc_types.append("RRU")
        if audit.get("has_aau"): assoc_types.append("AAU")
        if audit.get("has_antenna"): assoc_types.append("Antenna")
        if audit.get("has_wids"): assoc_types.append("WIDS")
        output.append(f"   Types: {', '.join(assoc_types) if assoc_types else 'None'}")
        output.append(f"   Status: {audit.get('association_status', 'N/A')}")
        output.append(f"   Description: {audit.get('status_description', 'N/A')}")
    else:
        output.append("   Cell not found in audit results (may be filtered out).")
    
    if results["audit_summary"]:
        summ = results["audit_summary"]
        output.append("")
        output.append(f"   Overall Statistics:")
        output.append(f"     Cells audited: {summ.get('total_cells', 0):,}")
        output.append(f"     Association rate: {summ.get('association_rate', 0):.2f}%")
    output.append("")
    
    # Summary section
    output.append("4. SUMMARY & RECOMMENDATIONS")
    output.append("-" * 40)
    summary = results["summary"]
    
    output.append(f"   Data Quality: {summary.get('data_quality', 'UNKNOWN')}")
    output.append("")
    
    if summary.get("location_found"):
        output.append(f"   ✓ Location identified: {summary.get('device_type', 'N/A')} {summary.get('device_id', 'N/A')}")
    else:
        output.append(f"   ✗ Location not found")
    
    if summary.get("planning_found"):
        output.append(f"   ✓ Planning information available")
    else:
        output.append(f"   ⚠ Planning information missing")
    
    if summary.get("has_associations", False):
        output.append(f"   ✓ Device associations present ({summary.get('association_count', 0)})")
    elif "has_associations" in summary:
        output.append(f"   ✗ No device associations found")
    
    output.append("")
    output.append(f"   Recommendation: {summary.get('recommendation', 'Check data quality and associations.')}")
    output.append("")
    
    # Next steps
    output.append("5. NEXT STEPS")
    output.append("-" * 40)
    output.append("   1. If location is missing: Check wr_map_*_cell tables for associations")
    output.append("   2. If planning is missing: Verify ac_access_batch_rel_rs entries")
    output.append("   3. If audit shows issues: Review device configuration and mapping")
    output.append("   4. For performance issues: Inspect physical equipment at location")
    output.append("   5. Update records if discrepancies found")
    output.append("")
    
    output.append("=" * 80)
    output.append("Workflow analysis complete. Use this information for troubleshooting.")
    output.append("=" * 80)
    
    return "\n".join(output)

def main():
    parser = argparse.ArgumentParser(description="Workflow demonstration for wireless resource management")
    parser.add_argument("cell_id", help="Cell ID to analyze")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress messages")
    
    args = parser.parse_args()
    
    output_format = "json" if args.json else "text"
    
    # Redirect stderr if quiet
    if args.quiet:
        import io
        sys.stderr = io.StringIO()
    
    results = get_cell_workflow_info(args.cell_id, output_format)
    
    print(format_workflow_results(results, output_format))

if __name__ == "__main__":
    main()