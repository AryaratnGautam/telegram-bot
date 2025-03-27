import csv
import random
import telebot
import os
import pandas as pd
import ssl
from dotenv import load_dotenv

# ✅ Load environment variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

# ✅ Ensure token is valid
if not TOKEN or ":" not in TOKEN:
    raise ValueError("Invalid Telegram Bot Token. Please check your .env file.")

bot = telebot.TeleBot(TOKEN)

# ✅ Ensure ADMIN_ID is a valid number
if not ADMIN_ID or not ADMIN_ID.isdigit():
    raise ValueError("Invalid ADMIN_ID. Please enter a valid numeric Telegram ID in .env file.")
ADMIN_ID = int(ADMIN_ID)

# ✅ CSV File Storage
CSV_FOLDER = "csv_files"
os.makedirs(CSV_FOLDER, exist_ok=True)
USER_CODES_FILE = "user_codes.xlsx"

def load_csv_data():
    """Load all CSV data into a set for quick lookup"""
    accounts = set()
    for file in os.listdir(CSV_FOLDER):
        if file.endswith(".csv"):
            try:
                df = pd.read_csv(os.path.join(CSV_FOLDER, file), header=None)
                accounts.update(df[0].astype(str).str.strip())
            except Exception as e:
                print(f"Error loading {file}: {e}")
    return accounts

def load_user_data():
    """Load user codes from Excel"""
    if os.path.exists(USER_CODES_FILE):
        try:
            return pd.read_excel(USER_CODES_FILE)
        except Exception as e:
            print(f"Error reading {USER_CODES_FILE}: {e}")
    return pd.DataFrame(columns=["Name", "Code", "UserID"])

def is_user_verified(user_id):
    """Check if the user is already verified"""
    df = load_user_data()
    return str(user_id) in df["UserID"].astype(str).values

def save_user_data(name, code, user_id):
    """Save user data to Excel file without duplication"""
    df = load_user_data()
    if str(user_id) in df["UserID"].astype(str).values:
        return  # User already exists, do nothing
    new_data = pd.DataFrame([[name, code, user_id]], columns=["Name", "Code", "UserID"])
    df = pd.concat([df, new_data], ignore_index=True)
    df.to_excel(USER_CODES_FILE, index=False)

@bot.message_handler(commands=['start'])
def start(message):
    if is_user_verified(message.chat.id):
        bot.send_message(message.chat.id, "✅ You are already verified!")
        return
    bot.send_message(message.chat.id, "👋 Welcome! Please enter your name:")
    bot.register_next_step_handler(message, get_name)

def get_name(message):
    user_name = message.text.strip()
    bot.send_message(message.chat.id, f"Hello {user_name}! Please enter your first Demat account number:")
    bot.register_next_step_handler(message, lambda msg: verify_account(msg, user_name, []))

def verify_account(message, user_name, verified_accounts):
    account_number = message.text.strip()
    csv_data = load_csv_data()
    if account_number.lower() == 'done':
        if verified_accounts:
            unique_code = str(random.randint(100000000, 999999999))
            save_user_data(user_name, unique_code, message.chat.id)
            bot.send_message(message.chat.id, f"🎉 Verification complete! Your unique code is: {unique_code}")
        else:
            bot.send_message(message.chat.id, "❌ No accounts verified. Please restart.")
    elif account_number in csv_data:
        verified_accounts.append(account_number)
        bot.send_message(message.chat.id, f"✅ Account {account_number} is verified. Enter next account number or type 'done':")
        bot.register_next_step_handler(message, lambda msg: verify_account(msg, user_name, verified_accounts))
    else:
        bot.send_message(message.chat.id, "❌ Account not found. Try again:")
        bot.register_next_step_handler(message, lambda msg: verify_account(msg, user_name, verified_accounts))

@bot.message_handler(commands=['upload'])
def upload_csv(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ You are not authorized to upload CSV files.")
        return
    bot.send_message(message.chat.id, "📤 Send me the CSV file to upload.")
    bot.register_next_step_handler(message, save_csv)

def save_csv(message):
    if not message.document or not message.document.file_name.endswith(".csv"):
        bot.send_message(message.chat.id, "❌ Please upload a valid CSV file.")
        return
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        file_path = os.path.join(CSV_FOLDER, message.document.file_name)
        with open(file_path, 'wb') as f:
            f.write(downloaded_file)
        bot.send_message(message.chat.id, "✅ CSV uploaded successfully!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ File upload failed: {e}")

@bot.message_handler(commands=['get_codes'])
def get_codes(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ You are not authorized to access user codes.")
        return
    df = load_user_data()
    if df.empty:
        bot.send_message(message.chat.id, "❌ No users verified yet.")
    else:
        file_path = "user_codes.xlsx"
        df.to_excel(file_path, index=False)
        with open(file_path, "rb") as f:
            bot.send_document(message.chat.id, f)

print("Bot is running...")
bot.polling(none_stop=True)
