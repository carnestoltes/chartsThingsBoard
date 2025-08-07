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
        timestamp_ms = int(row['Timestamp'].timestamp() * 1000) # ThingsBoard espera timestamps en milisegundos
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
            response.raise_for_status() # Lanza una excepción para errores HTTP (4xx o 5xx)
            if index % 100 == 0:
                print(f"Progreso envío datos originales: {index}/{len(df)} registros enviados.")
        except requests.exceptions.RequestException as e:
            print(f"Error al enviar datos originales a ThingsBoard: {e}")
            print(f"Payload que falló: {payload}")
        except Exception as e:
            print(f"Error inesperado en la fila {index} (datos originales): {e}")
            print(f"Payload que falló: {payload}")
    
    print("Proceso de envío de datos originales completado.")

# --- Función para enviar datos de oscilación a ThingsBoard ---
def enviar_oscilacion(df_oscilacion, token, host):
    url = f'{host}/api/v1/{token}/telemetry'
    headers = {'Content-Type': 'application/json'}

    print(f"Se cargarán {len(df_oscilacion)} registros de oscilación para enviar.")

    for index, row in df_oscilacion.iterrows():
        # El índice de df_oscilacion ya es el timestamp para la oscilación horaria
        timestamp_ms = int(index.timestamp() * 1000) 
        
        # Cada columna de df_oscilacion es una clave de oscilación (ej. Temperature_MoH)
        values = {col: row[col] for col in df_oscilacion.columns if pd.notnull(row[col])}
        
        payload = {
            "ts": timestamp_ms,
            "values": values
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            print(f"Progreso envío oscilación: {index} enviado. Datos: {values}")
        except requests.exceptions.RequestException as e:
            print(f"Error al enviar datos de oscilación a ThingsBoard: {e}")
            print(f"Payload que falló: {payload}")
        except Exception as e:
            print(f"Error inesperado al enviar oscilación en {index}: {e}")
            print(f"Payload que falló: {payload}")
    
    print("Proceso de envío de oscilación completado.")

# --- Cargar datos del CSV ---
def cargar_csv(csv_path):
    try:
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Error: El archivo CSV no se encontró en {csv_path}")

        df = pd.read_csv(csv_path, sep=';')
        if 'Timestamp' not in df.columns:
            raise KeyError("Error: Falta la columna 'Timestamp' en el CSV.")
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        df = df.sort_values(by='Timestamp')
        df = df.set_index('Timestamp')
        return df
    except KeyError as e:
        print(f"Error: Falta una columna esperada en el CSV. Detalles: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error al leer el CSV: {e}")
        sys.exit(1)

def validar_claves(df, keys):
   claves_faltantes = [key for key in keys if key not in df.columns]
   if claves_faltantes:
     raise KeyError(f"Error: Estas claves de telemetría no se encuentran en el CSV: {', '.join(claves_faltantes)}")

# --- Función para calcular la oscilación horaria ---
def calcular_oscilacion_horaria(df, telemetry_keys):
    print("Calculando oscilación horaria...")
    oscilacion_df = pd.DataFrame()
    for key in telemetry_keys:
        if key in df.columns:
            # Resampleo a intervalos de una hora ('H') y calculo min y max
            df[key] = pd.to_numeric(df[key], errors='coerce') # Convertir a numérico, forzando NaN si hay errores
            hourly_min = df[key].resample('H').min()
            hourly_max = df[key].resample('H').max()
            
            # Calculo la diferencia (oscilación)
            oscilacion = hourly_max - hourly_min
            
            # Asignar la columna al DataFrame de oscilación con un nombre descriptivo (ej. Temperature_MoH)
            oscilacion_df[f'{key}_MoH'] = oscilacion 
        else:
            print(f"Advertencia: La clave '{key}' no se encontró en el DataFrame para calcular la oscilación.")
    
    # Eliminar filas con NaN (horas sin datos o con valores no numéricos para la oscilación)
    oscilacion_df = oscilacion_df.dropna()
    print("Cálculo de oscilación horaria completado.")
    return oscilacion_df

# --- Función principal (main) ---
def main():
    parser = argparse.ArgumentParser(description="Subida de telemetría(s) a Thingsboard desde un CSV y cálculo de Máxima Oscilación Horaria (MoH)")

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    parser.add_argument('--csv', required=True, help='Ruta al archivo CSV completo')
    parser.add_argument('--keys', nargs='+', help='Listado de parámetros de telemetría a enviar (ej. --keys "Temperature" "Relative humidity")')
    parser.add_argument('--token', help='Token de acceso del dispositivo en ThingsBoard')
    parser.add_argument('--host', default='http://localhost:8080', help='URL del host donde esta desplegado ThingsBoard (por defecto: http://localhost:8080)')
    parser.add_argument('--list-columns', action='store_true', help='Muestra columnas de telemetría contenidas en el CSV y sale')
    parser.add_argument('--moh', action='store_true', help='Calcula y envía la Máxima Oscilación Horaria (MoH) para las claves de telemetría especificadas.') 

    args = parser.parse_args()

    try:
        df = cargar_csv(args.csv)

        if args.list_columns:
            print("Parámetros disponibles en el CSV:")
            # Excluir 'Timestamp' ya que ahora es el índice del DF
            print(" - " + "\n - ".join(col for col in df.columns)) 
            sys.exit(0)
        
        if not args.keys:
            print("Error: Debes proporcionar al menos una clave de telemetría con --keys o usar --list-columns para ver las disponibles.")
            parser.print_help(sys.stderr)
            sys.exit(1)
        
        if not args.token:
            print("Error: Debes proporcionar el token de acceso del dispositivo con --token.")
            parser.print_help(sys.stderr)
            sys.exit(1)

        # Evalua la columna Timestamp como columna regular y no como índice
        validar_claves(df.reset_index(), args.keys)

        # Enviar telemetría original
        enviar_datos(df.reset_index(), args.keys, args.token, args.host)

        # Lógica para calcular y enviar la oscilación MoH si se solicita
        if args.moh:
            moh_df = calcular_oscilacion_horaria(df, args.keys) # Usa el DF con Timestamp como índice
            if not moh_df.empty:
                enviar_oscilacion(moh_df, args.token, args.host)
            else:
                print("No se generaron datos de Máxima Oscilación Horaria (MoH) para enviar.")

    except FileNotFoundError as e:
        print(f"Error de archivo: {e}")
        sys.exit(1)
    except KeyError as e:
        print(f"Error de columna en CSV: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error de ejecución: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
