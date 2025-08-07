import pandas as pd
import requests
import time
import argparse
import os
import sys

# --- Enviar datos a ThingsBoard ---
def enviar_datos(df, telemetry_keys, token, host):
    url = f'{host}/api/v1/{token}/telemetry'
    headers = {'Content-Type': 'application/json'}

    print(f"Se cargaron {len(df)} registros originales del CSV.")

    for index, row in df.iterrows():
        timestamp_ms = int(row['Timestamp'].timestamp() * 1000) # ThingsBoard work with miliseconds
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
            response.raise_for_status() # Fail error HTTP (4xx o 5xx)
            if index % 100 == 0:
                print(f"Data progress: {index}/{len(df)} send.")
        except requests.exceptions.RequestException as e:
            print(f"Fail to send a data to ThingsBoard: {e}")
            print(f"Payload fails: {payload}")
        except Exception as e:
            print(f"Unexpected error in row {index}: {e}")
            print(f"Payload number: {payload}")
    
    print("Process success.")

# --- Function for send the oscilation to ThingsBoard ---
def enviar_oscilacion(df_oscilacion, token, host):
    url = f'{host}/api/v1/{token}/telemetry'
    headers = {'Content-Type': 'application/json'}

    print(f"Load {len(df_oscilacion)} records to send.")

    for index, row in df_oscilacion.iterrows():
        # The index of df_oscilacion is the timestamp 
        timestamp_ms = int(index.timestamp() * 1000) 
        
        # Each column df_oscilacion its a key
        values = {col: row[col] for col in df_oscilacion.columns if pd.notnull(row[col])}
        
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
def cargar_csv(csv_path):
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

def validar_claves(df, keys):
   claves_faltantes = [key for key in keys if key not in df.columns]
   if claves_faltantes:
     raise KeyError(f"Error: Missing keys into CSV: {', '.join(claves_faltantes)}")

# --- Function for calculate the MoH ---
def calcular_oscilacion_horaria(df, telemetry_keys):
    print("Processing ...")
    oscilacion_df = pd.DataFrame()
    for key in telemetry_keys:
        if key in df.columns:
            # Obteining a min, max with an interval of one hour
            df[key] = pd.to_numeric(df[key], errors='coerce') # Convertir a numérico, forzando NaN si hay errores
            hourly_min = df[key].resample('H').min()
            hourly_max = df[key].resample('H').max()
            
            # Diference between max and min
            oscilacion = hourly_max - hourly_min
            
            # Assing a descriptive name for variable
            oscilacion_df[f'{key}_MoH'] = oscilacion 
        else:
            print(f"Advertencia: La clave '{key}' no se encontró en el DataFrame para calcular la oscilación.")
    
    # Delete a NaN columns 
    oscilacion_df = oscilacion_df.dropna()
    print("Finish the compute of MoH.")
    return oscilacion_df

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

    args = parser.parse_args()

    try:
        df = cargar_csv(args.csv)

        if args.list_columns:
            print("Parameters into CSV:")
            # Excluded 'Timestamp' because is the index of DataFrame
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

        # Rebuild for use Timestamp like column and not like an index
        validar_claves(df.reset_index(), args.keys)

        # Send original data
        enviar_datos(df.reset_index(), args.keys, args.token, args.host)

        # Structure for send MoH data
        if args.moh:
            moh_df = calcular_oscilacion_horaria(df, args.keys) # A DataFrame index
            if not moh_df.empty:
                enviar_oscilacion(moh_df, args.token, args.host)
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
