import os
import logging
from aiogram import Bot, Dispatcher, F, types as aiogram_types
from aiogram.filters import Command
import google.generativeai as genai

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Получаем ключи и ID администратора
BOT_TOKEN = os.getenv("BOT_TOKEN", "ТВОЙ_ТОКЕН_ТЕЛЕГРАМ_БОТА")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "ТВОЙ_КЛЮЧ_GEMINI")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# Инициализация бота и клиента Gemini (классический стабильный SDK)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
genai.configure(api_key=GEMINI_API_KEY)

# Используем модель gemini-1.5-flash (быстрая, бесплатная и понимает системный промпт)
generation_config = {
    "temperature": 0.7,
    "max_output_tokens": 500,
}

# Словарь для хранения истории диалогов пользователей
user_sessions = {}

# Функция для чтения каталога из файла
def load_catalog():
    try:
        if os.path.exists("products.txt"):
            with open("products.txt", "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
                return ", ".join(lines)
        return "Асортимент тимчасово відсутній."
    except Exception as e:
        logging.error(f"Ошибка чтения файла каталога: {e}")
        return "Асортимент тимчасово відсутній."

@dp.message(Command("start"))
async def cmd_start(message: aiogram_types.Message):
    user_id = message.from_user.id
    user_sessions[user_id] = []
    await message.answer("Привіт! Я твій консультант у StyleHub. Як я можу тобі допомогти сьогодні?")

@dp.message(Command("reset"))
async def cmd_reset(message: aiogram_types.Message):
    user_id = message.from_user.id
    user_sessions[user_id] = []
    await message.answer("Історію очищено! Давайте почнемо спочатку.")

@dp.message(F.text)
async def handle_message(message: aiogram_types.Message):
    user_id = message.from_user.id
    user_text = message.text

    if user_id not in user_sessions:
        user_sessions[user_id] = []

    user_sessions[user_id].append({"role": "user", "content": user_text})

    try:
        catalog_text = load_catalog()
        
        # Системный промпт с правилами
        system_instruction = (
            f"Ти — професійний консультант StyleHub. ТЕКУЧИЙ АСОРИМЕНТ МАГАЗИНУ: [{catalog_text}].\n"
            "ПРАВИЛА:\n"
            "
