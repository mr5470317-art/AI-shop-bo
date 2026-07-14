import os
import asyncio
import logging
from google import genai
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") # Убедись, что в Railway ключ так и называется
MY_TELEGRAM_ID = int(os.getenv("MY_TELEGRAM_ID", 0))

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    raise ValueError("Не найдены TELEGRAM_TOKEN или GEMINI_API_KEY в переменных окружения!")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# Инициализация нового клиента Gemini
client = genai.Client(api_key=GEMINI_API_KEY)

# Память диалогов (храним историю списком сообщений)
user_histories = {}

def get_products_data():
    try:
        with open("products.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Список товарів наразі порожній."

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_histories[message.from_user.id] = []
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

    if user_id not in user_histories:
        user_histories[user_id] = []

    user_histories[user_id].append({"role": "user", "parts": [message.text]})
    
    # Ограничиваем историю
    if len(user_histories[user_id]) > 10:
        user_histories[user_id] = user_histories[user_id][-10:]

    products_info = get_products_data()
    
    system_instruction = f"""Ти — найкращий консультант StyleHub. Твій досвід — 10 років у продажах одягу. 
Асортимент: {products_info}

Стиль спілкування:
1. Тільки чиста грамотна ввічлива українська мова.
2. Жодних дивних зворотів чи сленгу.
3. Якщо клієнт запитує про товар — давай чітку відповідь.
4. ОФОРМЛЕННЯ ЗАМОВЛЕННЯ: Якщо клієнт погоджується купувати, попроси номер телефону та адресу доставки. Як тільки він надасть дані, обов'язково відповідай покупцю фразою "ЗАМОВЛЕННЯ ПРИЙНЯТО" і додай: "Дякуємо за покупку, нам було приємно з вами працювати!"
"""

    try:
        # В новой библиотеке системный промпт и история передаются через конфигурацию содержимого
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=user_histories[user_id],
            config={
                'system_instruction': system_instruction,
                'temperature': 0.4,
            }
        )
        
        reply_text = response.text
        user_histories[user_id].append({"role": "model", "parts": [reply_text]})
        
        await message.answer(reply_text)

        # Уведомление продавцу
        if "ЗАМОВЛЕННЯ ПРИЙНЯТО" in reply_text.upper():
            order_details = "\n".join([f"{msg['role']}: {msg['parts'][0]}" for msg in user_histories[user_id][-5:]])
            
            if MY_TELEGRAM_ID != 0:
                await bot.send_message(
                    chat_id=MY_TELEGRAM_ID, 
                    text=f"🔥 НОВЕ ЗАМОВЛЕННЯ!\nКлієнт: @{message.from_user.username or 'без ніка'}\nID: {user_id}\n\nДані з чату:\n{order_details}"
                )
            
    except Exception as e:
        logging.error(f"Ошибка при запросе к Gemini API: {e}")
        await message.answer(f"Помилка: {str(e)}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
