# MoHBot Module

## Description

The `MoHBot` module is a Telegram bot that interacts with the user to gather the necessary information and then executes the `MoH.py` script. It guides the user through a conversation to upload a CSV file and configure the upload parameters to ThingsBoard.

### Conversation Flow

The bot uses a `ConversationHandler` to manage a conversational flow with the user through several states:

1.  **`start`**: Initiates the conversation, asking the user to upload a CSV file.
2.  **`upload_csv`**: Handles the uploaded file, validates that it is a CSV, saves it temporarily, and shows the available columns.
3.  **`get_token`**: Prompts for the ThingsBoard access token.
4.  **`get_keys`**: Asks for the telemetry keys to upload and validates them against the CSV columns.
5.  **`get_host`**: Allows the user to specify a ThingsBoard URL or use the default one.
6.  **`get_time_period`**: Asks for a time filter for the data (e.g., '7D', 'all').
7.  **`get_moh_option`**: Asks whether the MoH metric should be calculated and uploaded.
8.  **`run_moh_script`**: Executes the `MoH.py` script with the collected parameters and shows real-time progress.
9.  **`cancel`**: Cancels the operation and removes the temporary CSV file.

### Dependencies

-   `python-telegram-bot`
-   `pandas`
-   `subprocess`
-   `os`
-   `asyncio`
