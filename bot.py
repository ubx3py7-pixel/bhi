import random
import logging
import asyncio
import json
import os
import time
# ================== Ab yahan se aapka asli bot code shuru hota hai ==================
# Niche se pura code paste kar dena
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

# ================== LOGGING ==================
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ================== CONFIG ==================
BOT_TOKEN = "8463525599:AAHqiJAEWgTXls7y9pZuODiVTCXK-eBAN2U"
OWNER_ID = 6940098775                       # ← renamed for clarity
ADMIN_IDS = {1388092746}                    # ← made it set from beginning

AUTH_FILE = "authorized_users.json"
CREDITS_FILE = "user_credits.json"
REDEEM_CODES_FILE = "redeem_codes.json"

# ================== DATA ==================
authorized_users = {OWNER_ID} | ADMIN_IDS
user_credits = {}
user_last_commands = {}
redeem_codes = {}
user_data = {}
user_locks = {}

# ================== STATES ==================
TARGET_URL, GMAIL, CONFIRM_GMAIL, OTP, ANNOUNCEMENT = range(5)

# ================== NAMES ==================
first_names = ["Aarav", "Vihaan", "Mohammad", "Sai", "Advik", "Reyansh", "Aaradhya",
    "Ananya", "Aadhya", "Saanvi", "Diya", "Pihu", "Rajesh", "Sunita",
    "Amit", "Priya", "Vikram", "Neha", "Rohan", "Sneha", "Arjun", "Ishaan",
    "Kabir", "Ayaan", "Rudra", "Dhruv", "Kavya", "Myra", "Ira", "Zara",
    "Aditya", "Shivansh", "Riya", "Aryan", "Tara", "Krish", "Avni", "Shaurya",
    "Nitya", "Yash", "Siya", "Dev", "Navya", "Atharv", "Kiara", "Veer",
    "Anika", "Aryan", "Pari", "Rishi", "Mira", "Arnav", "Tanisha", "Samar",
    "Naira", "Rudransh", "Aarohi", "Reyansh", "Ishita", "Aadi", "Prisha",
    "Vivian", "Aarush", "Jiya", "Ahaan", "Anvi", "Kritan", "Suhana", "Yuvaan",
    "Riddhi", "Ayaansh", "Kyra", "Parth", "Aarna", "Ved", "Riyaansh", "Akira",
    "Kiaan", "Navika", "Harsh", "Avya", "Aviraj", "Shanaya", "Aarit", "Inaya",
    "Vivaan", "Ayesha", "Aarush", "Zoya", "Daksh", "Aahana", "Rudra", "Tia",
    "Arhaan", "Aarohi", "Reyan", "Niva", "Aariv", "Misha", "Aarush", "Rishaan"]

last_names = ["Sharma", "Patel", "Kumar", "Singh", "Gupta", "Yadav", "Verma",
    "Mehta", "Jain", "Reddy", "Khan", "Rao", "Joshi", "Mishra",
    "Agarwal", "Choudhary", "Thakur", "Maurya", "Sahu", "Bansal", 
    "Garg", "Malhotra", "Kapoor", "Saxena", "Tiwari", "Pandey", 
    "Trivedi", "Dwivedi", "Shukla", "Tripathi", "Dubey", "Pathak",
    "Upadhyay", "Nayak", "Behera", "Mohanty", "Das", "Sahoo",
    "Nayak", "Swain", "Pattnaik", "Mahapatra", "Senapati", "Pradhan",
    "Biswal", "Samal", "Rath", "Kar", "Lenka", "Sethi", "Bakshi"]

# ================== DATA PERSISTENCE ==================
def load_data():
    global authorized_users, user_credits, redeem_codes

    if os.path.exists(AUTH_FILE):
        try:
            with open(AUTH_FILE, 'r') as f:
                data = json.load(f)
                loaded_users = data.get('users', [])
                authorized_users = set(loaded_users)
                authorized_users.add(OWNER_ID)  # always keep owner
        except Exception as e:
            logger.error(f"Failed to load authorized users: {e}")
            authorized_users = {OWNER_ID} | ADMIN_IDS
    else:
        authorized_users = {OWNER_ID} | ADMIN_IDS

    if os.path.exists(CREDITS_FILE):
        try:
            with open(CREDITS_FILE, 'r') as f:
                user_credits = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load credits: {e}")

    if os.path.exists(REDEEM_CODES_FILE):
        try:
            with open(REDEEM_CODES_FILE, 'r') as f:
                redeem_codes = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load redeem codes: {e}")


def save_data():
    try:
        with open(AUTH_FILE, 'w') as f:
            json.dump({'users': list(authorized_users)}, f)
        with open(CREDITS_FILE, 'w') as f:
            json.dump(user_credits, f)
        with open(REDEEM_CODES_FILE, 'w') as f:
            json.dump(redeem_codes, f)
    except Exception as e:
        logger.error(f"Error saving data: {e}")


load_data()

# ================== HELPERS ==================
def is_authorized(user_id: int) -> bool:
    return user_id in authorized_users

def is_admin(user_id: int) -> bool:
    return user_id == OWNER_ID or user_id in ADMIN_IDS

def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID

def get_user_lock(user_id: int) -> asyncio.Lock:
    if user_id not in user_locks:
        user_locks[user_id] = asyncio.Lock()
    return user_locks[user_id]

# ================== MENU ==================
async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if is_owner(user_id):
        menu_text = (
            "👑 OWNER ADMIN MENU\n\n"
            "🚀 /report <– Click Start report\n"
            "➕ /add <user_id>\n"
            "➖ /remove <user_id>\n"
            "👥 /view\n"
            "👑 /addadmin <id>\n"
            "❌ /removeadmin <id>\n"
            "👑 /viewadmins\n"
            "📢 /announcement"
        )
    elif is_admin(user_id):
        menu_text = (
            "👑 ADMIN MENU\n\n"
            "🚀 /report <– Click Start report\n"
            "➕ /add <user_id>\n"
            "➖ /remove <user_id>\n"
            "👥 /view\n"
            "📢 /announcement"
        )
    else:
        menu_text = (
            "📌 COMMANDS\n\n"
            "🚀 /report <– Click Start report"
        )
    await update.message.reply_text(menu_text)

# ================== BASIC COMMANDS ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text(
            "❌ Unauthorized!\n\n"
            "Contact admin to get access. Use /myid to get your User ID."
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "✨ Welcome to TEAM LOVE MASS GVR FORM bot ✨\n\n"
        "Join Tg channel--> https://t.me/team_lovefamily  @od9_q\n"
        "TEAM LOVE\n"
        "Use /help to see commands"
    )
    await show_menu(update, context)
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_menu(update, context)

async def my_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    username = update.effective_user.username or "No username"
    await update.message.reply_text(
        f"🆔 Your Telegram User ID: `{user_id}`\n"
        f"👤 Username: @{username}",
        parse_mode='Markdown'
    )

# ================== ADMIN COMMANDS ==================
async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Only admins can add users!")
        return

    if not context.args:
        await update.message.reply_text("Usage: /add <user_id>")
        return

    try:
        new_id = int(context.args[0])
        if new_id not in authorized_users:
            authorized_users.add(new_id)
            save_data()
            await update.message.reply_text(f"✅ User {new_id} added successfully!")
        else:
            await update.message.reply_text(f"User {new_id} already authorized.")
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID!")

async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Only admins can remove users!")
        return

    if not context.args:
        await update.message.reply_text("Usage: /remove <user_id>")
        return

    try:
        rem_id = int(context.args[0])
        if rem_id == OWNER_ID:
            await update.message.reply_text("Cannot remove OWNER!")
            return
        authorized_users.discard(rem_id)
        ADMIN_IDS.discard(rem_id)
        save_data()
        await update.message.reply_text(f"✅ User {rem_id} removed.")
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID!")

async def view_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Only admins can view users!")
        return

    if not authorized_users:
        await update.message.reply_text("❌ No authorized users.")
        return

    user_list = "\n".join(map(str, sorted(authorized_users)))
    await update.message.reply_text(f"👥 Authorized Users:\n{user_list}")

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("❌ Only OWNER can add admins!")
        return

    if not context.args:
        await update.message.reply_text("Usage: /addadmin <user_id>")
        return

    try:
        new_admin = int(context.args[0])
        if new_admin not in ADMIN_IDS:
            ADMIN_IDS.add(new_admin)
            authorized_users.add(new_admin)
            save_data()
            await update.message.reply_text(f"✅ Admin {new_admin} added!")
        else:
            await update.message.reply_text(f"Admin {new_admin} already exists.")
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID!")

async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("❌ Only OWNER can remove admins!")
        return

    if not context.args:
        await update.message.reply_text("Usage: /removeadmin <user_id>")
        return

    try:
        rem_admin = int(context.args[0])
        if rem_admin == OWNER_ID:
            await update.message.reply_text("Cannot remove OWNER!")
            return
        ADMIN_IDS.discard(rem_admin)
        save_data()
        await update.message.reply_text(f"✅ Admin {rem_admin} removed.")
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID!")

async def view_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("❌ Only OWNER can view admins!")
        return

    if not ADMIN_IDS:
        await update.message.reply_text("❌ No normal admins found.")
        return

    admin_list = "\n".join(map(str, sorted(ADMIN_IDS)))
    await update.message.reply_text(f"Normal Admins:\n{admin_list}")

# ================== REPORT FLOW ==================
async def report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("❌ Unauthorized!")
        return ConversationHandler.END
    await update.message.reply_text("🔗 Target post/video URL bhejo:")
    return TARGET_URL

async def get_target_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("❌ Unauthorized!")
        return ConversationHandler.END
    user_data[user_id] = {'target_url': update.message.text.strip()}
    await update.message.reply_text("📧 Gmail Address bhejo:")
    return GMAIL

async def get_gmail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("❌ Unauthorized!")
        return ConversationHandler.END
    user_data[user_id]['gmail'] = update.message.text.strip()
    await update.message.reply_text("📧 Gmail Address confirm karo:")
    return CONFIRM_GMAIL

async def get_confirm_gmail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("❌ Unauthorized!")
        return ConversationHandler.END
    
    confirm_gmail = update.message.text.strip()
    gmail = user_data[user_id]['gmail']
    
    if gmail != confirm_gmail:
        await update.message.reply_text("❌ Gmail addresses match nahi kar rahe! Dobara try karo.")
        await update.message.reply_text("📧 Gmail Address bhejo:")
        return GMAIL
    
    first_name = random.choice(first_names)
    last_name = random.choice(last_names)
    full_name = f"{first_name} {last_name}"
    user_data[user_id]['full_name'] = full_name
    user_data[user_id]['first_name'] = first_name
    user_data[user_id]['last_name'] = last_name
    
    await update.message.reply_text(f"👤 Indian Name: {full_name}\n\n⚙️ Automation start ho raha hai...")
    
    lock = get_user_lock(user_id)
    async with lock:
        try:
            success = await run_automation(user_id, context)
            if success:
                return OTP
            else:
                await update.message.reply_text("❌ Kuch error aa gaya. Dobara try karo.")
                return ConversationHandler.END
        except Exception as e:
            logger.error(f"Error in automation for user {user_id}: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
            return ConversationHandler.END

async def get_otp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("❌ Unauthorized!")
        return ConversationHandler.END
    
    otp = update.message.text.strip()
    user_data[user_id]['otp'] = otp
    
    await update.message.reply_text("🔑 OTP receive kar raha hoon aur automation continue kar raha hoon...")
    
    lock = get_user_lock(user_id)
    async with lock:
        try:
            success = await continue_after_otp(user_id)
            if success:
                await update.message.reply_text("✅ Form successfully submit! New Report karne ke liye /report cmd Likho.")
                await show_menu(update, context)
            else:
                await update.message.reply_text("❌ Kuch error aa gaya. Dobara try karo.")
        except Exception as e:
            logger.error(f"Error after OTP for user {user_id}: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("❌ Unauthorized!")
        return ConversationHandler.END
    
    await update.message.reply_text("❌ Operation cancel ho gaya.", reply_markup=ReplyKeyboardRemove())
    
    lock = get_user_lock(user_id)
    async with lock:
        if user_id in user_data:
            data = user_data[user_id]
            if 'p' in data:
                try:
                    await data['p'].stop()
                except Exception as e:
                    logger.error(f"Error closing playwright for user {user_id}: {e}")
            user_data.pop(user_id, None)
    
    if user_id in user_locks:
        user_locks.pop(user_id, None)
    
    return ConversationHandler.END

async def run_automation(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    data = user_data[user_id]
    start_url = "https://help.meta.com/requests/1371776380779082/"
    target_content_url = data['target_url']
    gmail = data['gmail']
    confirm_gmail = gmail
    first_name = data['first_name']
    last_name = data['last_name']
    full_name = data['full_name']

    p = None
    browser = None
    try:
        p = await async_playwright().start()
        browser = await p.chromium.launch(headless=False, slow_mo=800)
        page = await browser.new_page()
        await page.set_viewport_size({"width": 1280, "height": 900})

        await context.bot.send_message(chat_id=user_id, text="🌐 Report page khul raha hai...")
        await page.goto(start_url, wait_until="networkidle", timeout=60000)

        await context.bot.send_message(chat_id=user_id, text="📱 Instagram option select kar raha hu...")
        await page.get_by_text("Instagram", exact=False).click(timeout=20000)
        await asyncio.sleep(3)

        await context.bot.send_message(chat_id=user_id, text="➡️ Pehla Next click...")
        await page.get_by_role("button", name="Next").click(timeout=15000)

        await context.bot.send_message(chat_id=user_id, text="⚠️ 'I want to report another issue' select kar raha hu...")
        await page.get_by_text("I want to report another issue", exact=False).click(timeout=20000)

        await context.bot.send_message(chat_id=user_id, text="➡️ Dusra Next...")
        await page.get_by_role("button", name="Next").click(timeout=15000)

        await context.bot.send_message(chat_id=user_id, text="👤 Behalf of myself/organization select...")
        await page.get_by_text("I am reporting on behalf of myself", exact=False).click(timeout=20000)
        await asyncio.sleep(1.5)

        await context.bot.send_message(chat_id=user_id, text="📝 Name aur organization fill kar raha hu...")
        await page.get_by_label("Your First Name").fill(first_name)
        await page.get_by_label("Your Last Name").fill(last_name)
        await page.get_by_label("Name of your organization").fill("Reporting agency")

        await context.bot.send_message(chat_id=user_id, text="📧 Email aur confirm email bhar raha hu...")
        await page.locator('input[type="email"], input[placeholder*="email"], #_r_12_').fill(gmail)
        await page.locator('input[placeholder*="confirm"], input[name*="confirm"], #_r_15_').fill(confirm_gmail)

        await context.bot.send_message(chat_id=user_id, text="🔑 Request code bhej raha hu...")
        await page.get_by_text("Request code", exact=False).click(timeout=20000)

        await context.bot.send_message(chat_id=user_id, text="🔑 \nEmail mein aaya OTP daalo:")

        user_data[user_id]['p'] = p
        user_data[user_id]['browser'] = browser
        user_data[user_id]['page'] = page

        return True

    except PlaywrightTimeoutError as e:
        logger.error(f"Timeout error for user {user_id}: {e}")
        await context.bot.send_message(chat_id=user_id, text=f"⏰ Timeout error: {e}")
        if p:
            await p.stop()
        return False
    except Exception as e:
        logger.error(f"Error in run_automation for user {user_id}: {e}")
        await context.bot.send_message(chat_id=user_id, text=f"❌ Error: {e}")
        if p:
            await p.stop()
        return False

async def continue_after_otp(user_id: int) -> bool:
    data = user_data[user_id]
    p = data['p']
    browser = data['browser']
    page = data['page']
    otp = data['otp']
    target_content_url = data['target_url']
    full_name = data['full_name']

    try:
        await page.locator('input[placeholder*="code"], input[name*="code"], #_r_18_').fill(otp)
        await page.get_by_role("button", name="Next").click(timeout=15000)

        await page.get_by_label("Please provide links (URLs)").fill(target_content_url)

        await page.get_by_label("Why are you reporting this content?").fill(
            "Hello instagram this user has been posting stuff on stories and Posts this violates instagram terms and policies please look at him and remove him. Thank you in advance."
        )

        await page.get_by_role("button", name="Next").click(timeout=15000)

        declaration_text = "By submitting this notice, you agree"
        await page.get_by_text(declaration_text, exact=False).locator('..').click(timeout=20000)
        await page.locator('input[type="checkbox"][aria-label*="Declaration"], input[type="checkbox"]').check(timeout=20000)

        await page.get_by_label("Electronic signature").fill(full_name)

        await page.get_by_role("button", name="Submit").click(timeout=20000)

        await asyncio.sleep(4)

        await page.get_by_text("New request", exact=False).click(timeout=20000)

        await p.stop()
        user_data.pop(user_id, None)

        if user_id in user_locks:
            user_locks.pop(user_id, None)

        return True

    except PlaywrightTimeoutError as e:
        logger.error(f"Timeout error after OTP for user {user_id}: {e}")
        await p.stop()
        user_data.pop(user_id, None)
        if user_id in user_locks:
            user_locks.pop(user_id, None)
        return False
    except Exception as e:
        logger.error(f"Error in continue_after_otp for user {user_id}: {e}")
        await p.stop()
        user_data.pop(user_id, None)
        if user_id in user_locks:
            user_locks.pop(user_id, None)
        return False

# ================== ANNOUNCEMENT ==================
async def announcement(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin only!")
        return ConversationHandler.END

    await update.message.reply_text("📢 Announcement message bhejo:")
    return ANNOUNCEMENT

async def send_announcement(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message.text
    for uid in list(authorized_users):
        try:
            await context.bot.send_message(chat_id=uid, text=f"📢 ANNOUNCEMENT 🔥\n\n{msg}")
        except Exception as e:
            logger.error(f"Failed to send to {uid}: {e}")
    await update.message.reply_text("✅ Announcement sabko bhej diya gaya.")
    return ConversationHandler.END

# ================== MAIN ==================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("report", report)],
        states={
            TARGET_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_target_url)],
            GMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gmail)],
            CONFIRM_GMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_confirm_gmail)],
            OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_otp)],
            ANNOUNCEMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_announcement)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("myid", my_id))
    app.add_handler(CommandHandler("add", add_user))
    app.add_handler(CommandHandler("remove", remove_user))
    app.add_handler(CommandHandler("view", view_users))
    app.add_handler(CommandHandler("addadmin", add_admin))
    app.add_handler(CommandHandler("removeadmin", remove_admin))
    app.add_handler(CommandHandler("viewadmins", view_admins))
    app.add_handler(conv_handler)

    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":

    main()
