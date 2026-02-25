#!/usr/bin/env python3
"""
Test script to verify all imports work correctly.
Run this script to check for missing dependencies.
"""

import sys

def test_imports():
    """Test importing all modules."""
    modules_to_test = [
        ("db_config", "db_config"),
        ("check_mandatory_fields", "check_mandatory_fields"),
        ("validate_relationships", "validate_relationships"),
        ("generate_report", "generate_report"),
        ("generate_report_offline", "generate_report_offline"),
        ("find_cell_location", "find_cell_location"),
        ("find_rru_planning", "find_rru_planning"),
        ("audit_cell_associations", "audit_cell_associations"),
        ("workflow_demo", "workflow_demo"),
    ]
    
    print("Testing imports for wireless resource management scripts")
    print("=" * 60)
    
    all_passed = True
    
    for module_name, script_name in modules_to_test:
        try:
            __import__(script_name)
            print(f"✓ {module_name}: Import successful")
        except ImportError as e:
            print(f"✗ {module_name}: Import failed - {e}")
            all_passed = False
        except Exception as e:
            print(f"✗ {module_name}: Error - {e}")
            all_passed = False
    
    # Test optional dependencies
    print("\nTesting optional dependencies:")
    try:
        import psycopg2
        print("✓ psycopg2: Available for database operations")
    except ImportError:
        print("⚠ psycopg2: Not installed (required for database operations)")
        print("  Install with: pip install psycopg2-binary")
    
    try:
        import pandas
        print("✓ pandas: Available for offline analysis")
    except ImportError:
        print("⚠ pandas: Not installed (optional for offline analysis)")
    
    try:
        import sqlalchemy
        print("✓ sqlalchemy: Available for advanced database operations")
    except ImportError:
        print("⚠ sqlalchemy: Not installed (optional)")
    
    # Test configuration
    print("\nTesting configuration:")
    try:
        from db_config import config
        print(f"✓ Database config loaded")
        print(f"  Host: {config.host}, Database: {config.database}")
    except Exception as e:
        print(f"✗ Configuration error: {e}")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("SUCCESS: All core imports work correctly.")
        print("\nNext steps:")
        print("1. Configure database connection in db_config.py or use environment variables")
        print("2. Run: python check_mandatory_fields.py")
        print("3. Run: python find_cell_location.py 'test_cell_id'")
        print("4. Run: python workflow_demo.py 'test_cell_id'")
        return 0
    else:
        print("FAILURE: Some imports failed.")
        print("\nInstall missing dependencies:")
        print("  pip install psycopg2-binary pandas sqlalchemy")
        return 1

if __name__ == "__main__":
    sys.exit(test_imports())