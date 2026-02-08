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
            
        # Fetch existing row data to check for formulas
        try:
            # We fetch the entire row to be safe/simple, or just the range we care about.
            # Fetching the whole row ensures we have data for all columns.
            existing_row_values = sheet.row_values(target_row, value_render_option='FORMULA')
        except Exception as e:
            # If row doesn't exist (new row), this might fail or return empty.
            # For new rows, it's empty, so no formulas to preserve.
            # console.print(f"[red]Warning: Could not fetch existing row {target_row} to check formulas: {e}[/red]")
            existing_row_values = []

        # Add Date Update (Column A) - ONLY if no formula exists
        # Column A is index 0 in existing_row_values
        has_date_formula = False
        if len(existing_row_values) > 0:
            val_a = existing_row_values[0]
            if isinstance(val_a, str) and val_a.startswith('='):
                has_date_formula = True
                
        if not has_date_formula:
            # Only update date if we are appending a new row OR overriding an existing value (not formula)
            # If match_dt is True, we are overriding. If match_dt is False, we are appending.
            # In both cases, if there is NO formula, we write/overwrite the date.
            # Wait, if match_dt is True (existing row), do we rewrite the date? 
            # Usually strict override would, but here we want to preserve formula.
            # So yes, if no formula, we write the date (which effectively ensures it matches format or corrects it).
            
            # If it's a new row (match_dt is False), existing_row_values is empty, so has_date_formula is False.
            # So we write the date. Correct.
            
            updates.append({
                'range': f"{SHEET_NAME}!A{target_row}",
                'values': [[month_str]]
            })
            if not match_dt:
                console.print(f"[green]Appending new data for {month_str} to row {target_row}[/green]")
        else:
            if not match_dt:
                 # This is weird. New row but has formula? Unlikely unless we appended to a pre-filled template row.
                 console.print(f"[yellow]Skipping Date write for {month_str} at row {target_row} (formula detected in Col A)[/yellow]")
            pass

        # Prepare Category Values
        # We match dataframe columns to sheet headers dynamically starting from start_col_idx
        
        # Iterate through sheet headers from start_col_idx
        # This ensures we respect the sheet's column order
        headers_slice = header_row[start_col_idx:]
        
        current_col_idx = start_col_idx # 0-based index of the column we are processing
        
        for col_name in headers_slice:
            current_col_idx_sheet = current_col_idx # 0-based index in sheet
            
            # Check existing value for formula
            # existing_row_values is 0-indexed.
            has_formula = False
            if current_col_idx_sheet < len(existing_row_values):
                cell_val = existing_row_values[current_col_idx_sheet]
                if isinstance(cell_val, str) and cell_val.startswith('='):
                    has_formula = True
            
            if has_formula:
                # console.print(f"Skipping {col_name} at row {target_row} (formula detected)")
                pass
            else:
                if col_name in row:
                    val = row[col_name]
                    # Convert numpy types to native Python types
                    if hasattr(val, 'item'):
                        val = val.item()
                else:
                    # If sheet has a column not in our DF, fill with 0? 
                    # But safer to put 0.0 for numeric columns.
                    val = 0.0
                
                # Update specific cell
                cell_a1 = gspread.utils.rowcol_to_a1(target_row, current_col_idx + 1)
                updates.append({
                    'range': f"{SHEET_NAME}!{cell_a1}",
                    'values': [[val]]
                })
            
            current_col_idx += 1

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

def fetch_month_data(credentials_path: str, target_month: pd.Period) -> dict | None:
    """
    Fetches the data row for a specific month from the sheet.
    Returns a dictionary of {Category: Amount} or None if not found.
    """
    try:
        client = get_client(credentials_path)
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
        
        # 1. Find the row
        dates_col = sheet.col_values(1)
        target_row_idx = None
        
        for i, val in enumerate(dates_col):
            try:
                dt = pd.to_datetime(val, format='%b, %y')
                if dt.year == target_month.year and dt.month == target_month.month:
                    target_row_idx = i + 1
                    break
            except:
                continue
                
        if not target_row_idx:
            return None
            
        # 2. Read the row
        row_values = sheet.row_values(target_row_idx)
        header_row = sheet.row_values(1)
        
        # Map headers to values
        data = {}
        for i, header in enumerate(header_row):
            if i < len(row_values):
                val = row_values[i]
                # Try to clean numeric values
                try:
                    # Remove currency symbols etc if needed, but gspread usually returns raw values or formatted strings
                    # We want float
                    if isinstance(val, str):
                        val = val.replace(',', '').replace('£', '')
                        if val == '': val = 0.0
                    data[header] = float(val)
                except:
                    data[header] = val
            else:
                data[header] = 0.0
                
        return data
        
    except Exception as e:
        console.print(f"[red]Error fetching data from sheet: {e}[/red]")
        return None
