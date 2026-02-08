import pandas as pd
import numpy as np
from rich.console import Console

console = Console()

import json
from pathlib import Path

def load_rules():
    """Loads mapping rules from config/user_rules.json or falls back to example."""
    rules_path = Path("config/user_rules.json")
    example_path = Path("config/user_rules.example.json")
    
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

# Load Rules
rules = load_rules()

CATEGORY_MAPPING = rules.get("category_mapping", {})
DESCRIPTION_OVERRIDES = rules.get("description_overrides", {})
HOLIDAY_KEYWORDS = rules.get("holiday_keywords", [])
FOREIGN_CURRENCY_PATTERNS = rules.get("foreign_currency_patterns", [])
HOBBIES_KEYWORDS = rules.get("hobbies_keywords", [])
UK_HOTEL_KEYWORDS = rules.get("uk_hotel_keywords", [])
SPORTS_STORES = rules.get("sports_stores", [])

# Categories to ALWAYS exclude from final output
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
    
    # 1. Apply Description Overrides
    for desc, cat in DESCRIPTION_OVERRIDES.items():
        df.loc[df['DESCRIPTION'].str.contains(desc, case=False, na=False), 'CATEGORY'] = cat

    # 1a. Apply Hobbies Keywords (karate, gardening, photography, etc.)
    for kw in HOBBIES_KEYWORDS:
        df.loc[df['DESCRIPTION'].str.contains(kw, case=False, na=False), 'CATEGORY'] = 'Hobbies'

    # 1b. Apply UK Hotel Keywords -> Holiday
    for kw in UK_HOTEL_KEYWORDS:
        df.loc[df['DESCRIPTION'].str.contains(kw, case=False, na=False), 'CATEGORY'] = 'Other business costs'

    # 1c. Apply Sports Stores logic (Decathlon, Go Outdoors)
    # Under 200 GBP -> Clothing, Over 200 GBP -> Hobbies (cycling)
    # Only apply if user hasn't explicitly categorized it as something else we want to keep (e.g. Health & Beauty)
    # For now, we only apply this if the current category is 'Shopping' or unknown, OR if it matches typical sports store categories
    # But to fix the specific issue with Decathlon moving from Health & Beauty to Clothing when user wants it in H&B:
    # We should skip this rule if the category is already 'Health & Beauty' (or raw equivalent)
    # However, 'CATEGORY' here is the raw category from CSV.
    # Raw Category for Decathlon was 'Health & Beauty'.
    # So we should skip if category is 'Health & Beauty'.
    for store in SPORTS_STORES:
        mask = df['DESCRIPTION'].str.contains(store, case=False, na=False)
        # Skip if already categorized as Health & Beauty (or mapped equivalent)
        # 'Health & Beauty', 'Personal Care', 'Healthcare'
        mask = mask & ~df['CATEGORY'].isin(['Health & Beauty', 'Healthcare', 'Personal Care'])
        
        # Under 200 -> Clothing
        df.loc[mask & (df['AMOUNT'].abs() < 200), 'CATEGORY'] = 'Clothing & shoes'
        # Over 200 -> Hobbies (cycling)
        df.loc[mask & (df['AMOUNT'].abs() >= 200), 'CATEGORY'] = 'Hobbies'


    # 1d. Apply Holiday Keywords Logic (Split Travel)
    # If Category is Travel (or will be mapped to Transport), but description matches Holiday keywords, force to Holiday.
    mask_travel = df['CATEGORY'].isin(['Travel', 'Holiday'])
    for kw in HOLIDAY_KEYWORDS:
        df.loc[mask_travel & df['DESCRIPTION'].str.contains(kw, case=False, na=False), 'CATEGORY'] = 'Other business costs' 

    # 1e. Apply Foreign Currency Detection
    # Any transaction in a foreign currency is likely a holiday expense.
    # 1e. Apply Foreign Currency Detection
    # Any transaction in a foreign currency is likely a holiday expense.
    for pattern in FOREIGN_CURRENCY_PATTERNS:
        mask = df['DESCRIPTION'].str.contains(pattern, case=False, na=False)
        # Add basic categories to exclude list to prevent overwriting user's classification for food/transport while abroad
        exclude_cats = [
            'Salary', 'Transfers', 'Credit card payments', 'Securities trades', 'Savings', 'Investments',
            'Groceries', 'Transport', 'Eating Out', 'Eating out', 'Restaurant', 'Food'
        ]
        mask = mask & ~df['CATEGORY'].isin(exclude_cats)
        df.loc[mask, 'CATEGORY'] = 'Other business costs'  # Maps to Holiday


    # 2. Apply Category Mapping
    df['MAPPED_CATEGORY'] = df['CATEGORY'].map(CATEGORY_MAPPING).fillna(df['CATEGORY'])
    
    # 3. Filter Excluded Categories
    df = df[~df['MAPPED_CATEGORY'].isin(EXCLUDED_CATEGORIES)]
    
    # 4. REMOVED: Convert amounts to absolute values here.
    # We must keep signs to handle refunds (negative expenses vs positive refunds) correctly.
    # df['AMOUNT'] = df['AMOUNT'].abs() 
    
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
