import typer
from rich.console import Console
from rich.table import Table
import pandas as pd
from typing import Optional
from pathlib import Path
from src.data_loader import load_csv
from src.processor import categorize_transactions, aggregate_categories
from src.sheets_client import update_sheet

app = typer.Typer()
console = Console()

@app.command()
def process(
    csv_path: Optional[str] = typer.Option(None, "--csv", "-c", help="Path to the transaction CSV file. Defaults to demo data if not provided."),
    date: Optional[str] = typer.Option(None, "--date", "-d", help="Filter by month (e.g., 'may24', 'may-24', '2024-05'). If invalid/missing, attempts auto-detection."),
    dry_run: bool = typer.Option(False, "--dry-run", "--shadow-mode", help="Change to True to run without updating Google Sheets"),
    override: bool = typer.Option(False, "--override", help="Overwrite existing data for the selected month"),
    credentials_path: str = typer.Option("cli/resources/credentials.json", "--creds", help="Path to Google Cloud credentials")
):
    """
    Process financial transactions and update Google Sheets.
    """
    is_demo = False

    if dry_run and override:
        console.print("[bold red]WARNING: You have specified both --shadow-mode (read-only) and --override (write).[/bold red]")
        console.print("[yellow]--override implies connecting and writing to Google Sheets.[/yellow]")
        if typer.confirm("Do you want to continue in WRITE mode (disabling shadow mode)?", default=False):
            dry_run = False
            console.print("[bold green]Proceeding in WRITE mode...[/bold green]")
        else:
            console.print("[bold yellow]Proceeding in SHADOW mode (ignoring --override)...[/bold yellow]")
            override = False
    if csv_path is None:
        cli_dir = Path(__file__).parent
        csv_path = str(cli_dir / "csv/sample.csv")
        dry_run = True
        is_demo = True
        console.print("[bold magenta]Running in DEMO MODE using sample data (Shadow Mode forced)[/bold magenta]")

    try:
        if not Path(csv_path).exists():
             console.print(f"[bold red]Error: File not found: {csv_path}[/bold red]")
             return

        console.print(f"[bold green]Starting processing for: {csv_path}[/bold green]")
        
        # 1. Load Data
        df = load_csv(csv_path)
        console.print(f"Loaded {len(df)} transactions.")
        
        # 2. Process Data
        processed_df = categorize_transactions(df)
        
        # 2a. Determine Date Filter
        target_period = None
        
        if date:
            # User provided date
            target_period = parse_filter_date(date)
            if not target_period:
                return # Error printed in helper
        else:
            # Auto-detect logic
            import datetime
            today = datetime.date.today()
            # Default to previous month
            first = today.replace(day=1)
            prev_month = first - datetime.timedelta(days=1)
            default_period = pd.Period(prev_month, freq='M')
            
            use_sheet = False
            
            # Logic: If Shadow Mode (dry_run), prompt user. If Live Mode, default to Sheet.
            if dry_run:
                # In Demo Mode, skip prompt and use default (which will fallback)
                if not is_demo:
                    use_sheet = typer.confirm(f"Query Google Sheets to auto-detect date? (Default: Process {default_period})", default=False)
            else:
                # Live mode always defaults to Sheet logic unless specified
                # Actually, user logic implies we should check sheet in live mode.
                use_sheet = True # Default behavior for live mode from previous step

            if use_sheet:
                 from src.sheets_client import get_last_transaction_date
                 console.print("[yellow]Attempting to detect next month from Google Sheets...[/yellow]")
                 last_date = get_last_transaction_date(credentials_path)
                 
                 if last_date:
                     next_month = last_date + pd.DateOffset(months=1)
                     target_period = pd.Period(next_month, freq='M')
                     console.print(f"[bold cyan]Auto-detected next month from Sheet: {target_period}[/bold cyan]")
                 else:
                     console.print("[bold red]Could not determine last date from sheet. using default.[/bold red]")
                     target_period = default_period
            else:
                target_period = default_period
                if not is_demo: # Kept quiet for demo
                     console.print(f"[cyan]Using default target: {target_period}[/cyan]")

        # 2b. Apply Filter & Fallback
        if target_period:
            # Create a MonthPeriod column for filtering
            processed_df['MonthPeriod'] = processed_df['DATE'].dt.to_period('M')
            
            # Filter
            filtered_df = processed_df[processed_df['MonthPeriod'] == target_period].copy()
            
            if filtered_df.empty:
                 console.print(f"[yellow]No transactions found for {target_period}[/yellow]")
                 
                 # FALLBACK: Find latest month in CSV
                 if not processed_df.empty:
                     max_date = processed_df['DATE'].max()
                     new_target = pd.Period(max_date, freq='M')
                     console.print(f"[bold yellow]Falling back to latest month in CSV: {new_target}[/bold yellow]")
                     
                     filtered_df = processed_df[processed_df['MonthPeriod'] == new_target].copy()
                     target_period = new_target # Update for display
                 else:
                     console.print("[bold red]CSV is empty![/bold red]")
                     return

            if filtered_df.empty:
                 console.print(f"[bold red]No transactions found even after fallback.[/bold red]")
                 return
            
            console.print(f"[bold yellow]Filtering for {target_period}: Found {len(filtered_df)} transactions[/bold yellow]")
            processed_df = filtered_df
        
        aggregated_df = aggregate_categories(processed_df)
        
        # 3. Output
        if dry_run:
            console.print("[bold yellow]SHADOW MODE: Not updating Google Sheets[/bold yellow]")
            
            # Load Ground Truth if available (REMOVED)
            # gt_comparison removed per user request to simplify output
            gt_totals = {}
            
            print_aggregated_table(aggregated_df, gt_totals)
            console.print("\n[bold]CSV Format (for verification):[/bold]")
            import io
            csv_buf = io.StringIO()
            aggregated_df.to_csv(csv_buf, index=False)
            console.print(csv_buf.getvalue())
        else:
            from src.sheets_client import update_sheet
            from src.config import SHEET_COLUMNS
            
            # Filter out summary columns for the sheet update
            # We only want 'Month' + the raw categories defined in SHEET_COLUMNS
            cols_to_write = ['Month'] + SHEET_COLUMNS
            df_to_write = aggregated_df[cols_to_write].copy()
            
            console.print("[bold blue]Updating Google Sheets...[/bold blue]")
            update_sheet(df_to_write, credentials_path, override=override)
            console.print("[bold green]Update Complete![/bold green]")
            
            # Display what was written (Full Table including summaries for user context)
            console.print("\n[bold]Data written to Sheet (Summary columns are NOT written):[/bold]")
            print_aggregated_table(aggregated_df)
            
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        import traceback
        traceback.print_exc()


def parse_filter_date(date_str: str) -> Optional[pd.Period]:
    """
    Parses user input date string into a pandas Period (Month).
    Supports: 'may24', 'may-24', '2024-05', '05/24'
    """
    import datetime
    
    # Try different formats
    formats = [
        "%b%y",      # may24
        "%b-%y",     # may-24
        "%Y-%m",     # 2024-05
        "%m/%y",     # 05/24
        "%B %Y",     # May 2024
        "%b %Y",     # May 2024
    ]
    
    for fmt in formats:
        try:
            dt = datetime.datetime.strptime(date_str, fmt)
            return pd.Period(dt, freq='M')
        except ValueError:
            continue
            
    console.print(f"[bold red]Invalid date format: '{date_str}'. Try 'may24' or '2024-05'.[/bold red]")
    return None


def print_aggregated_table(df: pd.DataFrame, gt_data: dict = None):
    """Prints a rich table of the aggregated data."""
    if df.empty:
        console.print("[yellow]No data to display.[/yellow]")
        return

    # Determine date range for title
    min_date = df['Month'].min()
    max_date = df['Month'].max()
    
    if min_date == max_date:
        date_range_str = min_date.strftime('%b %Y')
    else:
        date_range_str = f"{min_date.strftime('%b %Y')} - {max_date.strftime('%b %Y')}"
        
    table = Table(title=f"Aggregated Monthly Expenses ({date_range_str})")
    
    # Add columns (Month + Categories)
    table.add_column("Month", style="cyan", no_wrap=True)
    
    # Identify summary columns for styling
    summary_cols = ['Totals', 'Necessary', 'Discretionary', 'Excess']
    
    categories = [col for col in df.columns if col != 'Month' and col not in summary_cols]
    
    # Sort categories by total amount (descending)
    # Use absolute sum to handle potential negative signs if any, though expenses are positive here.
    # Actually, expenses are positive, so sum is fine.
    categories_sorted = sorted(categories, key=lambda c: df[c].sum(), reverse=True)
    
    all_columns = summary_cols + categories_sorted

    # Add columns
    for cat in all_columns:
        if cat not in df.columns: continue # Safety check
        style = "bold magenta" if cat in summary_cols else "white"
        table.add_column(cat, justify="right", style=style)
        
    # Add rows
    for _, row in df.iterrows():
        month_dt = row['Month']
        month_str = month_dt.strftime('%b, %y')
        
        # Build row data based on sorted columns
        row_values = [f"{row[cat]:.2f}" if cat in df.columns else "0.00" for cat in all_columns]
        row_data = [month_str] + row_values
        table.add_row(*row_data)

    console.print(table)

if __name__ == "__main__":
    app()
