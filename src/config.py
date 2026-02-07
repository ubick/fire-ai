
# Configuration for FIRE AI

# Google Sheets ID matches the one from src/sheets_client.py
SPREADSHEET_ID = "155U77nBbBI9SHwk0TffdhYj4cnKO9u2EDRJe4Bw4Wq8"
SHEET_NAME = "Out"

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
