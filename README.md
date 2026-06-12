# ThingsBoard Telemetry Toolkit

[![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python&logoColor=white)]()
[![Platform](https://img.shields.io/badge/Platform-ThingsBoard%20CE%20%2F%20PE-429DF0)]()
[![License](https://img.shields.io/badge/License-Apache--2.0-green)](LICENSE)

A set of Python tools to ingest, process, and visualise sensor telemetry in **ThingsBoard** — an open-source IoT platform. Designed for environments where raw sensor data (CSV exports from dataloggers or similar) needs to be pushed to a platform, processed with custom aggregations, and displayed in dashboards.

Built during real R&D work with industrial environmental sensors.

---

## What problem this solves

Industrial dataloggers and measurement devices often export raw data as CSV files. Getting that data into an IoT platform for visualisation and alerting typically requires manual work. This toolkit automates the ingestion pipeline and adds calculated metrics (Hourly Maximum Oscillation) on top, without requiring ThingsBoard PE rule nodes for the CE edition.

```
CSV export (datalogger/sensor)
        │
        ▼
  MoH.py / MoHBot.py          ← ingestion + calculation
        │
        ▼
  ThingsBoard API              ← telemetry stored per device
        │
        ▼
  Custom bar chart widget      ← visualisation dashboard
```

---

## Contents

| Component | Description |
|---|---|
| `CE/MoH.py` | CLI script — ingests CSV, calculates MoH, pushes to ThingsBoard CE |
| `CE/MoHBot.py` | Telegram chatbot interface for the same pipeline (user-friendly) |
| `PE/` | Rule chain JSON for ThingsBoard PE — aggregations without custom code |

---

## CE edition — CLI tool

### Install

```bash
git clone https://github.com/carnestoltes/chartsThingsBoard.git
cd chartsThingsBoard/CE
pip install pandas requests argparse
```

### Usage

```bash
# List available columns in your CSV
python3 MoH.py --csv data.csv --list-columns

# Upload a subset of data (last 7 days)
python3 MoH.py --csv data.csv --keys "Temperature" "Humidity" --token <device-token> --time-filter "7D"

# Upload and calculate Hourly Maximum Oscillation
python3 MoH.py --csv data.csv --keys "Temperature" --token <device-token> --time-filter "all" --moh
```

---

## CE edition — Telegram bot

For non-technical operators who need to trigger ingestion without a terminal:

```bash
pip install pandas requests argparse python-telegram-bot
# Set your bot token in MoHBot.py, then:
python3 MoHBot.py
```

In the chat: `/start` to begin, `/cancel` to abort.

---

## PE edition — rule chain

Import the `.json` files from `PE/` directly into ThingsBoard PE's rule chain editor. Includes aggregation chains for:

- Hourly Maximum Oscillation (MoH)
- Dewpoint calculation
- Absolute humidity

> **Note:** Update telemetry variable names inside each node to match your device's keys before importing.

---

## ThingsBoard widget setup

To visualise MoH data, create a **Time-Series Bar Chart** widget in ThingsBoard and set the data key to your calculated metric (e.g. `Temperature_MoH`). Screenshots of the expected result are in `images/`.

---

## Topics

`iot` `thingsboard` `mqtt` `telemetry` `python` `data-acquisition` `industrial-iot` `edge-computing` `raspberry-pi` `environmental-monitoring`


