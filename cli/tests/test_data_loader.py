import pandas as pd
import pytest
import os
from src.data_loader import load_csv

# Use the fake CSV created for E2E tests
FAKE_CSV_PATH = "tests/fixtures/fake_transactions.csv"

def test_load_csv_exists():
    assert os.path.exists(FAKE_CSV_PATH)
    df = load_csv(FAKE_CSV_PATH)
    assert not df.empty
    assert len(df) == 12 # Based on fake_transactions.csv content

def test_load_csv_columns():
    df = load_csv(FAKE_CSV_PATH)
    expected_cols = ['DATE', 'DESCRIPTION', 'AMOUNT', 'CATEGORY']
    for col in expected_cols:
        assert col in df.columns

def test_load_csv_dtypes():
    df = load_csv(FAKE_CSV_PATH)
    assert pd.api.types.is_datetime64_any_dtype(df['DATE'])
    assert pd.api.types.is_float_dtype(df['AMOUNT'])
    assert pd.api.types.is_string_dtype(df['DESCRIPTION']) or pd.api.types.is_object_dtype(df['DESCRIPTION'])
