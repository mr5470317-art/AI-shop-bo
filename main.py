import os
import asyncio
import logging
import google.generativeai as genai
from aiogram import Bot, Dispatcher, types as aiogram_types, F
from aiogram.filters import Command

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MY_TELEGRAM_ID = int(os.getenv("MY_TELEGRAM_ID", 0))

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    raise ValueError("Не найдены TELEGRAM_TOKEN или GEMINI_API_KEY в переменных окружения!")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# Настройка классического SDK
genai.configure(api_key=GEMINI_API_KEY.strip())

# Используем модель с явным префиксом
generation_config = {
    "temperature": 0.4,
}
model = genai.GenerativeModel(
    model_name="models/gemini-1.5-flash",
    generation_config=generation_config
)

def get_products_data():
    try:
        with open("products.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Список товарів наразі порожній."

@dp.message(Command("start"))
async def cmd_start(message: aiogram_types.Message):
    if MY_TELEGRAM_ID and message.from_user.id == MY_TELEGRAM_ID:
        await message.answer("Привіт, адміне! Це службовий чат.")
    else:
        await message.answer("Привіт! Я твій інтелектуальний помічник-консультант StyleHub.")

@dp.message(F.text)
async def handle_message(message: aiogram_types.Message):
    user_id = message.from_user.id
    
    if MY_TELEGRAM_ID and user_id == MY_TELEGRAM_ID:
        await message.answer("Це службовий чат адміністратора. Клієнтів тут немає.")
        return

    products_info = get_products_data()
    
    system_instruction = f"""Ти — найкращий консультант StyleHub. Твій досвід — 10 років у продажах одягу. 
Асортимент: {products_info}

Стиль спілкування:
1. Тільки чиста грамотна ввічлива українська мова. Жодних дивних зворотів чи сленгу.
2. Якщо клієнт запитує про товар — давай чітку відповідь.
3. ОФОРМЛЕННЯ ЗАМОВЛЕННЯ: Якщо клієнт погоджується купувати, попроси номер телефону та адресу доставки. Як тільки він надасть дані, обов'язково відповідай покупцю фразою "ЗАМОВЛЕННЯ ПРИЙНЯТО" і додай: "Дякуємо за покупку, нам було приємно з вами працювати!"
"""

    try:
        # Передаем системную инструкцию и текст вместе
        prompt = f"{system_instruction}\n\nПовідомлення клієнта: {message.text}"
        response = model.generate_content(prompt)
        
        reply_text = response.text
        await message.answer(reply_text)

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
