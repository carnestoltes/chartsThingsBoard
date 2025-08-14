"""
File Name:           MoHBot.py
Description:         Script for upload the raw data to ThingsBoards platform and optionally computes the MoH metric using chatbot from Telegram.
Author:              Rubén Rodríguez Navarro
Creation Date:       2025-08-10
Last Modified Date:  2025-08-10
Version:             1.2.0
License:             Apache 2.0
Notes:
    - It's mandatory use a token ID for reference the node which will have the data.
    - It's mandatory specify the token ID from chatbot.
    
"""

import logging
import subprocess
import os
import asyncio
import pandas as pd
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackContext,
)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define conversation states
UPLOAD_CSV, GET_TOKEN, GET_KEYS, GET_HOST, GET_TIME_PERIOD, GET_MOH_OPTION, CONFIRM_RUN = range(7)

# --- Define the functions for the bot's conversation flow ---

async def start(update: Update, context: CallbackContext) -> int:
    """Sends a message to the user and starts the conversation."""
    await update.message.reply_text(
        "Hello! I am a bot that uploads CSV data to ThingsBoard using your MoH script. "
        "Please, upload your CSV file to begin."
    )
    return UPLOAD_CSV

async def upload_csv(update: Update, context: CallbackContext) -> int:
    """Handles the uploaded file, verifies it's a CSV, and asks for the token."""
    if update.message.document:
        file_info = update.message.document
        
        if not file_info.file_name.endswith('.csv'):
            await update.message.reply_text("The file must be a .csv file. Please try again.")
            return UPLOAD_CSV

        file = await context.bot.get_file(file_info.file_id)
        file_path = f'./{file_info.file_name}'
        await file.download_to_drive(file_path)

        context.user_data['csv_path'] = file_path

        try:
            df = pd.read_csv(file_path, sep=';')
            columns = [col for col in df.columns if col != 'Timestamp']
            if not columns:
                await update.message.reply_text("The CSV file seems to be empty or has no columns besides 'Timestamp'. Please try again with a valid file.")
                os.remove(file_path)
                return UPLOAD_CSV
            
            context.user_data['available_columns'] = columns

            await update.message.reply_text(
                f"CSV file '{file_info.file_name}' received.\n\n"
                f"Available columns:\n- " + "\n- ".join(columns) + 
                "\n\nNow, please provide the **ThingsBoard access token** for the device."
            )
            return GET_TOKEN
        except Exception as e:
            await update.message.reply_text(f"Error reading CSV file: {e}. Please try again.")
            os.remove(file_path)
            return UPLOAD_CSV
    else:
        await update.message.reply_text("Please upload a CSV file.")
        return UPLOAD_CSV

async def get_token(update: Update, context: CallbackContext) -> int:
    """Gets the ThingsBoard token from the user."""
    token = update.message.text
    context.user_data['token'] = token
    
    await update.message.reply_text(
        "Token received. Now, from the list of available columns, "
        "please provide the **telemetry keys** you want to upload, separated by spaces."
    )
    return GET_KEYS

async def get_keys(update: Update, context: CallbackContext) -> int:
    """Gets the telemetry keys from the user."""
    keys_input = update.message.text
    keys = keys_input.split()
    
    available_columns = context.user_data.get('available_columns', [])
    invalid_keys = [key for key in keys if key not in available_columns]

    if invalid_keys:
        await update.message.reply_text(
            f"The following keys are not in the CSV: {', '.join(invalid_keys)}. "
            "Please provide valid keys from the list, separated by spaces."
        )
        return GET_KEYS
    
    context.user_data['keys'] = keys
    
    await update.message.reply_text(
        "Keys received. "
        "The default ThingsBoard host is 'http://localhost:8080'. "
        "Would you like to use a different host? If so, please send me the URL. "
        "Otherwise, type 'default' to proceed with the default host."
    )
    return GET_HOST

async def get_host(update: Update, context: CallbackContext) -> int:
    """Gets the host from the user and prepares to get the time filter."""
    user_input = update.message.text
    if user_input.lower() == 'default':
        host = 'http://localhost:8080'
    else:
        if not user_input.startswith(('http://', 'https://')):
            await update.message.reply_text("That doesn't look like a valid URL. Please send a valid host URL or type 'default'.")
            return GET_HOST
        host = user_input
    
    context.user_data['host'] = host
    
    await update.message.reply_text(
        f"ThingsBoard host set to: {host}. "
        "Now, please provide a time filter for the data. "
        "For example, type '7D' for the last 7 days, '1M' for the last month, or 'all' to upload all data."
    )
    return GET_TIME_PERIOD

async def get_time_period(update: Update, context: CallbackContext) -> int:
    """Gets the time filter from the user and prepares to get the MoH option."""
    time_filter = update.message.text
    context.user_data['time_filter'] = time_filter
    
    await update.message.reply_text(
        f"Time filter set to: {time_filter}. "
        "Would you like to compute and upload the **MoH metric** for the selected telemetry? (yes/no)"
    )
    return GET_MOH_OPTION

async def get_moh_option(update: Update, context: CallbackContext) -> int:
    """Gets the MoH computation option from the user."""
    moh_option = update.message.text.lower()
    if moh_option in ['yes', 'y']:
        context.user_data['compute_moh'] = True
    elif moh_option in ['no', 'n']:
        context.user_data['compute_moh'] = False
    else:
        await update.message.reply_text("Invalid option. Please respond with 'yes' or 'no'.")
        return GET_MOH_OPTION
    
    await update.message.reply_text(
        f"MoH computation is set to: {context.user_data['compute_moh']}. "
        "Ready to run the script. Please confirm by typing 'run'."
    )
    return CONFIRM_RUN

async def run_moh_script(update: Update, context: CallbackContext) -> int:
    """Executes the MoH.py script with the gathered data and shows real-time progress."""
    if update.message.text.lower() != 'run':
        await update.message.reply_text("Please type 'run' to confirm.")
        return CONFIRM_RUN

    csv_path = context.user_data.get('csv_path')
    token = context.user_data.get('token')
    keys = context.user_data.get('keys')
    host = context.user_data.get('host')
    time_filter = context.user_data.get('time_filter')
    compute_moh = context.user_data.get('compute_moh', False)
    
    if not all([csv_path, token, keys, host, time_filter]):
        await update.message.reply_text("Something went wrong. Please start again with /start.")
        return ConversationHandler.END
    
    progress_message = await update.message.reply_text(
        "Starting data upload... Please wait for progress updates."
    )
    progress_message_id = progress_message.message_id
    
    try:
        command = [
            'python', 'MoH.py',
            '--csv', csv_path,
            '--keys', *keys,
            '--token', token,
            '--host', host
        ]

        if compute_moh:
            command.append('--moh')
        
        if time_filter.lower() != 'all':
            command.extend(['--time-filter', time_filter])
        
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        while True:
            stdout_line = process.stdout.readline()
            stderr_line = process.stderr.readline()

            if not stdout_line and not stderr_line and process.poll() is not None:
                break
            
            if stdout_line:
                if "Progress: Records sent" in stdout_line:
                    await context.bot.edit_message_text(
                        chat_id=update.effective_chat.id,
                        message_id=progress_message_id,
                        text=stdout_line.strip()
                    )
                else:
                    await update.message.reply_text(stdout_line.strip())

            if stderr_line:
                await update.message.reply_text(f" **Error:** {stderr_line.strip()}")
            
            await asyncio.sleep(0.1)

        if process.returncode == 0:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=progress_message_id,
                text=f"Upload completed successfully!"
            )
        else:
            await update.message.reply_text(f" Script finished with an error. Check the messages above for details.")
    
    except FileNotFoundError:
        await update.message.reply_text("The 'MoH.py' script was not found. Please ensure it is in the same directory as the bot.")
    finally:
        if os.path.exists(csv_path):
            os.remove(csv_path)

    return ConversationHandler.END

async def cancel(update: Update, context: CallbackContext) -> int:
    """Cancels and ends the conversation."""
    if 'csv_path' in context.user_data and os.path.exists(context.user_data['csv_path']):
        os.remove(context.user_data['csv_path'])
    await update.message.reply_text('Operation cancelled. You can start again with /start.')
    return ConversationHandler.END

def main():
    """Start the bot."""
    bot_token = "" 
    
    application = Application.builder().token(bot_token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            UPLOAD_CSV: [MessageHandler(filters.Document.FileExtension('csv'), upload_csv)],
            GET_TOKEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_token)],
            GET_KEYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_keys)],
            GET_HOST: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_host)],
            GET_TIME_PERIOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_time_period)],
            GET_MOH_OPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_moh_option)],
            CONFIRM_RUN: [MessageHandler(filters.TEXT & ~filters.COMMAND, run_moh_script)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == '__main__':
    main()
