import pandas as pd
import numpy as np
from rich.console import Console

console = Console()

import json
from pathlib import Path

def load_rules():
    """Loads mapping rules from config/user_rules.json or falls back to example."""
    cli_dir = Path(__file__).parent.parent
    rules_path = cli_dir / "config/user_rules.json"
    example_path = cli_dir / "config/user_rules.example.json"
    
    if rules_path.exists():
        with open(rules_path, 'r') as f:
            return json.load(f)
    elif example_path.exists():
        console.print("[yellow]Warning: config/user_rules.json not found. Using example rules.[/yellow]")
        with open(example_path, 'r') as f:
            return json.load(f)
    else:
        console.print("[red]Error: No rules configuration found![/red]")
        return {}

# Load Rules dynamically in categorize_transactions to support long-running processes
EXCLUDED_CATEGORIES = ["EXCLUDE"]

from src.config import SHEET_COLUMNS

def categorize_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Applies categorization rules to the DataFrame.
    """
    df = df.copy()
    
    # Ensure CATEGORY is object type to allow string assignments
    if df['CATEGORY'].dtype != 'object':
        df['CATEGORY'] = df['CATEGORY'].astype('object')
    
    # Load Rules Fresh
    rules = load_rules()
    category_mapping = rules.get("category_mapping", {})
    description_overrides = rules.get("description_overrides", {})

    # 1. Apply Description Overrides
    for desc, cat in description_overrides.items():
        df.loc[df['DESCRIPTION'].str.contains(desc, case=False, na=False), 'CATEGORY'] = cat

    # 2. Apply Category Mapping
    df['MAPPED_CATEGORY'] = df['CATEGORY'].map(category_mapping).fillna(df['CATEGORY'])
    
    # 3. Filter Excluded Categories
    df = df[~df['MAPPED_CATEGORY'].isin(EXCLUDED_CATEGORIES)]
    
    return df

def aggregate_categories(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregates transactions by Month and Category.
    """
    if df.empty:
        return pd.DataFrame(columns=['Month'] + SHEET_COLUMNS)

    df = df.copy()
    
    # Create Month Column (e.g., "Oct, 23" or "2023-10-01")
    # Sheet format in screenshot looks like "Oct, 23" (Custom format)
    # We will keep it as a datetime object for sorting, and format before writing.
    df['Month'] = df['DATE'].dt.to_period('M').dt.to_timestamp()
    
    # Pivot (Summing signed values: Expenses are negative, Refunds are positive)
    pivot_df = df.pivot_table(
        index='Month', 
        columns='MAPPED_CATEGORY', 
        values='AMOUNT', 
        aggfunc='sum', 
        fill_value=0.0
    )
    
    # Invert Sign (Expenses become Positive, Refunds/Surplus become Negative)
    pivot_df = -pivot_df
    
    # Reindex to ensure all target columns exist and are in order
    pivot_df = pivot_df.reindex(columns=SHEET_COLUMNS, fill_value=0.0)
    
    # Calculate Summaries
    # Necessary: Bank, Legal, Tax | Groceries | Transport | Car | Phone, Net, TV | Utilities | Kids
    necessary_cols = ["Bank, Legal, Tax", "Groceries", "Transport", "Car", "Phone, Net, TV", "Utilities", "Kids"]
    pivot_df['Necessary'] = pivot_df[necessary_cols].sum(axis=1)
    
    # Discretionary: Experiences | Restaurant | Clothing | Household | Hobbies | ATM | Subscriptions | Personal Care
    discretionary_cols = ["Experiences", "Restaurant", "Clothing", "Household", "Hobbies", "ATM", "Subscriptions", "Personal Care"]
    pivot_df['Discretionary'] = pivot_df[discretionary_cols].sum(axis=1)
    
    # Excess: Gifts | Holiday
    excess_cols = ["Gifts", "Holiday"]
    pivot_df['Excess'] = pivot_df[excess_cols].sum(axis=1)
    
    # Totals
    pivot_df['Totals'] = pivot_df['Necessary'] + pivot_df['Discretionary'] + pivot_df['Excess']
    
    # Reorder columns for CLI display
    # We want: Month, Totals, Necessary, Discretionary, Excess, [Individual Categories...]
    summary_cols = ['Totals', 'Necessary', 'Discretionary', 'Excess']
    
    # Note: sheets_client expects specific columns. We should return a DF with ALL columns, 
    # but sheets_client should select what it needs.
    # The current sheets_client logic iterates over SHEET_COLUMNS (implicitly via header row matching).
    # So adding extra columns here won't break sheets_client as long as we don't remove existing ones.
    
    final_cols = ['Month'] + summary_cols + SHEET_COLUMNS
    final_df = pivot_df.reset_index()[final_cols]
    
    return final_df
