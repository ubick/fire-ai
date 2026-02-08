
# Configuration for FIRE AI

import json
from pathlib import Path
from rich.console import Console

console = Console()

def load_sheet_config():
    """Loads spreadsheet ID and Name from config/sheet_config.json or falls back to example."""
    cli_dir = Path(__file__).parent.parent
    config_path = cli_dir / "config/sheet_config.json"
    example_path = cli_dir / "config/sheet_config.example.json"
    
    config = {}
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = json.load(f)
    elif example_path.exists():
        console.print("[yellow]Warning: config/sheet_config.json not found. Using example config.[/yellow]")
        with open(example_path, 'r') as f:
            config = json.load(f)
    else:
        # Fallback default (will likely fail auth, but prevents crash on import)
        config = {"spreadsheet_id": "", "sheet_name": "Out"}
        
    return config

_sheet_config = load_sheet_config()

# Google Sheets ID matches the one from src/sheets_client.py
SPREADSHEET_ID = _sheet_config.get("spreadsheet_id", "")
SHEET_NAME = _sheet_config.get("sheet_name", "Out")

# Columns expected in the Google Sheet (in order)
# Note: Totals, Necessary, Discretionary, Excess are calculated dynamically
SHEET_COLUMNS = [
    "Bank, Legal, Tax",
    "Groceries",
    "Transport",
    "Car",
    "Phone, Net, TV",
    "Utilities",
    "Kids",
    "Experiences",
    "Restaurant",
    "Clothing",
    "Household",
    "Hobbies",
    "ATM",
    "Subscriptions",
    "Personal Care",
    "Gifts",
    "Holiday"
]
