
import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from src.sheets_client import update_sheet
from src.config import SPREADSHEET_ID, SHEET_NAME

@patch('src.sheets_client.get_client')
@patch('src.sheets_client.SPREADSHEET_ID', 'test_spreadsheet_id')
@patch('src.sheets_client.SHEET_NAME', 'test_sheet_name')
def test_update_sheet_preserves_formulas(mock_get_client):
    # Setup Mocks
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_sheet = MagicMock()
    mock_client.open_by_key.return_value.worksheet.return_value = mock_sheet

    # Mock Data
    # Existing dates in column A
    mock_sheet.col_values.return_value = ["Month", "Jan, 24"]
    
    # Mock row data with formulas
    # Row 1: Headers
    # Row 2: Jan, 24 data. 
    # Let's say column B (index 1) has a formula "=SUM(X:Y)" and column C has a value.
    # The update_sheet logic calls row_values, but we want it to call get with value_render_option='FORMULA'
    # Actually, my plan says I will use `value_render_option='FORMULA'` which implies using `get()` or `batch_get()` 
    # instead of `row_values()` (which is just values).
    
    # Let's assume the implementation uses `sheet.row_values(row_idx, value_render_option='FORMULA')` if available, 
    # or `sheet.get(range, value_render_option='FORMULA')`.
    # `gspread` `row_values` supports `value_render_option`.
    
    # Mocking `row_values` to return formulas for the target row (Row 2)
    # detailed sequence:
    # 1. col_values(1) called to get dates.
    # 2. update_sheet iterates. matches "Jan, 24".
    # 3. calls `row_values(2, value_render_option='FORMULA')` -> returns ["Jan, 24", "=FORMULA", "100", ...]
    
    def side_effect_row_values(row, **kwargs):
        if row == 1: 
            return ["Month", "Bank, Legal, Tax", "Groceries"] # shortened header
        if row == 2:
            # key check: kwargs should contain value_render_option='FORMULA'
            if kwargs.get('value_render_option') == 'FORMULA':
                 return ["Jan, 24", "=EXISTING_FORMULA", "50"]
            return ["Jan, 24", "10", "50"] # default values
        return []

    mock_sheet.row_values.side_effect = side_effect_row_values

    # Input DataFrame
    df = pd.DataFrame({
        'Month': [pd.Timestamp('2024-01-01')],
        'Bank, Legal, Tax': [200.0], # Should NOT overwrite formula
        'Groceries': [150.0]         # Should overwrite 50
    })

    # Execute
    update_sheet(df, "credentials.json", override=True)

    # Verify
    # Expect batch_update to be called
    mock_sheet.values_batch_update.assert_not_called() # It calls spreadsheet.values_batch_update actually
    
    # Let's check `spreadsheet.values_batch_update`
    mock_spreadsheet = mock_client.open_by_key.return_value
    assert mock_spreadsheet.values_batch_update.called
    
    _, args = mock_spreadsheet.values_batch_update.call_args
    body = args['body'] if 'body' in args else mock_spreadsheet.values_batch_update.call_args[0][0]
    
    updates = body['data']
    
    # We expect updates for:
    # 1. 'Groceries' (Column C -> "C2") -> 150.0
    # We expect NO update for 'Bank, Legal, Tax' (Column B -> "B2") because it had "=EXISTING_FORMULA"
    
    # Verify
    # Expect batch_update to be called
    mock_spreadsheet = mock_client.open_by_key.return_value
    assert mock_spreadsheet.values_batch_update.called
    
    _, args = mock_spreadsheet.values_batch_update.call_args
    body = args['body'] if 'body' in args else mock_spreadsheet.values_batch_update.call_args[0][0]
    
    updates = body['data']
    
    # Analyze updates
    # We expect:
    # 1. Date update (since new data or just general flow often adds date if not skipping whole row, 
    #    but here we override=True so we are processing the row).
    #    Actually, wait. logic says:
    #    if match_dt: ... Overwriting data ...
    #    It does NOT add date update to `updates` if match_dt is found (existing row). 
    #    It only adds date update if NEW row.
    #    In this test, "Jan, 24" exists in mock_sheet.col_values(1). So match_dt is found.
    #    So NO date update.
    
    # We expect updates for 'Groceries' (Column C -> C2, value 150.0).
    # We expect NO update for 'Bank, Legal, Tax' (Column B -> B2) because formula.
    
    # Let's search updates for target ranges
    updated_ranges = {u['range']: u['values'][0][0] for u in updates}
    
    print("Updated Ranges:", updated_ranges)
    
    # Check Groceries (Column C is 3rd column -> C)
    # Target row is 2. Range: "test_sheet_name!C2"
    assert "test_sheet_name!C2" in updated_ranges
    assert updated_ranges["test_sheet_name!C2"] == 150.0
    
    # Check Bank (Column B -> B)
    # Range: "test_sheet_name!B2" should NOT be in updates
    assert "test_sheet_name!B2" not in updated_ranges

@patch('src.sheets_client.get_client')
@patch('src.sheets_client.SPREADSHEET_ID', 'test_spreadsheet_id')
@patch('src.sheets_client.SHEET_NAME', 'test_sheet_name')
def test_update_sheet_preserves_date_formulas(mock_get_client):
    # Setup Mocks
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_sheet = MagicMock()
    mock_client.open_by_key.return_value.worksheet.return_value = mock_sheet

    # Mock Data
    # Existing dates in column A
    mock_sheet.col_values.return_value = ["Month", "Jan, 24"]
    
    # Mock row data with formula in Column A
    def side_effect_row_values(row, **kwargs):
        if row == 1: 
            return ["Month", "Bank, Legal, Tax"]
        if row == 2:
            if kwargs.get('value_render_option') == 'FORMULA':
                 # Column A has formula
                 return ["=EDATE(A1,1)", "100"]
            return ["Jan, 24", "100"]
        return []

    mock_sheet.row_values.side_effect = side_effect_row_values

    # Input DataFrame
    df = pd.DataFrame({
        'Month': [pd.Timestamp('2024-01-01')],
        'Bank, Legal, Tax': [200.0]
    })

    # Execute
    update_sheet(df, "credentials.json", override=True)

    # Verify
    mock_spreadsheet = mock_client.open_by_key.return_value
    assert mock_spreadsheet.values_batch_update.called
    
    _, args = mock_spreadsheet.values_batch_update.call_args
    body = args['body'] if 'body' in args else mock_spreadsheet.values_batch_update.call_args[0][0]
    updates = body['data']
    updated_ranges = {u['range']: u['values'][0][0] for u in updates}
    
    print("Updated Ranges:", updated_ranges)
    
    # Check Date (Column A)
    # Target row is 2. Range: "test_sheet_name!A2" should NOT be in updates
    assert "test_sheet_name!A2" not in updated_ranges
    
    # Check Bank (Column B)
    # Should be updated to 200.0
    assert "test_sheet_name!B2" in updated_ranges
    assert updated_ranges["test_sheet_name!B2"] == 200.0
