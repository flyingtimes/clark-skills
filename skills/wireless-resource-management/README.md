# Wireless Resource Management Skill

This skill provides comprehensive tools and documentation for managing wireless base station databases, designed specifically for telecom engineers working with provincial wireless network resource management systems.

## What's Included

### Documentation
- **SKILL.md** - Main skill documentation and overview
- **references/** - Detailed reference materials
  - `resource-model.md` - Resource object definitions
  - `table-dictionary.md` - Database table structures
  - `audit-rules.md` - Data quality audit rules
  - `query-examples.md` - SQL query examples (including extensive materialized view queries for business scenarios)
  - `quick-reference.md` - Quick reference for daily operations
  - `tutorial.md` - Step-by-step tutorial for cell troubleshooting
  - `process-guide.md` - Operational process guidance
  - `security.md` - Security best practices
  - `api-service-example.md` - API implementation examples

### Python Scripts
- **`db_config.py`** - Database connection configuration
- **`check_mandatory_fields.py`** - Validate mandatory field completeness
- **`validate_relationships.py`** - Check referential integrity
- **`generate_report.py`** - Generate data quality reports
- **`generate_report_offline.py`** - Offline report generation
- **`find_cell_location.py`** - Trace cell location through device associations
- **`find_rru_planning.py`** - Find RRU serial numbers and planning point associations (traditional joins)
- **`find_rru_planning_mv.py`** - Find RRU serial numbers using materialized view (recommended)
- **`audit_cell_associations.py`** - Audit cell device associations
- **`workflow_demo.py`** - Combined workflow for cell troubleshooting

### Assets
- Example SQL scripts and templates
- Configuration examples

## Key Features

1. **Comprehensive Domain Knowledge**: Covers wireless resource management concepts, distributed deployment architecture, and enumeration field systems
2. **Practical Scripts**: Ready-to-use Python scripts for common operations
 3. **Query Examples**: Real-world SQL queries based on actual telecom database schemas, including extensive materialized view queries for business scenarios like fault troubleshooting, capacity planning, and network evolution analysis
4. **Materialized View Integration**: Pre-joined `mv_logic_element_device_room_station` view for simplified queries and faster analysis
5. **Data Quality Framework**: Audit rules and validation scripts for maintaining data integrity
6. **Deployment Flexibility**: Can be used as CLI tools, API services, or integrated into existing systems

## Quick Start

1. Review the `SKILL.md` file for an overview
2. Check `references/quick-reference.md` for essential information
3. Configure database connection in `scripts/db_config.py`
4. Run data quality checks: `python scripts/check_mandatory_fields.py`
5. Try the workflow demo: `python scripts/workflow_demo.py "cell_id"`

## Database Schema

The skill is designed for wireless resource databases with tables like:
- `wr_logic_eutrancell`, `wr_logic_nrcell`, `wr_logic_gsmcell` - Cell tables
- `wr_logic_enodeb`, `wr_logic_gnodeb` - Base station tables
- `wr_device_bbu`, `wr_device_rru`, `wr_device_aau` - Device tables
- `mv_logic_element_device_room_station` - Materialized view integrating cells, devices, rooms, and stations
- `wr_space_room`, `wr_space_station` - Location tables
- `dim_*` tables - Dimension tables for enumeration values

## Use Cases

- **Cell Troubleshooting**: Locate physical equipment for problematic cells
- **Data Quality Audits**: Regular validation of database integrity
- **Report Generation**: Automated generation of quality and inventory reports
- **Operational Support**: Guidance for data entry, modification, and decommissioning
- **Training**: Reference materials for new telecom engineers

## Prerequisites

- Python 3.8+ with psycopg2 for database access
- PostgreSQL database with wireless resource data (or use offline mode)
- Basic understanding of wireless network architecture

## License

This skill is provided for educational and professional use within telecom organizations. Refer to your organization's policies for usage guidelines.