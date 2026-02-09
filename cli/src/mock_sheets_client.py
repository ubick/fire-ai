import pandas as pd
import json
from pathlib import Path
from rich.console import Console
from src.config import SHEET_COLUMNS, SHEET_NAME

console = Console()

class MockWorksheet:
    def __init__(self, data):
        self.data = data # List of lists (rows)

    def col_values(self, index):
        # 1-based index
        col_idx = index - 1
        return [row[col_idx] if col_idx < len(row) else "" for row in self.data]

    def row_values(self, index, **kwargs):
        # 1-based index
        row_idx = index - 1
        if 0 <= row_idx < len(self.data):
            return self.data[row_idx]
        return []

    def get_all_values(self):
        return self.data

class MockSpreadsheet:
    def __init__(self, data):
        self.data = data

    def worksheet(self, name):
        return MockWorksheet(self.data)

    def values_batch_update(self, body):
        console.print(f"[bold cyan][Mock][/bold cyan] Batch Update executed with {len(body.get('data', []))} updates.")
        return {"spreadsheetId": "mock_id", "updatedCells": len(body.get('data', []))}

class MockClient:
    def __init__(self, data):
        self.data = data

    def open_by_key(self, key):
        return MockSpreadsheet(self.data)

def get_mock_data():
    """Returns some default mock data for the spreadsheet."""
    headers = ["Month"] + SHEET_COLUMNS + ["Necessary", "Discretionary", "Excess", "Totals"]
    rows = [
        headers,
        ["Jan, 24", 100, 200, 50, 20, 10, 80, 50, 100, 50, 40, 30, 20, 10, 5, 15, 10, 50, 100, 510, 455, 165, 1130],
        ["Feb, 24", 110, 210, 55, 25, 15, 85, 55, 105, 55, 45, 35, 25, 15, 10, 20, 15, 55, 105, 555, 505, 215, 1275],
    ]
    return rows

def get_client(credentials_path: str):
    return MockClient(get_mock_data())

def get_last_transaction_date(credentials_path: str) -> pd.Timestamp | None:
    data = get_mock_data()
    last_row = data[-1]
    date_str = last_row[0]
    try:
        return pd.to_datetime(date_str, format='%b, %y')
    except:
        return None

def update_sheet(df: pd.DataFrame, credentials_path: str, override: bool = False):
    console.print(f"[bold cyan][Mock][/bold cyan] update_sheet called with {len(df)} rows. Override={override}")
    return True

def fetch_month_data(credentials_path: str, target_month: pd.Period) -> dict | None:
    data = get_mock_data()
    headers = data[0]
    for row in data[1:]:
        try:
            dt = pd.to_datetime(row[0], format='%b, %y')
            if dt.year == target_month.year and dt.month == target_month.month:
                return {headers[i]: row[i] for i in range(len(headers))}
        except:
            continue
    return None
