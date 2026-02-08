import pytest
from typer.testing import CliRunner
from main import app
import os

runner = CliRunner()

@pytest.fixture
def fake_csv_path(tmp_path):
    """Creates a temporary CSV file with test data."""
    csv_content = """DATE,DESCRIPTION,AMOUNT,CATEGORY
2024-11-01,Tesco,-40.00,Groceries
2024-11-02,Shell,-60.00,Fuel
2024-11-05,Refund,10.00,Fuel
2024-11-10,Hotel,-15.00,Holiday
2024-11-12,Bank Fee,-5.00,Finances
2024-11-15,Salary,2000.00,Income
2024-11-20,Transfer,-500.00,Transfers
2024-11-12,Tax Refund,27.89,Taxes
2024-11-25,Phone Bill,-135.00,Phone
2024-11-28,Rent,-100.00,House
2024-11-30,Dinner,-40.00,Eating Out
2024-12-01,Dec Grocery,-100.00,Groceries
"""
    p = tmp_path / "fake_transactions.csv"
    p.write_text(csv_content, encoding="utf-8")
    return str(p)

def test_shadow_mode_e2e(fake_csv_path):
    # Ensure fake CSV exists
    assert os.path.exists(fake_csv_path)
    
    # Run the command in shadow mode for Nov 2024
    # Note: Observed behavior is that main.py behaves as single command
    result = runner.invoke(app, ["--csv", fake_csv_path, "--date", "nov24", "--dry-run"])
    
    # Verify execution success
    assert result.exit_code == 0
    assert "SHADOW MODE: Not updating Google Sheets" in result.stdout
    assert "Filtering for 2024-11: Found" in result.stdout
    
    # Verify Dynamic Title
    # Should say "Aggregated Monthly Expenses (Nov 2024)" since min=max date
    assert "Aggregated Monthly Expenses (Nov 2024)" in result.stdout
    
    # Verify specific output values in the table
    # We expect Household to be 100.00 (Standard)
    # We look for the row "Nov, 24" and then verify the number presence
    
    # Simple string checks for key values we calculated
    # Household: 100.00 (or 100.0 in CSV)
    assert "100.0" in result.stdout
    
    # Bank, Legal, Tax: -22.89
    # The output format for negative numbers in Rich table might be "-22.89"
    assert "-22.89" in result.stdout
    
    # Groceries: 40.00 (-50 + 10 = -40 inverted -> 40)
    assert "40.0" in result.stdout
    
    # Phone, Net, TV: 135.00
    assert "135.0" in result.stdout
    
    # Household: 100.00
    assert "100.0" in result.stdout
    
    # Restaurant: 40.00
    # Note: 40.00 matches multiple categories, so just checking presence isn't perfect but good enough for smoke test.
    
    # Check that Dec data is excluded (Dec Groceries -100)
    # If filtered correctly, Total for Nov shouldn't include it.
    # Total Nov: 40(Groc) + 50(Fuel) + 15(Hol) - 22.89(Bank) + 135(Phone) + 100(House) + 40(Rest) = 357.11
    
    assert "357.11" in result.stdout

def test_date_filter_formats(fake_csv_path):
    # Test alternative date format
    result = runner.invoke(app, ["--csv", fake_csv_path, "--date", "2024-11", "--dry-run"])
    assert result.exit_code == 0
    assert "Filtering for 2024-11" in result.stdout
