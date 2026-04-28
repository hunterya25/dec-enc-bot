# ============================================================
#   🔐 TELEGRAM ENCRYPTION / DECRYPTION BOT — FINAL FIXED
#   Library : python-telegram-bot v22.x
#   OS Fix  : Windows asyncio event loop fix included
# ============================================================

import logging
import base64
import os
import hashlib
import asyncio

from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

# ─── Load .env ────────────────────────────────────────────────
load_dotenv()

# ─── Logging ──────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── Bot Token ────────────────────────────────────────────────
TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_BOT_TOKEN_HERE")

# ─── ConversationHandler States ───────────────────────────────
CHOOSE_METHOD     = 0
WAIT_ENC_MSG      = 1
WAIT_DEC_MSG      = 2
WAIT_CAESAR_SHIFT = 3
WAIT_CAESAR_MSG   = 4
WAIT_VIG_KEY      = 5
WAIT_VIG_MSG      = 6
WAIT_CUSTOM_KEY   = 7
WAIT_CUSTOM_MSG   = 8
WAIT_DEC_CUSTOM   = 9

# ─── Per-user Storage ─────────────────────────────────────────
user_data_store: dict = {}


# ╔══════════════════════════════════════════════════════════════╗
# ║               🔧  ENCRYPTION UTILITIES                       ║
# ╚══════════════════════════════════════════════════════════════╝

def get_fernet_key() -> bytes:
    secret = os.getenv("FERNET_KEY")
    if secret:
        return secret.encode()
    return Fernet.generate_key()

DEFAULT_KEY = get_fernet_key()

def fernet_encrypt(plain: str, key: bytes = DEFAULT_KEY) -> str:
    return Fernet(key).encrypt(plain.encode()).decode()

def fernet_decrypt(token: str, key: bytes = DEFAULT_KEY) -> str:
    return Fernet(key).decrypt(token.encode()).decode()

def caesar_encrypt(plain: str, shift: int) -> str:
    result = []
    for ch in plain:
        if ch.isalpha():
            base = ord('A') if ch.isupper() else ord('a')
            result.append(chr((ord(ch) - base + shift) % 26 + base))
        else:
            result.append(ch)
    return "".join(result)

def caesar_decrypt(cipher: str, shift: int) -> str:
    return caesar_encrypt(cipher, -shift)

def base64_encode(plain: str) -> str:
    return base64.b64encode(plain.encode()).decode()

def base64_decode(encoded: str) -> str:
    return base64.b64decode(encoded.encode()).decode()

def vigenere_encrypt(plain: str, key: str) -> str:
    key = key.lower()
    result, ki = [], 0
    for ch in plain:
        if ch.isalpha():
            shift = ord(key[ki % len(key)]) - ord('a')
            base  = ord('A') if ch.isupper() else ord('a')
            result.append(chr((ord(ch) - base + shift) % 26 + base))
            ki += 1
        else:
            result.append(ch)
    return "".join(result)

def vigenere_decrypt(cipher: str, key: str) -> str:
    key = key.lower()
    result, ki = [], 0
    for ch in cipher:
        if ch.isalpha():
            shift = ord(key[ki % len(key)]) - ord('a')
            base  = ord('A') if ch.isupper() else ord('a')
            result.append(chr((ord(ch) - base - shift) % 26 + base))
            ki += 1
        else:
            result.append(ch)
    return "".join(result)

def password_to_key(password: str) -> bytes:
    digest = hashlib.sha256(password.encode()).digest()
    return base64.urlsafe_b64encode(digest)

def custom_encrypt(plain: str, password: str) -> str:
    return fernet_encrypt(plain, password_to_key(password))

def custom_decrypt(token: str, password: str) -> str:
    return fernet_decrypt(token, password_to_key(password))


# ╔══════════════════════════════════════════════════════════════╗
# ║               📋  MAIN MENU & /START                         ║
# ╚══════════════════════════════════════════════════════════════╝

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [
        [
            InlineKeyboardButton("🔒 Encrypt Message", callback_data="menu_encrypt"),
            InlineKeyboardButton("🔓 Decrypt Message", callback_data="menu_decrypt"),
        ],
        [
            InlineKeyboardButton("📖 All Methods", callback_data="menu_methods"),
            InlineKeyboardButton("ℹ️ Help",         callback_data="menu_help"),
        ],
    ]
    await update.message.reply_text(
        "🔐 *Welcome to CryptoBot!*\n\n"
        "Main aapke messages ko *encrypt* aur *decrypt* kar sakta hun!\n\n"
        "🛡️ *Available Methods:*\n"
        "• 🔵 Fernet   — AES-128 military-grade\n"
        "• 🟡 Caesar   — Classic shift cipher\n"
        "• 🟢 Base64   — Quick encode/decode\n"
        "• 🟣 Vigenere — Keyword cipher\n"
        "• 🔴 Custom   — Password-based AES\n\n"
        "👇 Neeche se choose karo:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return CHOOSE_METHOD


# ╔══════════════════════════════════════════════════════════════╗
# ║               🔘  MENU CALLBACK HANDLER                      ║
# ╚══════════════════════════════════════════════════════════════╝

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data  = query.data

    back_btn = [[InlineKeyboardButton("🔙 Back", callback_data="menu_back")]]

    if data == "menu_encrypt":
        kb = [
            [InlineKeyboardButton("🔵 Fernet (AES)",  callback_data="enc_fernet")],
            [InlineKeyboardButton("🟡 Caesar Cipher", callback_data="enc_caesar")],
            [InlineKeyboardButton("🟢 Base64",        callback_data="enc_base64")],
            [InlineKeyboardButton("🟣 Vigenere",      callback_data="enc_vigenere")],
            [InlineKeyboardButton("🔴 Custom (Pass)", callback_data="enc_custom")],
            [InlineKeyboardButton("🔙 Back",          callback_data="menu_back")],
        ]
        await query.edit_message_text(
            "🔒 *Encryption Method Choose Karo:*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb),
        )
        return CHOOSE_METHOD

    if data == "menu_decrypt":
        kb = [
            [InlineKeyboardButton("🔵 Fernet (AES)",  callback_data="dec_fernet")],
            [InlineKeyboardButton("🟡 Caesar Cipher", callback_data="dec_caesar")],
            [InlineKeyboardButton("🟢 Base64",        callback_data="dec_base64")],
            [InlineKeyboardButton("🟣 Vigenere",      callback_data="dec_vigenere")],
            [InlineKeyboardButton("🔴 Custom (Pass)", callback_data="dec_custom")],
            [InlineKeyboardButton("🔙 Back",          callback_data="menu_back")],
        ]
        await query.edit_message_text(
            "🔓 *Decryption Method Choose Karo:*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb),
        )
        return CHOOSE_METHOD

    if data == "menu_methods":
        await query.edit_message_text(
            "📖 *Encryption Methods — Full Info*\n\n"
            "🔵 *Fernet (AES-128)*\n   Military-grade symmetric encryption.\n\n"
            "🟡 *Caesar Cipher*\n   Har letter ko N positions shift karo.\n\n"
            "🟢 *Base64*\n   Binary to text encoding. No key needed.\n\n"
            "🟣 *Vigenere Cipher*\n   Keyword-based polyalphabetic cipher.\n\n"
            "🔴 *Custom Password (AES)*\n   SHA-256 + Fernet. Strongest option!\n",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(back_btn),
        )
        return CHOOSE_METHOD

    if data == "menu_help":
        await query.edit_message_text(
            "ℹ️ *Help — CryptoBot*\n\n"
            "1️⃣ /start — Main menu\n"
            "2️⃣ /encrypt `<msg>` — Quick Fernet encrypt\n"
            "3️⃣ /decrypt `<token>` — Quick Fernet decrypt\n"
            "4️⃣ /caesar `<shift> <msg>` — Caesar encrypt\n"
            "5️⃣ /b64enc `<msg>` — Base64 encode\n"
            "6️⃣ /b64dec `<msg>` — Base64 decode\n"
            "7️⃣ /vigenere `<key> <msg>` — Vigenere encrypt\n"
            "8️⃣ /cancel — Koi bhi step cancel karo\n",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(back_btn),
        )
        return CHOOSE_METHOD

    if data == "menu_back":
        keyboard = [
            [
                InlineKeyboardButton("🔒 Encrypt Message", callback_data="menu_encrypt"),
                InlineKeyboardButton("🔓 Decrypt Message", callback_data="menu_decrypt"),
            ],
            [
                InlineKeyboardButton("📖 All Methods", callback_data="menu_methods"),
                InlineKeyboardButton("ℹ️ Help",         callback_data="menu_help"),
            ],
        ]
        await query.edit_message_text(
            "🔐 *CryptoBot — Main Menu*\n\n👇 Option choose karo:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return CHOOSE_METHOD

    # ── Encrypt Actions ───────────────────────────────────────
    if data == "enc_fernet":
        context.user_data["action"] = "enc_fernet"
        await query.edit_message_text("🔵 *Fernet Encryption*\n\n✏️ Message bhejo:", parse_mode="Markdown")
        return WAIT_ENC_MSG

    if data == "enc_base64":
        context.user_data["action"] = "enc_base64"
        await query.edit_message_text("🟢 *Base64 Encode*\n\n✏️ Message bhejo:", parse_mode="Markdown")
        return WAIT_ENC_MSG

    if data == "enc_caesar":
        context.user_data["action"] = "enc_caesar"
        await query.edit_message_text("🟡 *Caesar Cipher*\n\n🔢 Shift number bhejo (1–25):", parse_mode="Markdown")
        return WAIT_CAESAR_SHIFT

    if data == "enc_vigenere":
        context.user_data["action"] = "enc_vigenere"
        await query.edit_message_text("🟣 *Vigenere Encrypt*\n\n🔑 Keyword bhejo (only letters):", parse_mode="Markdown")
        return WAIT_VIG_KEY

    if data == "enc_custom":
        context.user_data["action"] = "enc_custom"
        await query.edit_message_text("🔴 *Custom Encrypt*\n\n🔑 Password bhejo:", parse_mode="Markdown")
        return WAIT_CUSTOM_KEY

    # ── Decrypt Actions ───────────────────────────────────────
    if data == "dec_fernet":
        context.user_data["action"] = "dec_fernet"
        await query.edit_message_text("🔵 *Fernet Decrypt*\n\n✏️ Encrypted token paste karo:", parse_mode="Markdown")
        return WAIT_DEC_MSG

    if data == "dec_base64":
        context.user_data["action"] = "dec_base64"
        await query.edit_message_text("🟢 *Base64 Decode*\n\n✏️ Encoded string paste karo:", parse_mode="Markdown")
        return WAIT_DEC_MSG

    if data == "dec_caesar":
        context.user_data["action"] = "dec_caesar"
        await query.edit_message_text("🟡 *Caesar Decrypt*\n\n🔢 Shift number bhejo:", parse_mode="Markdown")
        return WAIT_CAESAR_SHIFT

    if data == "dec_vigenere":
        context.user_data["action"] = "dec_vigenere"
        await query.edit_message_text("🟣 *Vigenere Decrypt*\n\n🔑 Keyword bhejo:", parse_mode="Markdown")
        return WAIT_VIG_KEY

    if data == "dec_custom":
        context.user_data["action"] = "dec_custom"
        await query.edit_message_text("🔴 *Custom Decrypt*\n\n🔑 Password bhejo:", parse_mode="Markdown")
        return WAIT_CUSTOM_KEY

    return CHOOSE_METHOD


# ╔══════════════════════════════════════════════════════════════╗
# ║            💬  ALL MESSAGE HANDLERS                          ║
# ╚══════════════════════════════════════════════════════════════╝

async def handle_enc_dec_msg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    action  = context.user_data.get("action", "")
    text    = update.message.text.strip()
    back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data="menu_back")]])

    try:
        if action == "enc_fernet":
            result = fernet_encrypt(text)
            await update.message.reply_text(f"🔵 *Fernet Encrypted!*\n\n`{result}`\n\n⚠️ Token safe rakhna!", parse_mode="Markdown", reply_markup=back_kb)

        elif action == "dec_fernet":
            result = fernet_decrypt(text)
            await update.message.reply_text(f"🔵 *Fernet Decrypted!*\n\n✅ `{result}`", parse_mode="Markdown", reply_markup=back_kb)

        elif action == "enc_base64":
            result = base64_encode(text)
            await update.message.reply_text(f"🟢 *Base64 Encoded!*\n\n`{result}`", parse_mode="Markdown", reply_markup=back_kb)

        elif action == "dec_base64":
            result = base64_decode(text)
            await update.message.reply_text(f"🟢 *Base64 Decoded!*\n\n✅ `{result}`", parse_mode="Markdown", reply_markup=back_kb)

    except InvalidToken:
        await update.message.reply_text("❌ *Invalid Token!* Sahi encrypted text paste karo.", parse_mode="Markdown", reply_markup=back_kb)
    except Exception as e:
        await update.message.reply_text(f"❌ *Error:* `{e}`", parse_mode="Markdown", reply_markup=back_kb)

    context.user_data.clear()
    return ConversationHandler.END


async def caesar_get_shift(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        shift = int(update.message.text.strip())
        if not (1 <= shift <= 25):
            raise ValueError
        context.user_data["shift"] = shift
        word = "encrypt" if "enc" in context.user_data.get("action","") else "decrypt"
        await update.message.reply_text(f"✅ Shift = *{shift}*\n\n✏️ Ab message bhejo jo {word} karna hai:", parse_mode="Markdown")
        return WAIT_CAESAR_MSG
    except ValueError:
        await update.message.reply_text("❌ Sirf 1–25 ke beech number bhejo!")
        return WAIT_CAESAR_SHIFT


async def caesar_get_msg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text    = update.message.text.strip()
    shift   = context.user_data.get("shift", 3)
    action  = context.user_data.get("action", "enc_caesar")
    back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data="menu_back")]])

    if "enc" in action:
        result = caesar_encrypt(text, shift)
        label  = "🟡 *Caesar Encrypted!*"
    else:
        result = caesar_decrypt(text, shift)
        label  = "🟡 *Caesar Decrypted!*"

    await update.message.reply_text(f"{label}\n\n🔢 Shift: *{shift}*\n📝 Result: `{result}`", parse_mode="Markdown", reply_markup=back_kb)
    context.user_data.clear()
    return ConversationHandler.END


async def vigenere_get_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    key = update.message.text.strip()
    if not key.isalpha():
        await update.message.reply_text("❌ Keyword sirf letters mein hona chahiye! Dobara bhejo:")
        return WAIT_VIG_KEY
    context.user_data["vig_key"] = key
    word = "encrypt" if "enc" in context.user_data.get("action","") else "decrypt"
    await update.message.reply_text(f"✅ Key = *{key}*\n\n✏️ Ab message bhejo jo {word} karna hai:", parse_mode="Markdown")
    return WAIT_VIG_MSG


async def vigenere_get_msg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text    = update.message.text.strip()
    key     = context.user_data.get("vig_key", "KEY")
    action  = context.user_data.get("action", "enc_vigenere")
    back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data="menu_back")]])

    if "enc" in action:
        result = vigenere_encrypt(text, key)
        label  = "🟣 *Vigenere Encrypted!*"
    else:
        result = vigenere_decrypt(text, key)
        label  = "🟣 *Vigenere Decrypted!*"

    await update.message.reply_text(f"{label}\n\n🔑 Key: *{key}*\n📝 Result: `{result}`", parse_mode="Markdown", reply_markup=back_kb)
    context.user_data.clear()
    return ConversationHandler.END


async def custom_get_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["password"] = update.message.text.strip()
    action = context.user_data.get("action", "enc_custom")
    if action == "dec_custom":
        await update.message.reply_text("✅ Password mila!\n\n✏️ Ab encrypted token paste karo:", parse_mode="Markdown")
        return WAIT_DEC_CUSTOM
    await update.message.reply_text("✅ Password set!\n\n✏️ Ab message bhejo jo encrypt karna hai:", parse_mode="Markdown")
    return WAIT_CUSTOM_MSG


async def custom_get_msg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text     = update.message.text.strip()
    password = context.user_data.get("password", "")
    back_kb  = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data="menu_back")]])
    token = custom_encrypt(text, password)
    await update.message.reply_text(f"🔴 *Custom Encrypted!*\n\n`{token}`\n\n⚠️ Password aur token dono safe rakhna!", parse_mode="Markdown", reply_markup=back_kb)
    context.user_data.clear()
    return ConversationHandler.END


async def custom_dec_msg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    token    = update.message.text.strip()
    password = context.user_data.get("password", "")
    back_kb  = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data="menu_back")]])
    try:
        plain = custom_decrypt(token, password)
        await update.message.reply_text(f"🔴 *Custom Decrypted!*\n\n✅ `{plain}`", parse_mode="Markdown", reply_markup=back_kb)
    except InvalidToken:
        await update.message.reply_text("❌ *Galat password ya invalid token!*\n/start se dobara try karo.", parse_mode="Markdown", reply_markup=back_kb)
    context.user_data.clear()
    return ConversationHandler.END


# ╔══════════════════════════════════════════════════════════════╗
# ║             ⚡  QUICK COMMAND HANDLERS                        ║
# ╚══════════════════════════════════════════════════════════════╝

async def cmd_encrypt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Usage: `/encrypt Your message`", parse_mode="Markdown")
        return
    plain = " ".join(context.args)
    await update.message.reply_text(f"🔵 *Quick Fernet Encrypt*\n\n🔒 `{fernet_encrypt(plain)}`", parse_mode="Markdown")

async def cmd_decrypt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Usage: `/decrypt <token>`", parse_mode="Markdown")
        return
    try:
        await update.message.reply_text(f"🔵 *Quick Decrypt*\n\n✅ `{fernet_decrypt(context.args[0])}`", parse_mode="Markdown")
    except InvalidToken:
        await update.message.reply_text("❌ *Invalid Token!*", parse_mode="Markdown")

async def cmd_caesar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("❌ Usage: `/caesar 3 Hello`", parse_mode="Markdown")
        return
    try:
        shift = int(context.args[0])
        text  = " ".join(context.args[1:])
        await update.message.reply_text(f"🟡 *Caesar* (shift={shift})\n\n`{caesar_encrypt(text, shift)}`", parse_mode="Markdown")
    except ValueError:
        await update.message.reply_text("❌ Shift number hona chahiye!")

async def cmd_b64enc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Usage: `/b64enc Hello`", parse_mode="Markdown")
        return
    await update.message.reply_text(f"🟢 *Base64*\n\n`{base64_encode(' '.join(context.args))}`", parse_mode="Markdown")

async def cmd_b64dec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Usage: `/b64dec SGVsbG8=`", parse_mode="Markdown")
        return
    try:
        await update.message.reply_text(f"🟢 *Decoded*\n\n`{base64_decode(context.args[0])}`", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("❌ Invalid Base64 string!")

async def cmd_vigenere(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("❌ Usage: `/vigenere SECRET Hello`", parse_mode="Markdown")
        return
    key  = context.args[0]
    text = " ".join(context.args[1:])
    await update.message.reply_text(f"🟣 *Vigenere*\n\n🔑 Key: `{key}`\n🔒 `{vigenere_encrypt(text, key)}`", parse_mode="Markdown")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("❌ *Cancelled!*\n/start se dobara shuru karo.", parse_mode="Markdown")
    return ConversationHandler.END


# ╔══════════════════════════════════════════════════════════════╗
# ║                 🚀  MAIN — FULLY FIXED                        ║
# ╚══════════════════════════════════════════════════════════════╝

async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSE_METHOD:     [CallbackQueryHandler(menu_callback)],
            WAIT_ENC_MSG:      [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_enc_dec_msg)],
            WAIT_DEC_MSG:      [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_enc_dec_msg)],
            WAIT_CAESAR_SHIFT: [MessageHandler(filters.TEXT & ~filters.COMMAND, caesar_get_shift)],
            WAIT_CAESAR_MSG:   [MessageHandler(filters.TEXT & ~filters.COMMAND, caesar_get_msg)],
            WAIT_VIG_KEY:      [MessageHandler(filters.TEXT & ~filters.COMMAND, vigenere_get_key)],
            WAIT_VIG_MSG:      [MessageHandler(filters.TEXT & ~filters.COMMAND, vigenere_get_msg)],
            WAIT_CUSTOM_KEY:   [MessageHandler(filters.TEXT & ~filters.COMMAND, custom_get_key)],
            WAIT_CUSTOM_MSG:   [MessageHandler(filters.TEXT & ~filters.COMMAND, custom_get_msg)],
            WAIT_DEC_CUSTOM:   [MessageHandler(filters.TEXT & ~filters.COMMAND, custom_dec_msg)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
        per_message=False,
        per_chat=True,
        per_user=True,
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("encrypt",  cmd_encrypt))
    app.add_handler(CommandHandler("decrypt",  cmd_decrypt))
    app.add_handler(CommandHandler("caesar",   cmd_caesar))
    app.add_handler(CommandHandler("b64enc",   cmd_b64enc))
    app.add_handler(CommandHandler("b64dec",   cmd_b64dec))
    app.add_handler(CommandHandler("vigenere", cmd_vigenere))
    app.add_handler(CommandHandler("cancel",   cancel))

    print("=" * 55)
    print("  🔐 CryptoBot — ONLINE!")
    print("  Methods: Fernet | Caesar | Base64 | Vigenere | Custom")
    print("=" * 55)

    # ✅ FIXED: Proper async start
    async with app:
        await app.start()
        await app.updater.start_polling()
        print("  ✅ Polling shuru! Ctrl+C se band karo.")
        print("=" * 55)
        await asyncio.Event().wait()  # ✅ Bot ko alive rakho


# ╔══════════════════════════════════════════════════════════════╗
# ║                     ▶️  ENTRY POINT                           ║
# ╚══════════════════════════════════════════════════════════════╝

if __name__ == "__main__":
    try:
        # ✅ Windows ke liye asyncio fix
        if os.name == 'nt':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        asyncio.run(main())

    except KeyboardInterrupt:
        print("\n" + "=" * 55)
        print("  🛑 CryptoBot band ho gaya! (Ctrl+C)")
        print("=" * 55)
