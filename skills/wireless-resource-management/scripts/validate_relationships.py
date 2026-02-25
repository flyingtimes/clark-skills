#!/usr/bin/env python3
"""
Validate relationships between wireless resource objects.
"""

import sys
from db_config import config

def validate_relationships():
    """Check referential integrity between related tables."""
    
    # Define relationships to validate
    relationships = [
        {
            "name": "Cells referencing ENODEB",
            "child_table": "wr_sync_rc_eutrancell",
            "child_key": "enodeb_id",
            "parent_table": "wr_sync_rc_enodeb",
            "parent_key": "enodeb_id"
        },
        {
            "name": "RRUs referencing cells",
            "child_table": "wr_sync_rc_rru_cell",
            "child_key": "cell_id",
            "parent_table": "wr_sync_rc_eutrancell",
            "parent_key": "cell_id"
        },
        {
            "name": "Antennas referencing RRUs",
            "child_table": "wr_sync_rc_ant",
            "child_key": "rru_id",
            "parent_table": "wr_sync_rc_rru",
            "parent_key": "rru_id"
        },
        {
            "name": "Rooms referencing sites",
            "child_table": "wr_space_room",
            "child_key": "site_id",
            "parent_table": "wr_space_site",
            "parent_key": "site_id"
        },
        {
            "name": "ENODEBs referencing rooms",
            "child_table": "wr_sync_rc_enodeb",
            "child_key": "room_id",
            "parent_table": "wr_space_room",
            "parent_key": "room_id"
        }
    ]
    
    try:
        import psycopg2
        conn = psycopg2.connect(**config.psycopg2_params())
        cursor = conn.cursor()
        
        print("Relationship Validation Results")
        print("=" * 60)
        
        all_valid = True
        
        for rel in relationships:
            # Check if tables exist
            for table in [rel["child_table"], rel["parent_table"]]:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = %s AND table_name = %s
                    )
                """, (config.schema, table))
                
                if not cursor.fetchone()[0]:
                    print(f"\nTable {table} does not exist, skipping relationship: {rel['name']}")
                    continue
            
            # Check for orphaned child records
            query = f"""
                SELECT COUNT(*)
                FROM {config.schema}.{rel["child_table"]} c
                LEFT JOIN {config.schema}.{rel["parent_table"]} p 
                  ON c.{rel["child_key"]} = p.{rel["parent_key"]}
                WHERE p.{rel["parent_key"]} IS NULL
                  AND c.{rel["child_key"]} IS NOT NULL
            """
            
            cursor.execute(query)
            orphan_count = cursor.fetchone()[0]
            
            # Get total child records for context
            cursor.execute(f"SELECT COUNT(*) FROM {config.schema}.{rel['child_table']}")
            total_child = cursor.fetchone()[0]
            
            if orphan_count > 0:
                status = "FAIL"
                all_valid = False
            else:
                status = "PASS"
            
            print(f"\nRelationship: {rel['name']}")
            print(f"  Child table: {rel['child_table']}.{rel['child_key']}")
            print(f"  Parent table: {rel['parent_table']}.{rel['parent_key']}")
            print(f"  Total child records: {total_child}")
            print(f"  Orphaned records: {orphan_count}")
            print(f"  Status: {status}")
            
            if orphan_count > 0:
                # Get sample orphaned records
                sample_query = f"""
                    SELECT c.{rel["child_key"]}
                    FROM {config.schema}.{rel["child_table"]} c
                    LEFT JOIN {config.schema}.{rel["parent_table"]} p 
                      ON c.{rel["child_key"]} = p.{rel["parent_key"]}
                    WHERE p.{rel["parent_key"]} IS NULL
                      AND c.{rel["child_key"]} IS NOT NULL
                    LIMIT 5
                """
                cursor.execute(sample_query)
                orphans = cursor.fetchall()
                
                if orphans:
                    orphan_ids = [str(o[0]) for o in orphans]
                    print(f"  Sample orphan IDs: {', '.join(orphan_ids)}")
                    if len(orphans) == 5:
                        print(f"  (showing 5 of {orphan_count} orphans)")
        
        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        
        if all_valid:
            print("SUCCESS: All relationships are valid.")
            sys.exit(0)
        else:
            print("FAILURE: Some relationships have orphaned records.")
            print("\nACTION REQUIRED:")
            print("1. Investigate orphaned records")
            print("2. Either fix foreign key references")
            print("3. Or remove orphaned records if appropriate")
            sys.exit(1)
            
    except ImportError:
        print("Error: psycopg2 not installed. Install with: pip install psycopg2-binary")
        sys.exit(1)
    except Exception as e:
        print(f"Error during validation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    validate_relationships()