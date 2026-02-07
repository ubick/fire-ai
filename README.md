# Fire AI - Financial Transaction Processor

A Python application for categorizing and aggregating financial transactions from CSV exports (e.g., Barclays, Amex) to track monthly spending against a Google Sheet.

## Features
- **Smart Categorization**: Automatically categorizes transactions based on your custom rules (`config/user_rules.json`).
- **Auto-Date Detection**: Automatically determines the next month to process based on the last entry in your Google Sheet.
- **Google Sheets Integration**: Updates your tracker with raw category data while preserving your sheet's formulas for totals.
- **Shadow Mode**: Run dry-runs to visualize changes in a rich terminal table without modifying the sheet.
- **Demo Mode**: Instantly try the app with sample data without any setup.
- **Privacy Focused**: Configuration, rules, and credentials are completely separated from the code.

## Quick Start (Demo Mode)

Want to see it in action? Just run the script without arguments:

```bash
./run.sh
```

This will load sample data (`csv/sample.csv`) and run in **Shadow Mode**, showing you the aggregated results in the terminal.

## Setup

### 1. Prerequisites
- Python 3.9+
- A Google Cloud Project with the Sheets API enabled.

### 2. Installation
1. Clone the repository.
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### 3. Configuration

#### Google Credentials
1. Place your Google Cloud service account credentials JSON file in `resources/credentials.json`.
   - *Note: This path is gitignored.*
2. **Important**: Share your Google Sheet with the `client_email` found in your credentials JSON file (give it **Editor** access).

#### User Rules
1. Copy the example rules file:
   ```bash
   cp config/user_rules.example.json config/user_rules.json
   ```
2. Edit `config/user_rules.json` to define your specific category mappings, keywords, and patterns.
   - *Note: `config/user_rules.json` is gitignored to protect your personal financial logic.*

#### Spreadsheet Config
1. Copy the example configuration:
   ```bash
   cp config/sheet_config.example.json config/sheet_config.json
   ```
2. Edit `config/sheet_config.json` and update:
   - `spreadsheet_id`: Your Google Sheet ID.
   - `sheet_name`: The tab name to update.
3. Edit `src/config.py` if you need to change the `SHEET_COLUMNS` list to match your sheet structure.

## Usage

### Shadow Mode (Dry Run)
Process a CSV file and visualize the result without updating the sheet.

```bash
./run.sh --csv path/to/your.csv --shadow-mode
```
*Tip: If you don't provide a date, the app will try to detect the relevant month automatically, or fall back to the latest data in the CSV.*

### Live Update
Process a CSV and update the Google Sheet.

```bash
./run.sh --csv path/to/your.csv
```

**Auto-Date Behavior:**
If you omit the `--date` argument, the app will:
1. Query your Google Sheet to find the last processed month.
2. Calculate the next month.
3. Filter the CSV for that specific month.
4. Process and append the data to the sheet.

**Note:** The app writes only the **Month** and **Raw Category Columns**. Summary columns (Totals, Necessary, Discretionary, Excess) are calculated for display in the terminal but are **excluded** from the update to avoid overwriting your sheet's formulas.

## Testing
Run the test suite to ensure everything is working correctly:
```bash
./test.sh
```

## Project Structure
- `src/`: Application source code.
- `config/`: Configuration files (rules).
- `csv/`: Place your transaction CSVs here (gitignored).
- `resources/`: Credentials (gitignored).
- `tests/`: Unit and E2E tests.
