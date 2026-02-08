"""
FastAPI server for FIRE-AI web app.
Provides endpoints for analytics, CSV file listing, and transaction processing.
"""
import sys
from pathlib import Path

# Add cli directory to path for imports
CLI_DIR = Path(__file__).parent.parent / "cli"
sys.path.insert(0, str(CLI_DIR))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import pandas as pd
import os

app = FastAPI(title="FIRE-AI API", version="1.0.0")

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
CREDENTIALS_PATH = CLI_DIR / "resources" / "credentials.json"
CSV_DIR = CLI_DIR / "csv"
CONFIG_DIR = CLI_DIR / "config"


class ProcessRequest(BaseModel):
    csv_file: str
    month: Optional[int] = None # 1-12
    year: Optional[int] = None   # e.g., 2024
    mode: str   # "shadow" or "live"
    override: bool = False
    auto_date: bool = False


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/csv-files")
def list_csv_files():
    """List available CSV files in the csv/ directory, sorted by modification time (most recent first)."""
    if not CSV_DIR.exists():
        return {"files": [], "default": None}
    
    csv_files = []
    for f in CSV_DIR.glob("*.csv"):
        stat = f.stat()
        csv_files.append({
            "name": f.name,
            "path": str(f),
            "modified": stat.st_mtime
        })
    
    # Sort by modification time (most recent first)
    csv_files.sort(key=lambda x: x["modified"], reverse=True)
    
    default_file = csv_files[0]["name"] if csv_files else None
    
    return {
        "files": [f["name"] for f in csv_files],
        "default": default_file
    }


@app.get("/api/analytics")
def get_analytics():
    """Fetch last 12 months of data from Google Sheets for the dashboard chart."""
    try:
        from src.sheets_client import get_client
        from src.config import SPREADSHEET_ID, SHEET_NAME, SHEET_COLUMNS
        import re
        
        if not CREDENTIALS_PATH.exists():
            raise HTTPException(status_code=500, detail="Credentials file not found")
        
        client = get_client(str(CREDENTIALS_PATH))
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
        
        # Get headers and all values
        headers = sheet.row_values(1)
        all_values = sheet.get_all_values()
        
        if not all_values or len(all_values) < 2:
            return {"months": [], "categories": [], "averages": {}, "monthly_data": []}
        
        # Month pattern: "MMM, YY" (e.g. "May, 24")
        month_pattern = re.compile(r'^[A-Z][a-z]{2}, \d{2}$')
        
        # Parse rows with valid month data
        parsed_rows = []
        for row in all_values[1:]:  # Skip header row
            if row and len(row) > 0:
                month_val = row[0].strip() if row[0] else ""
                if month_pattern.match(month_val):
                    row_data = {"Month": month_val}
                    for i, header in enumerate(headers):
                        if i < len(row) and header:
                            val = row[i]
                            # Clean currency formatting
                            if isinstance(val, str):
                                val = val.replace('£', '').replace(',', '').strip()
                            try:
                                row_data[header] = float(val) if val else 0.0
                            except (ValueError, TypeError):
                                row_data[header] = 0.0
                    parsed_rows.append(row_data)
        
        if not parsed_rows:
            return {"months": [], "categories": [], "averages": {}, "monthly_data": []}
        
        # Take last 12 months
        recent_data = parsed_rows[-12:] if len(parsed_rows) > 12 else parsed_rows
        
        # Build response
        months = [row["Month"] for row in recent_data]
        
        # Calculate averages per category
        category_averages = {}
        for cat in SHEET_COLUMNS:
            values = [row.get(cat, 0) for row in recent_data]
            category_averages[cat] = round(sum(values) / len(values), 2) if values else 0
        
        # Also return monthly data for charts
        monthly_data = []
        for row in recent_data:
            month_entry = {"month": row["Month"]}
            for cat in SHEET_COLUMNS:
                month_entry[cat] = row.get(cat, 0)
            monthly_data.append(month_entry)
        
        # Calculate total spend per month for summary
        totals_per_month = []
        for row in recent_data:
            # Use "Totals" column if available, otherwise sum categories
            if "Totals" in row:
                totals_per_month.append({"month": row["Month"], "total": row["Totals"]})
            else:
                total = sum(row.get(cat, 0) for cat in SHEET_COLUMNS)
                totals_per_month.append({"month": row["Month"], "total": total})
        
        return {
            "months": months,
            "categories": SHEET_COLUMNS,
            "averages": category_averages,
            "monthly_data": monthly_data,
            "totals_per_month": totals_per_month
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/process")
def process_transactions(request: ProcessRequest):
    """Process transactions for a given month with shadow or live mode."""
    try:
        from src.data_loader import load_csv
        from src.processor import categorize_transactions, aggregate_categories
        from src.sheets_client import update_sheet, get_last_transaction_date
        from src.config import SHEET_COLUMNS
        import datetime
        
        # Validate CSV file
        csv_path = CSV_DIR / request.csv_file
        if not csv_path.exists():
            raise HTTPException(status_code=400, detail=f"CSV file not found: {request.csv_file}")
        
        # Load and process data
        df = load_csv(str(csv_path))
        processed_df = categorize_transactions(df)
        
        # Determine target period
        target_period = None
        detected_from_sheet = False
        
        if request.auto_date:
            # Auto-detect month logic
            try:
                if CREDENTIALS_PATH.exists():
                    last_date = get_last_transaction_date(str(CREDENTIALS_PATH))
                    if last_date:
                        next_month = last_date + pd.DateOffset(months=1)
                        target_period = pd.Period(next_month, freq='M')
                        detected_from_sheet = True
            except Exception:
                # Fallback silently or log
                pass
            
            # Fallback if sheet detection failed or no credentials
            if not target_period:
                # Default to previous month
                today = datetime.date.today()
                first = today.replace(day=1)
                prev_month = first - datetime.timedelta(days=1)
                target_period = pd.Period(prev_month, freq='M')
        else:
            # Manual date
            if request.year is None or request.month is None:
                raise HTTPException(status_code=400, detail="Year and Month are required when auto_date is False")
            target_period = pd.Period(year=request.year, month=request.month, freq='M')
        
        # Filter by period
        processed_df['MonthPeriod'] = processed_df['DATE'].dt.to_period('M')
        filtered_df = processed_df[processed_df['MonthPeriod'] == target_period].copy()
        
        if filtered_df.empty:
            if request.auto_date and detected_from_sheet:
                 # Strict check: If we expected a specific month from sheet history, it MUST be in the CSV.
                 raise HTTPException(
                     status_code=400, 
                     detail=f"The next logical month is {target_period} (based on Google Sheet history), "
                            f"but the CSV does not contain any transactions for this month. "
                            f"Please upload a CSV containing data for {target_period}."
                 )
            
            elif request.auto_date and not detected_from_sheet:
                 # Fallback logic: If we just guessed 'previous month' and failed, try latest in CSV
                 if not processed_df.empty:
                     max_date = processed_df['DATE'].max()
                     target_period = pd.Period(max_date, freq='M')
                     filtered_df = processed_df[processed_df['MonthPeriod'] == target_period].copy()
            
            # Re-check if still empty after fallback attempt
            if filtered_df.empty:
                return {
                    "success": False,
                    "message": f"No transactions found for {target_period}",
                    "data": []
                }
        
        # Aggregate
        aggregated_df = aggregate_categories(filtered_df)
        
        # Prepare response data
        result_data = []
        for _, row in aggregated_df.iterrows():
            row_dict = {"Month": row['Month'].strftime('%b %Y')}
            for col in aggregated_df.columns:
                if col != 'Month':
                    row_dict[col] = round(float(row[col]), 2)
            result_data.append(row_dict)
        
        # If live mode, update sheets
        if request.mode == "live":
            if not CREDENTIALS_PATH.exists():
                raise HTTPException(status_code=500, detail="Credentials file not found for live mode")
            
            cols_to_write = ['Month'] + SHEET_COLUMNS
            df_to_write = aggregated_df[cols_to_write].copy()
            update_sheet(df_to_write, str(CREDENTIALS_PATH), override=request.override)
            
            return {
                "success": True,
                "message": f"Successfully updated Google Sheets for {target_period}",
                "mode": "live",
                "transactions_count": len(filtered_df),
                "data": result_data
            }
        else:
            return {
                "success": True,
                "message": f"Shadow mode preview for {target_period}",
                "mode": "shadow",
                "transactions_count": len(filtered_df),
                "data": result_data
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
