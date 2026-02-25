#!/usr/bin/env python3
"""
Check mandatory fields for wireless resource objects.
"""

import sys
import pandas as pd
from db_config import config

def check_mandatory_fields():
    """Check mandatory fields for key resource objects."""
    
    # Define mandatory fields for each object type
    mandatory_fields = {
        "wr_sync_rc_aau": ["aau_id", "installation_location", "device_model"],
        "wr_sync_rc_enodeb": ["enodeb_id", "device_type", "software_version"],
        "wr_sync_rc_eutrancell": ["cell_id", "enodeb_id", "cell_name"],
        "wr_sync_rc_rru": ["rru_id", "installation_location", "device_model"],
        "wr_space_site": ["site_id", "site_name", "longitude", "latitude", "address"],
        "wr_space_room": ["room_id", "room_name", "site_id", "room_type"],
    }
    
    try:
        import psycopg2
        conn = psycopg2.connect(**config.psycopg2_params())
        cursor = conn.cursor()
        
        results = []
        
        for table, fields in mandatory_fields.items():
            # Check if table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = %s AND table_name = %s
                )
            """, (config.schema, table))
            
            if not cursor.fetchone()[0]:
                print(f"Table {table} does not exist, skipping...")
                continue
            
            # Build query to check missing mandatory fields
            field_checks = []
            for field in fields:
                field_checks.append(f"{field} IS NULL")
            
            where_clause = " OR ".join(field_checks)
            
            query = f"""
                SELECT COUNT(*) as total_count,
                       COUNT(CASE WHEN {where_clause} THEN 1 END) as missing_count
                FROM {config.schema}.{table}
                WHERE lifecycle_status = '现网有业务'
            """
            
            cursor.execute(query)
            total_count, missing_count = cursor.fetchone()
            
            if total_count > 0:
                missing_percentage = (missing_count / total_count) * 100
            else:
                missing_percentage = 0
            
            results.append({
                "table": table,
                "total_records": total_count,
                "missing_mandatory": missing_count,
                "missing_percentage": round(missing_percentage, 2)
            })
        
        # Print results
        print("Mandatory Field Check Results")
        print("=" * 60)
        for result in results:
            print(f"\nTable: {result['table']}")
            print(f"  Total records: {result['total_records']}")
            print(f"  Records missing mandatory fields: {result['missing_mandatory']}")
            print(f"  Percentage missing: {result['missing_percentage']}%")
            
            if result['missing_mandatory'] > 0:
                print(f"  STATUS: FAIL - {result['missing_mandatory']} records need attention")
            else:
                print(f"  STATUS: PASS")
        
        # Generate summary
        total_missing = sum(r['missing_mandatory'] for r in results)
        total_records = sum(r['total_records'] for r in results)
        
        print("\n" + "=" * 60)
        print("SUMMARY")
        print(f"Total records checked: {total_records}")
        print(f"Total records with missing mandatory fields: {total_missing}")
        
        if total_missing > 0:
            print("\nACTION REQUIRED: Investigate and fix missing mandatory fields.")
            sys.exit(1)
        else:
            print("\nSUCCESS: All mandatory fields are populated.")
            sys.exit(0)
            
    except ImportError:
        print("Error: psycopg2 not installed. Install with: pip install psycopg2-binary")
        sys.exit(1)
    except Exception as e:
        print(f"Error during check: {e}")
        sys.exit(1)

if __name__ == "__main__":
    check_mandatory_fields()