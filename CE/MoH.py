"""
File Name:           MoH.py
Description:         Script for upload the raw data to ThingsBoards platform and optionally computes the MoH metric.
Author:              Rubén Rodríguez Navarro
Creation Date:       2025-07-28
Last Modified Date:  2025-08-10
Version:             1.2.0
License:             Apache 2.0
Notes:
    - It's mandatory use a token ID for reference the node which will have the data.
    
"""
import pandas as pd
import requests
import time
import argparse
import os
import sys

# --- Rounding function ---
def round_to(num, decimals):
    """A Python implementation of the JavaScript Math.round-like function."""
    if isinstance(num, (int, float)):
        return round(num * (10 ** decimals)) / (10 ** decimals)
    return num

# --- Send data to ThingsBoard ---
def send_data(df, telemetry_keys, token, host):
    url = f'{host}/api/v1/{token}/telemetry'
    headers = {'Content-Type': 'application/json'}

    print(f"Load {len(df)} registries from CSV.")
    total_records = len(df)
    
    for index, row in df.iterrows():
        timestamp_ms = int(row['Timestamp'].timestamp() * 1000)
        values = {}
        for key in telemetry_keys:
            if key in row and pd.notnull(row[key]):
                values[key] = row[key]
        
        payload = {
            "ts": timestamp_ms,
            "values": values
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            if index % 100 == 0:
                # Updated progress message
                print(f"Progress: Records sent {index+1}/{total_records}.")
        except requests.exceptions.RequestException as e:
            print(f"Fail to send a data to ThingsBoard: {e}")
            print(f"Payload fails: {payload}")
        except Exception as e:
            print(f"Unexpected error in row {index}: {e}")
            print(f"Payload number: {payload}")
    
    print("Process success.")

# --- Function for send the oscilation to ThingsBoard ---
def send_oscillation(df_oscillation, token, host):
    url = f'{host}/api/v1/{token}/telemetry'
    headers = {'Content-Type': 'application/json'}

    print(f"Load {len(df_oscillation)} records to send.")

    for index, row in df_oscillation.iterrows():
        timestamp_ms = int(index.timestamp() * 1000)
        
        values = {col: round_to(row[col], 3) for col in df_oscillation.columns if pd.notnull(row[col])}
        
        payload = {
            "ts": timestamp_ms,
            "values": values
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            print(f"Progress sending oscillations: {index}. Data: {values}")
        except requests.exceptions.RequestException as e:
            print(f"Error sending oscillation data to ThingsBoard: {e}")
            print(f"Payload failed: {payload}")
        except Exception as e:
            print(f"Unexpected error sending oscillation with index {index}: {e}")
            print(f"Payload failed: {payload}")
    
    print("Send oscillation succed.")

# --- Load data to CSV ---
def load_csv(csv_path):
    try:
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Error: CSV file don't find it {csv_path}")

        df = pd.read_csv(csv_path, sep=';')
        if 'Timestamp' not in df.columns:
            raise KeyError("Error: Cannot find 'Timestamp' column into CSV.")
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        df = df.sort_values(by='Timestamp')
        df = df.set_index('Timestamp')
        return df
    except KeyError as e:
        print(f"Error: Missing column into CSV. Details: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Cannot read the CSV: {e}")
        sys.exit(1)

def keys_validation(df, keys):
   missing_keys = [key for key in keys if key not in df.columns]
   if missing_keys:
     raise KeyError(f"Error: Missing keys into CSV: {', '.join(missing_keys)}")

# --- Function for calculate the MoH ---
def MoH_calculation(df, telemetry_keys):
    print("Processing ...")
    oscillation_df = pd.DataFrame()
    for key in telemetry_keys:
        if key in df.columns:
            # Obteining a min, max with an interval of one hour
            df[key] = pd.to_numeric(df[key], errors='coerce')
            hourly_min = df[key].resample('H').min()
            hourly_max = df[key].resample('H').max()
            
            # Diference between max and min
            oscillation = hourly_max - hourly_min
            
            # Assing a descriptive name for variable
            oscillation_df[f'{key}_MoH'] = oscillation
        else:
            print(f"Warning: The key '{key}' not found into DataFrame. MoH will not be computed for this key.")
    
    oscillation_df = oscillation_df.dropna()
    print("Finish the compute of MoH.")
    return oscillation_df

# --- Function to filter data by time period ---
def filter_by_time(df, time_filter):
    try:
        end_time = df.index.max()
        period = time_filter[-1].upper()
        number = int(time_filter[:-1])
        
        if period == 'D':
            start_time = end_time - pd.DateOffset(days=number)
        elif period == 'M':
            start_time = end_time - pd.DateOffset(months=number)
        elif period == 'Y':
            start_time = end_time - pd.DateOffset(years=number)
        else:
            print(f"Invalid time filter format: '{time_filter}'. Using all data.")
            return df
        
        filtered_df = df[df.index >= start_time]
        print(f"Data filtered from {start_time} to {end_time}.")
        return filtered_df
        
    except (ValueError, IndexError):
        print(f"Invalid time filter format: '{time_filter}'. Using all data.")
        return df
    except Exception as e:
        print(f"Error during time filtering: {e}. Using all data.")
        return df

# --- Main ---
def main():
    parser = argparse.ArgumentParser(description="Upload telemetries to ThingsBoard with CSV file with MoH implementation")

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    parser.add_argument('--csv', required=True, help='Requires absolute path locates')
    parser.add_argument('--keys', nargs='+', help='List of parameters to send (ex. --keys "Temperature" "Relative humidity")')
    parser.add_argument('--token', help='ThingsBoard access token')
    parser.add_argument('--host', default='http://localhost:8080', help='ThingsBoard URL API (default: http://localhost:8080)')
    parser.add_argument('--list-columns', action='store_true', help='List of parameters contained into CSV')
    parser.add_argument('--moh', action='store_true', help='Compute and send MoH telemetry')
    parser.add_argument('--time-filter', help='Filter data by a specific time period (e.g., "7D" for 7 days, "1M" for 1 month)')

    args = parser.parse_args()

    try:
        df = load_csv(args.csv)

        if args.list_columns:
            print("Parameters into CSV:")
            print(" - " + "\n - ".join(col for col in df.columns)) 
            sys.exit(0)
        
        if not args.keys:
            print("Error: You should give at least one key --keys or use --list-columns for obtain the available parameters.")
            parser.print_help(sys.stderr)
            sys.exit(1)
        
        if not args.token:
            print("Error: You should give a token ID --token.")
            parser.print_help(sys.stderr)
            sys.exit(1)
        
        if args.time_filter:
            df = filter_by_time(df, args.time_filter)

        keys_validation(df.reset_index(), args.keys)

        send_data(df.reset_index(), args.keys, args.token, args.host)

        if args.moh:
            moh_df = MoH_calculation(df, args.keys)
            if not moh_df.empty:
                send_oscillation(moh_df, args.token, args.host)
            else:
                print("MOH data empty.")

    except FileNotFoundError as e:
        print(f"File error: {e}")
        sys.exit(1)
    except KeyError as e:
        print(f"Column error into CSV: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Load error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
