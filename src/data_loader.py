import pandas as pd
from datetime import datetime

def load_csv(file_path: str) -> pd.DataFrame:
    """
    Loads a CSV file of financial transactions.
    
    Expected format:
    DATE, AMOUNT, DESCRIPTION, CATEGORY
    
    Args:
        file_path: Path to the CSV file.
        
    Returns:
        pd.DataFrame: DataFrame with parsed dates and numeric amounts.
    """
    try:
        # Read CSV
        df = pd.read_csv(file_path)
        
        # Check if required columns exist (case-insensitive)
        required_cols = ["DATE", "AMOUNT", "DESCRIPTION", "CATEGORY"]
        df.columns = df.columns.str.upper().str.strip()
        
        if not all(col in df.columns for col in required_cols):
             raise ValueError(f"CSV missing required columns: {required_cols}")

        # Parse Dates
        # Kotlin app uses standard SQL format YYYY-MM-DD usually, but let's be robust
        df["DATE"] = pd.to_datetime(df["DATE"], errors='coerce')
        
        # Clean Amounts (remove currency symbols if present)
        if df["AMOUNT"].dtype == 'object':
             df["AMOUNT"] = df["AMOUNT"].astype(str).str.replace(r'[^\d.-]', '', regex=True).astype(float)
        
        # Drop rows with invalid dates
        cleaned_df = df.dropna(subset=["DATE"]).copy()
        
        return cleaned_df

    except Exception as e:
        raise ValueError(f"Error loading CSV: {e}")
