import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from rich.console import Console
from src.config import SPREADSHEET_ID, SHEET_NAME

console = Console()

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def get_client(credentials_path: str):
    """Authenticates with Google Sheets."""
    creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client

def get_last_transaction_date(credentials_path: str) -> pd.Timestamp | None:
    """Retrieves the date of the last transaction/row in the sheet."""
    try:
        client = get_client(credentials_path)
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
        dates_col = sheet.col_values(1)
        
        # Iterate backwards to find the last valid date
        for val in reversed(dates_col):
            try:
                # Try parsing "MMM, YY" (e.g. "Oct, 23")
                return pd.to_datetime(val, format='%b, %y')
            except:
                continue
        return None
    except Exception as e:
        console.print(f"[red]Error fetching last date from sheet: {e}[/red]")
        import traceback
        traceback.print_exc()
        return None

def update_sheet(df: pd.DataFrame, credentials_path: str, override: bool = False):
    """
    Updates the Google Sheet with new monthly data.
    If override is True, overwrites existing rows for the matching month.
    """
    client = get_client(credentials_path)
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
    
    # 1. Map existing months to row indices
    dates_col = sheet.col_values(1)
    sheet_dates = {}
    
    for i, val in enumerate(dates_col):
        try:
            # Parse "MMM, YY" (e.g. "Oct, 23")
            dt = pd.to_datetime(val, format='%b, %y')
            sheet_dates[dt] = i + 1 # 1-based index
        except:
            continue
            
    # 2. Identify column range for categories
    header_row = sheet.row_values(1)
    try:
        # We assume the data columns start at "Bank, Legal, Tax"
        # and follow the order in SHEET_COLUMNS (or broadly the header order)
        start_col_idx = header_row.index("Bank, Legal, Tax") # 0-based index
    except ValueError:
        console.print("[red]Error: Could not find 'Bank, Legal, Tax' column in sheet headers.[/red]")
        return

    # 3. Process each row in the input DataFrame
    updates = []
    
    # Ensure df Month is datetime for comparison
    df = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df['Month']):
         df['Month'] = pd.to_datetime(df['Month'])

    for _, row in df.iterrows():
        month_dt = row['Month']
        month_str = month_dt.strftime('%b, %y')
        
        # Check if month exists
        # We need to handle potential day differences by normalizing to Month Start if needed, 
        # but the sheet parsing uses format='%b, %y' which defaults to Day 1.
        # Our df['Month'] is also typically Day 1.
        # Let's align on Year-Month comparison just in case.
        match_dt = None
        target_row = None
        
        for s_dt, s_row in sheet_dates.items():
            if s_dt.year == month_dt.year and s_dt.month == month_dt.month:
                match_dt = s_dt
                target_row = s_row
                break
        
        if match_dt:
            if not override:
                console.print(f"[yellow]Skipping {month_str} (already exists in row {target_row}). Use --override to update.[/yellow]")
                continue
            else:
                console.print(f"[bold cyan]Overwriting data for {month_str} at row {target_row}[/bold cyan]")
        else:
            # Append to end
            target_row = len(dates_col) + 1
            dates_col.append(month_str) # Update local list to prevent overwriting if multiple new rows
            
            # Add Date Update (Column A)
            updates.append({
                'range': f"{SHEET_NAME}!A{target_row}",
                'values': [[month_str]]
            })
            console.print(f"[green]Appending new data for {month_str} to row {target_row}[/green]")

        # Prepare Category Values
        # We match dataframe columns to sheet headers dynamically starting from start_col_idx
        
        # Iterate through sheet headers from start_col_idx
        # This ensures we respect the sheet's column order
        headers_slice = header_row[start_col_idx:]
        
        cat_values = []
        for col_name in headers_slice:
            if col_name in row:
                val = row[col_name]
                # Convert numpy types to native Python types
                if hasattr(val, 'item'):
                    val = val.item()
                cat_values.append(val)
            else:
                # If sheet has a column not in our DF, fill with 0? 
                # Or keep as empty string to not overwrite formulas if any (unlikely in data section)
                # But safer to put 0.0 for numeric columns.
                cat_values.append(0.0)
                
        # Calculate A1 notation for the category block
        start_letter = gspread.utils.rowcol_to_a1(target_row, start_col_idx + 1).replace(str(target_row), "")
        end_letter = gspread.utils.rowcol_to_a1(target_row, len(header_row)).replace(str(target_row), "")
        
        range_name = f"{SHEET_NAME}!{start_letter}{target_row}:{end_letter}{target_row}"
        
        # console.print(f"   Writing categories to {range_name}")
        updates.append({
            'range': range_name,
            'values': [cat_values]
        })

    # 4. Execute Batch Update
    if updates:
        try:
            spreadsheet = client.open_by_key(SPREADSHEET_ID)
            body = {
                'valueInputOption': 'USER_ENTERED',
                'data': updates
            }
            spreadsheet.values_batch_update(body)
            # console.print(f"[bold green]Successfully updated Google Sheet![/bold green]")
        except Exception as e:
            console.print(f"[bold red]Failed to update sheet: {e}[/bold red]")
    else:
        # If we skipped everything because override=False, we should probably clearly say so
        # handled by per-row logging
        pass
