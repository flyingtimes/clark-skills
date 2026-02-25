# API Service Implementation Examples

## Overview

This document provides examples of implementing the wireless resource management functionality as API services. These examples can serve as starting points for building standalone applications, web services, or integration components.

## Architecture Options

### Option 1: REST API Service (FastAPI)

A modern, asynchronous REST API using FastAPI with PostgreSQL backend.

#### Project Structure
```
wireless-api/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application
│   ├── database.py      # Database connection pool
│   ├── models.py        # Pydantic models
│   ├── crud.py          # CRUD operations
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── sites.py     # Site-related endpoints
│   │   ├── cells.py     # Cell-related endpoints
│   │   └── reports.py   # Report generation endpoints
│   └── security.py      # Authentication and authorization
├── requirements.txt
└── config.yaml          # Configuration
```

#### FastAPI Application Example

`app/main.py`:
```python
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from typing import Optional
import pandas as pd

from app.database import get_db
from app.routers import sites, cells, reports

app = FastAPI(
    title="Wireless Resource Management API",
    description="API for managing wireless base station resources",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(sites.router, prefix="/api/v1/sites", tags=["sites"])
app.include_router(cells.router, prefix="/api/v1/cells", tags=["cells"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])

@app.get("/")
async def root():
    return {"message": "Wireless Resource Management API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": pd.Timestamp.now().isoformat()}
```

#### Site Router Example

`app/routers/sites.py`:
```python
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

from app.database import get_db

router = APIRouter()

@router.get("/")
async def get_sites(
    city: Optional[str] = None,
    site_type: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db=Depends(get_db)
):
    """Get list of sites with optional filtering."""
    query = """
        SELECT 
          site_id, site_name, province, city, district,
          longitude, latitude, site_type, maintenance_type,
          vip_level, coverage_scenario
        FROM wr_space_site
        WHERE 1=1
    """
    params = []
    
    if city:
        query += " AND city = %s"
        params.append(city)
    
    if site_type:
        query += " AND site_type = %s"
        params.append(site_type)
    
    query += " ORDER BY site_id LIMIT %s OFFSET %s"
    params.extend([limit, offset])
    
    try:
        with db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            sites = cur.fetchall()
            return {"sites": sites, "count": len(sites)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/{site_id}")
async def get_site_details(site_id: str, db=Depends(get_db)):
    """Get detailed information for a specific site."""
    query = """
        SELECT 
          s.*,
          COUNT(DISTINCT c.cell_id) as cell_count,
          COUNT(DISTINCT e.enodeb_id) as enodeb_count
        FROM wr_space_site s
        LEFT JOIN wr_sync_rc_eutrancell c ON s.site_id = c.site_id
        LEFT JOIN wr_sync_rc_enodeb e ON s.site_id = e.site_id
        WHERE s.site_id = %s
        GROUP BY s.site_id
    """
    
    try:
        with db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, (site_id,))
            site = cur.fetchone()
            if not site:
                raise HTTPException(status_code=404, detail="Site not found")
            return site
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
```

#### Report Generation Endpoint

`app/routers/reports.py`:
```python
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import FileResponse
from typing import Optional
import tempfile
import os
import pandas as pd
from datetime import datetime

from app.database import get_db

router = APIRouter()

@router.get("/resource-summary")
async def generate_resource_summary(
    format: str = Query("html", regex="^(html|word|excel|json)$"),
    city: Optional[str] = None,
    db=Depends(get_db)
):
    """Generate resource summary report in specified format."""
    
    # Base query
    query = """
        SELECT 
          province, city, district,
          COUNT(DISTINCT site_id) as site_count,
          COUNT(DISTINCT cell_id) as cell_count,
          COUNT(DISTINCT enodeb_id) as enodeb_count,
          ROUND(AVG(longitude), 6) as avg_longitude,
          ROUND(AVG(latitude), 6) as avg_latitude
        FROM (
          SELECT 
            s.site_id, s.province, s.city, s.district,
            s.longitude, s.latitude,
            c.cell_id, e.enodeb_id
          FROM wr_space_site s
          LEFT JOIN wr_sync_rc_eutrancell c ON s.site_id = c.site_id
          LEFT JOIN wr_sync_rc_enodeb e ON s.site_id = e.site_id
          WHERE 1=1
    """
    params = []
    
    if city:
        query += " AND s.city = %s"
        params.append(city)
    
    query += """
        ) aggregated
        GROUP BY province, city, district
        ORDER BY province, city, district
    """
    
    try:
        with db.cursor() as cur:
            cur.execute(query, params)
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            
        df = pd.DataFrame(rows, columns=columns)
        
        # Generate report based on format
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{format}") as tmp:
            tmp_path = tmp.name
            
            if format == "excel":
                df.to_excel(tmp_path, index=False, engine='openpyxl')
                media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                filename = f"resource_summary_{timestamp}.xlsx"
                
            elif format == "html":
                html_content = df.to_html(index=False, classes='table table-striped')
                # Add basic styling
                styled_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Resource Summary Report</title>
                    <style>
                        table {{ border-collapse: collapse; width: 100%; }}
                        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                        th {{ background-color: #4CAF50; color: white; }}
                        tr:nth-child(even) {{ background-color: #f2f2f2; }}
                    </style>
                </head>
                <body>
                    <h1>Wireless Resource Summary</h1>
                    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    {html_content}
                </body>
                </html>
                """
                with open(tmp_path, 'w', encoding='utf-8') as f:
                    f.write(styled_html)
                media_type = "text/html"
                filename = f"resource_summary_{timestamp}.html"
                
            elif format == "word":
                # Using python-docx for Word document generation
                try:
                    from docx import Document
                    from docx.shared import Inches
                    
                    doc = Document()
                    doc.add_heading('Wireless Resource Summary', 0)
                    doc.add_paragraph(f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
                    
                    # Add table
                    table = doc.add_table(rows=len(df)+1, cols=len(df.columns))
                    table.style = 'LightShading-Accent1'
                    
                    # Header row
                    for col_idx, col_name in enumerate(df.columns):
                        table.cell(0, col_idx).text = str(col_name)
                    
                    # Data rows
                    for row_idx, row in df.iterrows():
                        for col_idx, col_name in enumerate(df.columns):
                            table.cell(row_idx+1, col_idx).text = str(row[col_name])
                    
                    doc.save(tmp_path)
                    media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    filename = f"resource_summary_{timestamp}.docx"
                except ImportError:
                    raise HTTPException(
                        status_code=500, 
                        detail="Word document generation requires python-docx package"
                    )
            
            else:  # json
                df.to_json(tmp_path, orient='records', indent=2)
                media_type = "application/json"
                filename = f"resource_summary_{timestamp}.json"
        
        return FileResponse(
            path=tmp_path,
            media_type=media_type,
            filename=filename,
            background=BackgroundTask(lambda: os.unlink(tmp_path))
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")
```

### Option 2: Flask Web Application

A simpler Flask-based web application with basic CRUD and reporting.

#### Flask Application Structure
```
wireless-web/
├── app.py
├── templates/
│   └── index.html
├── static/
│   └── style.css
├── requirements.txt
└── config.py
```

#### Flask App Example

`app.py`:
```python
from flask import Flask, render_template, request, jsonify, send_file
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from datetime import datetime
import tempfile
import os

app = Flask(__name__)

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'wireless_db'),
    'user': os.getenv('DB_USER', 'wireless_user'),
    'password': os.getenv('DB_PASSWORD', '')
}

def get_db_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/sites')
def get_sites():
    city = request.args.get('city', '')
    limit = request.args.get('limit', 100, type=int)
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    query = """
        SELECT site_id, site_name, province, city, district,
               longitude, latitude, site_type, maintenance_type
        FROM wr_space_site
        WHERE (%s = '' OR city = %s)
        LIMIT %s
    """
    cur.execute(query, (city, city, limit))
    sites = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return jsonify({'sites': sites})

@app.route('/api/reports/summary')
def download_summary():
    format = request.args.get('format', 'excel')
    
    conn = get_db_connection()
    query = """
        SELECT province, city, COUNT(*) as site_count,
               COUNT(DISTINCT cell_id) as cell_count
        FROM wr_space_site s
        LEFT JOIN wr_sync_rc_eutrancell c ON s.site_id = c.site_id
        GROUP BY province, city
        ORDER BY province, city
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if format == 'excel':
        output = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
        df.to_excel(output.name, index=False, engine='openpyxl')
        mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        filename = f'site_summary_{timestamp}.xlsx'
    
    elif format == 'html':
        output = tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w', encoding='utf-8')
        html = df.to_html(index=False, classes='table table-striped')
        output.write(f"<html><body>{html}</body></html>")
        output.close()
        mimetype = 'text/html'
        filename = f'site_summary_{timestamp}.html'
    
    elif format == 'word':
        try:
            from docx import Document
            output = tempfile.NamedTemporaryFile(delete=False, suffix='.docx')
            doc = Document()
            doc.add_heading('Site Summary Report', 0)
            
            table = doc.add_table(rows=len(df)+1, cols=len(df.columns))
            for col_idx, col_name in enumerate(df.columns):
                table.cell(0, col_idx).text = str(col_name)
            
            for row_idx, row in df.iterrows():
                for col_idx, col_name in enumerate(df.columns):
                    table.cell(row_idx+1, col_idx).text = str(row[col_name])
            
            doc.save(output.name)
            mimetype = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            filename = f'site_summary_{timestamp}.docx'
        except ImportError:
            return jsonify({'error': 'python-docx not installed'}), 500
    
    else:
        return jsonify({'error': 'Unsupported format'}), 400
    
    return send_file(
        output.name,
        mimetype=mimetype,
        as_attachment=True,
        download_name=filename
    )

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```

### Option 3: Scheduled Reporting Service

A service that runs periodic reports and sends them via email or uploads to a shared location.

#### Scheduled Service Example

`scheduled_reporter.py`:
```python
import schedule
import time
import pandas as pd
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import os
from db_config import config

def generate_daily_report():
    """Generate daily resource report."""
    conn = psycopg2.connect(**config.psycopg2_params())
    
    # Generate report data
    queries = {
        'site_summary': "SELECT ...",
        'data_quality': "SELECT ...",
        'equipment_status': "SELECT ..."
    }
    
    report_data = {}
    for name, query in queries.items():
        df = pd.read_sql_query(query, conn)
        report_data[name] = df
    
    conn.close()
    
    # Create Excel report
    timestamp = datetime.now().strftime("%Y%m%d")
    filename = f"wireless_report_{timestamp}.xlsx"
    
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        for name, df in report_data.items():
            df.to_excel(writer, sheet_name=name[:31], index=False)
    
    return filename

def send_report_email(filename, recipients):
    """Send report via email."""
    msg = MIMEMultipart()
    msg['Subject'] = f"Wireless Resource Daily Report - {datetime.now().strftime('%Y-%m-%d')}"
    msg['From'] = os.getenv('EMAIL_FROM')
    msg['To'] = ', '.join(recipients)
    
    body = f"Attached is the daily wireless resource report for {datetime.now().strftime('%Y-%m-%d')}."
    msg.attach(MIMEText(body, 'plain'))
    
    with open(filename, 'rb') as f:
        attachment = MIMEApplication(f.read(), _subtype="xlsx")
        attachment.add_header('Content-Disposition', 'attachment', filename=filename)
        msg.attach(attachment)
    
    # Send email
    with smtplib.SMTP(os.getenv('SMTP_SERVER'), os.getenv('SMTP_PORT')) as server:
        server.starttls()
        server.login(os.getenv('SMTP_USER'), os.getenv('SMTP_PASSWORD'))
        server.send_message(msg)

def daily_report_job():
    """Job to run daily report generation and distribution."""
    print(f"Running daily report job at {datetime.now()}")
    
    try:
        # Generate report
        report_file = generate_daily_report()
        
        # Send to recipients
        recipients = os.getenv('REPORT_RECIPIENTS', '').split(',')
        if recipients:
            send_report_email(report_file, recipients)
        
        # Upload to shared location (optional)
        # upload_to_sharepoint(report_file)
        
        print(f"Daily report completed: {report_file}")
        
    except Exception as e:
        print(f"Error in daily report job: {e}")
        # Send alert email about failure

# Schedule daily job at 8:00 AM
schedule.every().day.at("08:00").do(daily_report_job)

if __name__ == "__main__":
    print("Scheduled reporter started. Press Ctrl+C to exit.")
    # Run immediately for testing
    daily_report_job()
    
    while True:
        schedule.run_pending()
        time.sleep(60)
```

## Deployment Considerations

### Containerization (Docker)

Create a `Dockerfile` for the API service:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Configuration

Use environment variables for configuration:

```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=wireless_db
DB_USER=wireless_user
DB_PASSWORD=secure_password

# API Security
API_SECRET_KEY=your_secret_key
API_CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# Email (for reporting)
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
SMTP_USER=user@example.com
SMTP_PASSWORD=email_password
REPORT_RECIPIENTS=engineer1@example.com,engineer2@example.com
```

### Monitoring and Logging

- Implement logging with different levels (DEBUG, INFO, ERROR)
- Use structured logging (JSON format) for production
- Integrate with monitoring tools (Prometheus, Grafana)
- Set up health checks and readiness probes

## Next Steps

1. **Choose architecture** based on your requirements:
   - FastAPI for modern, high-performance APIs
   - Flask for simpler web applications
   - Scheduled service for automated reporting

2. **Implement authentication** using JWT tokens or OAuth2

3. **Add caching** for frequently accessed data (Redis)

4. **Implement rate limiting** to prevent abuse

5. **Create comprehensive documentation** using OpenAPI/Swagger

6. **Set up CI/CD pipeline** for automated testing and deployment

These examples provide a foundation for building wireless resource management services that can be integrated into existing workflows or used as standalone applications.