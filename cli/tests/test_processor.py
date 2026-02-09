import pandas as pd
import pytest
from src.processor import categorize_transactions, aggregate_categories

@pytest.fixture
def raw_data():
    data = {
        'DATE': pd.to_datetime(['2024-11-01', '2024-11-02', '2024-11-03', '2024-11-10', '2024-11-12', '2024-11-20', '2024-11-25']),
        'DESCRIPTION': ['Tesco', 'Shell', 'Refund Tesco', 'Barclaycard Cashback', 'Vanguard Fee', 'IKEA Home', 'Salary'],
        'AMOUNT': [-50.00, -60.00, 10.00, 32.33, -9.44, -100.00, 2500.00],
        'CATEGORY': ['Groceries', 'Fuel', 'Groceries', 'Finances', 'Finances', 'House', 'Salary']
    }
    return pd.DataFrame(data)

def test_categorize_transactions(raw_data):
    df = categorize_transactions(raw_data)
    
    # Check mappings
    assert df.loc[df['DESCRIPTION'] == 'Shell', 'MAPPED_CATEGORY'].values[0] == 'Car'
    assert df.loc[df['DESCRIPTION'] == 'IKEA Home', 'MAPPED_CATEGORY'].values[0] == 'Household'
    assert df.loc[df['DESCRIPTION'] == 'Barclaycard Cashback', 'MAPPED_CATEGORY'].values[0] == 'Bank, Legal, Tax'
    
    # Check exclusions (Salary should be removed)
    assert 'Salary' not in df['MAPPED_CATEGORY'].values

def test_categorize_simplified_logic():
    """Verify that specific rules are gone (e.g. Decathlon goes to Mapping not Rule)"""
    data = {
        'DATE': pd.to_datetime(['2024-11-20']),
        'DESCRIPTION': ['Decathlon Purchase'],
        'AMOUNT': [-50.00],
        'CATEGORY': ['Health & Beauty'] 
    }
    df = pd.DataFrame(data)
    processed = categorize_transactions(df)
    
    # Decathlon (Health & Beauty) -> Personal Care (via Mapping)
    # Old logic would have moved it to Clothing (<200)
    assert processed['MAPPED_CATEGORY'].iloc[0] == 'Personal Care'

def test_aggregate_categories(raw_data):
    df = categorize_transactions(raw_data)
    agg_df = aggregate_categories(df)
    
    # Check shape
    assert not agg_df.empty
    
    # Check Net Aggregation Logic
    # Groceries: -50 + 10 = -40 (Net Expense) -> Inverted = 40.00
    expected_groceries = 40.00
    actual_groceries = agg_df['Groceries'].iloc[0]
    assert actual_groceries == expected_groceries
    
    # Bank, Legal, Tax: 32.33 (Income) + -9.44 (Expense) = 22.89 (Net Surplus) -> Inverted = -22.89
    expected_bank = -22.89 # 22.89 surplus -> -22.89
    actual_bank = agg_df['Bank, Legal, Tax'].iloc[0]
    assert abs(actual_bank - expected_bank) < 0.01

    # Household: -100 (Expense) -> Inverted = 100.00
    assert agg_df['Household'].iloc[0] == 100.00

def test_aggregate_categories_empty():
    """Verify that an empty DataFrame returns a DataFrame with correct columns and zero rows or handles gracefully."""
    df = pd.DataFrame(columns=['DATE', 'DESCRIPTION', 'AMOUNT', 'CATEGORY', 'MAPPED_CATEGORY'])
    agg_df = aggregate_categories(df)
    # pandas .empty is True if there are 0 rows, even with columns
    assert 'Month' in agg_df.columns
    assert 'Totals' not in agg_df.columns # Wait, aggregate_categories normally adds Totals, but the early return doesn't
    # Let's check what it actually returns
    assert len(agg_df) == 0

def test_categorize_missing_category():
    """Verify that transactions with missing categories are handled."""
    data = {
        'DATE': pd.to_datetime(['2024-11-20']),
        'DESCRIPTION': ['Unknown Shop'],
        'AMOUNT': [-50.00],
        'CATEGORY': [None] 
    }
    df = pd.DataFrame(data)
    processed = categorize_transactions(df)
    
    # MAPPED_CATEGORY should be None or NaN (fillna uses df['CATEGORY'])
    assert pd.isna(processed['MAPPED_CATEGORY'].iloc[0]) or processed['MAPPED_CATEGORY'].iloc[0] is None
