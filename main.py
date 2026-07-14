import os
import asyncio
import logging
from google import genai
from google.genai import types as genai_types
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MY_TELEGRAM_ID = int(os.getenv("MY_TELEGRAM_ID", 0))

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    raise ValueError("Не найдены TELEGRAM_TOKEN или GEMINI_API_KEY в переменных окружения!")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# Инициализация нового клиента google-genai
client = genai.Client(api_key=GEMINI_API_KEY)

# Хранилище активных чат-сессий для каждого пользователя
user_chats = {}

def get_products_data():
    try:
        with open("products.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Список товарів наразі порожній."

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    products_info = get_products_data()
    
    system_instruction = f"""Ти — найкращий консультант StyleHub. Твій досвід — 10 років у продажах одягу. 
Асортимент: {products_info}

Стиль спілкування:
1. Тільки чиста грамотна ввічлива українська мова. Жодних дивних зворотів чи сленгу.
2. Якщо клієнт запитує про товар — давай чітку відповідь.
3. ОФОРМЛЕННЯ ЗАМОВЛЕННЯ: Якщо клієнт погоджується купувати, попроси номер телефону та адресу доставки. Як тільки він надасть дані, обов'язково відповідай покупцю фразою "ЗАМОВЛЕННЯ ПРИЙНЯТО" і додай: "Дякуємо за покупку, нам було приємно з вами працювати!"
"""
    # Создаем стабильную чат-сессию через клиент с актуальной универсальной моделью
    user_chats[message.from_user.id] = client.chats.create(
        model='gemini-2.5-flash',
        config=genai_types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.4,
        )
    )

    if MY_TELEGRAM_ID and message.from_user.id == MY_TELEGRAM_ID:
        await message.answer("Привіт, адміне! Це службовий чат.")
    else:
        await message.answer("Привіт! Я твій інтелектуальний помічник-консультант StyleHub.")

@dp.message(F.text)
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    
    if MY_TELEGRAM_ID and user_id == MY_TELEGRAM_ID:
        await message.answer("Це службовий чат адміністратора. Клієнтів тут немає.")
        return

    if user_id not in user_chats:
        products_info = get_products_data()
        system_instruction = f"Ти — консультант StyleHub. Асортимент: {products_info}. Пиши грамотною українською."
        user_chats[user_id] = client.chats.create(
            model='gemini-2.5-flash',
            config=genai_types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.4
            )
        )

    try:
        # Отправляем сообщение в текущую сессию
        chat = user_chats[user_id]
        response = chat.send_message(message.text)
        
        reply_text = response.text
        await message.answer(reply_text)

        # Уведомление продавцу
        if "ЗАМОВЛЕННЯ ПРИЙНЯТО" in reply_text.upper():
            if MY_TELEGRAM_ID != 0:
                await bot.send_message(
                    chat_id=MY_TELEGRAM_ID, 
                    text=f"🔥 НОВЕ ЗАМОВЛЕННЯ!\nКлієнт: @{message.from_user.username or 'без ніка'}\nID: {user_id}\n\nВідповідь бота:\n{reply_text}"
                )
            
    except Exception as e:
        logging.error(f"Ошибка при запросе к Gemini API: {e}")
        await message.answer(f"Помилка: {str(e)}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
