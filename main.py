import os
import asyncio
import logging
import google.generativeai as genai
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") # Убедись, что переменная называется так
MY_TELEGRAM_ID = int(os.getenv("MY_TELEGRAM_ID", 0))

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    raise ValueError("Не найдены TELEGRAM_TOKEN или GEMINI_API_KEY!")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# Настройка Gemini
genai.configure(api_key=GEMINI_API_KEY)
# Используем модель flash для скорости
model = genai.GenerativeModel('models/gemini-1.5-flash')

# Память диалогов (для Gemini лучше использовать chat-сессии)
user_chats = {}

def get_products_data():
    try:
        with open("products.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Список товарів наразі порожній."

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Создаем новую чат-сессию для каждого пользователя
    products_info = get_products_data()
    system_prompt = f"""Ти — найкращий консультант StyleHub. Твій досвід — 10 років у продажах одягу. 
    Твоя мова — грамотна, ввічлива українська мова. 
    Ось асортимент: {products_info}
    
    Стиль: впевнений, професійний, без сленгу та суржику.
    Якщо клієнт купує — попроси телефон та адресу. Після отримання напиши "ЗАМОВЛЕННЯ ПРИЙНЯТО. Дякуємо за покупку, нам було приємно з вами працювати!"""
    
    user_chats[message.from_user.id] = model.start_chat(history=[])
    # Передаем системный контекст в историю чата
    user_chats[message.from_user.id].send_message(f"Інструкція для тебе: {system_prompt}")

    if MY_TELEGRAM_ID and message.from_user.id == MY_TELEGRAM_ID:
        await message.answer("Привіт, адміне!")
    else:
        await message.answer("Привіт! Я твій консультант StyleHub. Чим можу допомогти?")

@dp.message(F.text)
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    
    if MY_TELEGRAM_ID and user_id == MY_TELEGRAM_ID:
        return

    if user_id not in user_chats:
        await cmd_start(message)
        return

    try:
        # Отправляем сообщение в чат
        chat = user_chats[user_id]
        response = chat.send_message(message.text)
        reply_text = response.text
        
        await message.answer(reply_text)

        if "ЗАМОВЛЕННЯ ПРИЙНЯТО" in reply_text.upper():
            if MY_TELEGRAM_ID != 0:
                await bot.send_message(
                    chat_id=MY_TELEGRAM_ID, 
                    text=f"🔥 НОВЕ ЗАМОВЛЕННЯ!\nКлієнт: @{message.from_user.username or 'без ніка'}\n{reply_text}"
                )
            
    except Exception as e:
        logging.error(f"Ошибка Gemini API: {e}")
        await message.answer("Вибачте, виникла технічна помилка.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
