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

def update_sheet(df: pd.DataFrame, credentials_path: str):
    """
    Updates the Google Sheet with new monthly data.
    """
    client = get_client(credentials_path)
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
    
    # 1. Find the last filled row based on Column A (Month)
    # Get all values in Column A
    dates_col = sheet.col_values(1)
    last_row_index = len(dates_col) # 1-based index of the last row
    
    # 2. Determine the last month present in the sheet
    last_sheet_date = None
    # Iterate backwards to find the last date
    for val in reversed(dates_col):
        try:
            # Try parsing "MMM, YY" (e.g. "Oct, 23")
            last_sheet_date = pd.to_datetime(val, format='%b, %y')
            break
        except:
            continue
            
    if last_sheet_date is None:
        console.print("[yellow]Warning: Could not determine last date in sheet. Appending all data.[/yellow]")
        # Fallback: strict append at end
    else:
        # Filter dataframe for months > last_sheet_date
        # Ensure df['Month'] is datetime
        df['Month'] = pd.to_datetime(df['Month'])
        df = df[df['Month'] > last_sheet_date]
    
    if df.empty:
        console.print("[yellow]No new data to append (all months already in sheet).[/yellow]")
        return

    # 3. Format Data for Writing
    # Format Month column to "MMM, YY" (e.g., "Nov, 24")
    df_output = df.copy()
    df_output['Month'] = df_output['Month'].dt.strftime('%b, %y')
    
    # Convert to list of lists
    # We need to ensure we map to the correct columns. 
    # The df columns are already ordered by aggregate_categories:
    # Month, Bank..., Groceries...
    
    # The sheet screenshot shows Column A is Date.
    # But where do the expense columns start?
    # Screenshot:
    # A: Date (Col 1)
    # B: Totals ?
    # C: Necessary Total ?
    # D: Discret Total ?
    # E: Excess Total ?
    # F: Bank, Legal, Tax (Col 6)
    # ...
    
    # CRITICAL: We need to respect the column offset!
    # The aggregation calculates the values for the categories from Col F onwards.
    # We need to check where "Bank, Legal, Tax" is in the header row.
    
    header_row = sheet.row_values(1) # Assuming Headers are in Row 1
    try:
        start_col_idx = header_row.index("Bank, Legal, Tax")
        # gspread uses 1-based indexing for get, 0-based for python lists
        # But we need to construct the row to write.
        # The row structure in sheet:
        # [Date, (Formulas specific to sheet...), Category Values...]
        
        # WE CANNOT OVERWRITE COLUMNS B, C, D, E if they contain formulas.
        # AND `append_rows` writes a contiguous block.
        
        # STRATEGY: 
        # Write Date to Col A.
        # Write Category Values to Col F onwards.
        # Leave B, C, D, E blank? No, creating a NEW row usually needs formulas copied down.
        # User said "figure out the next row... write in 91".
        
        # If we use `update_cells` or specific ranges, we can skip columns.
        
        # Let's map headers to their indices to be safe.
        header_map = {name: i for i, name in enumerate(header_row)}
        
        updates = []
        current_row = last_row_index + 1
        
        for _, row in df_output.iterrows():
            # Update Categories
            # Prepare a list of values for the contiguous block of categories if they are contiguous
            # List of columns: 
            # "Bank, Legal, Tax", "Groceries", "Transport", "Car", "Phone, Net, TV", 
            # "Utilities", "Kids", "Experiences", "Restaurant", "Clothing", 
            # "Household", "Hobbies", "ATM", "Subscriptions", 
            # "Personal Care", "Gifts", "Holiday"
            
            # Are they contiguous in the sheet?
            # From screenshot: Bank... -> Groceries -> Transport -> Car -> Phone.. -> Utilities -> Kids -> Experiences -> Restaurant
            # Looks contiguous from F onwards.
            
            # Let's verify the header order matches our list
            # We will construct the row values based on the SHEET'S header order for saftey.
            
            category_start_col_char = 'F' # Assuming index 5
            # Actually, let's just build the range for the category block.
            
            # Get values for categories in the order they appear in the sheet
            # We need to find the column index for each category in our DF
            
            # Better approach:
            # 1. Read the header row again to be sure.
            # 2. Construct the update vector.
            pass
            
            data_values = []
            # We assume the categories in the sheet start at 'Bank, Legal, Tax' and continue.
            # We will grab the sub-list of headers from the sheet starting at 'Bank, Legal, Tax'
            
            # Find index of first category
            first_cat_idx = header_row.index("Bank, Legal, Tax")
            
            # Iterate through the sheet headers from there
            row_cat_values = []
            for col_idx in range(first_cat_idx, len(header_row)):
                col_name = header_row[col_idx]
                if col_name in df.columns:
                    row_cat_values.append(row[col_name])
                else:
                    # If the sheet has a column we don't know about, put 0 or empty?
                    # Safer to put 0.0 or check if it's a known category
                    row_cat_values.append(0.0)
            
            # Update the category range
            # We assume the categories in the sheet start at 'Bank, Legal, Tax' and continue.
            # We will grab the sub-list of headers from the sheet starting at 'Bank, Legal, Tax'
            
            # Find index of first category
            first_cat_idx = header_row.index("Bank, Legal, Tax")
            
            # Iterate through the sheet headers from there
            row_cat_values = []
            for col_idx in range(first_cat_idx, len(header_row)):
                col_name = header_row[col_idx]
                if col_name in df.columns:
                    # Convert numpy types to python native types for JSON serialization
                    val = row[col_name]
                    if hasattr(val, 'item'): 
                        val = val.item()
                    row_cat_values.append(val)
                else:
                    row_cat_values.append(0.0)
            
            # Calculate range A1 notation
            # gspread uses 1-based indexing
            # Start col: first_cat_idx (0-based) -> +1
            start_col_letter = gspread.utils.rowcol_to_a1(current_row, first_cat_idx + 1).replace(str(current_row), "")
            end_col_letter = gspread.utils.rowcol_to_a1(current_row, len(header_row)).replace(str(current_row), "")
            
            range_name = f"{SHEET_NAME}!{start_col_letter}{current_row}:{end_col_letter}{current_row}"
            
            console.print(f"   Writing categories to {range_name}")
            updates.append({
                'range': range_name,
                'values': [row_cat_values]
            })
            
            # Date (Col A) is handled automatically by the sheet
            # date_range = f"{SHEET_NAME}!A{current_row}"
            # date_val = row['Month']
            # console.print(f"   Writing Date '{date_val}' to {date_range}")
            # updates.append({
            #     'range': date_range,
            #     'values': [[date_val]]
            # })

            current_row += 1
            
        # Execute batch update
        if updates:
            spreadsheet = client.open_by_key(SPREADSHEET_ID)
            body = {
                'valueInputOption': 'USER_ENTERED',
                'data': updates
            }
            spreadsheet.values_batch_update(body)
            console.print(f"[green]Successfully appended {len(df)} rows to Sheet '{SHEET_NAME}'.[/green]")
        else:
            console.print("[yellow]No updates prepared.[/yellow]")

    except ValueError as e:
        console.print(f"[red]Error finding columns: {e}. Check sheet headers.[/red]")
        # raising so it can be caught in main.py
        raise
