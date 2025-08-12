# MoH Module

## Description

The `MoH` module is a script for uploading telemetry data to the ThingsBoard platform. Optionally, it can calculate and send the **Hourly Maximum Oscillation (MoH)** metric from the CSV data.

### Key Functions

-   `round_to(num, decimals)`: Implements a rounding function similar to JavaScript's `Math.round`.
-   `send_data(df, telemetry_keys, token, host)`: Sends data from a pandas DataFrame to ThingsBoard.
-   `send_oscillation(df_oscillation, token, host)`: Sends the calculated MoH telemetry to ThingsBoard.
-   `load_csv(csv_path)`: Loads a CSV file, validates its format, and returns a DataFrame.
-   `keys_validation(df, keys)`: Verifies that the telemetry keys exist in the DataFrame.
-   `MoH_calculation(df, telemetry_keys)`: Calculates the MoH metric on an hourly basis for the specified telemetry keys.
-   `filter_by_time(df, time_filter)`: Filters the DataFrame by a time period (e.g., '7D', '1M').

### Command-Line Usage

The `MoH.py` script can be executed from the terminal with several arguments:

-   `--csv <path>`: (Required) Path to the CSV file.
-   `--keys <key1> <key2> ...`: List of telemetry keys to send.
-   `--token <token_id>`: (Required) ThingsBoard device access token.
-   `--host <URL>`: (Optional) ThingsBoard API URL (default: `http://localhost:8080`).
-   `--list-columns`: Lists the available columns in the CSV and exits the program.
-   `--moh`: Activates the calculation and sending of the MoH metric.
-   `--time-filter <filter>`: Filters data by a specific time period (e.g., `7D`, `1M`).

### Dependencies

- `pandas`
- `requests`
- `argparse`
