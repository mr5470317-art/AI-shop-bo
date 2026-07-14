import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from openai import OpenAI

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Твой юзернейм из переменных окружения (например: @my_username или без знака @)
MY_TELEGRAM_USERNAME = os.getenv("MY_TELEGRAM_USERNAME", "").replace("@", "").lower()

if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise ValueError("Не найдены TELEGRAM_TOKEN или GROQ_API_KEY в переменных окружения!")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

# Переменная для динамического сохранения твоего ID после /start
my_real_chat_id = None
user_histories = {}

def get_products_data():
    try:
        with open("products.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Список товарів наразі порожній."

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    global my_real_chat_id
    user_id = message.from_user.id
    user_histories[user_id] = []
    
    # Автоматически определяем, что это ты по твоему юзернейму
    if MY_TELEGRAM_USERNAME and message.from_user.username and message.from_user.username.lower() == MY_TELEGRAM_USERNAME:
        my_real_chat_id = user_id
        await message.json if hasattr(message, 'json') else None
        await message.answer("Привіт, босоту! Твій юзернейм розпізнано, тепер я надсилатиму сюди замовлення.")
    else:
        await message.answer("Привіт! Я твій інтелектуальний помічник-консультант. Готовий допомагати з вибором товарів.")

@dp.message(F.text)
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    
    # Если это пишет владелец (ты) и случайно триггернул команду
    if my_real_chat_id and user_id == my_real_chat_id:
        await message.answer("Це службовий чат адміністратора. Клієнтів тут немає.")
        return

    if user_id not in user_histories:
        user_histories[user_id] = []

    user_histories[user_id].append({"role": "user", "content": message.text})
    
    if len(user_histories[user_id]) > 10:
        user_histories[user_id] = user_histories[user_id][-10:]

    products_info = get_products_data()
    
    system_prompt = f"""Ти - професійний менеджер з продажу брендового одягу.
Ось актуальна інформація про товари:
{products_info}

Твій стиль спілкування:
1. Лаконічний, впевнений, діловий український стиль.
2. Жодних дивних зворотів, кальки з інших мов чи сленгу. Тільки чиста ділова українська мова.
3. Якщо клієнт запитує про розмір чи товар - давай чітку відповідь.
4. Не вигадуй зайвих питань, якщо клієнт уже назвав товар.
5. Завжди будь ввічливим, але тримай дистанцію професіонала.
6. Якщо клієнт остаточно погоджується на покупку/замовлення, обов'язково у своїй відповіді напиши фразу "ЗАМОВЛЕННЯ ПРИЙНЯТО" та попроси залишити контактні дані (номер телефону)."""

    try:
        messages = [{"role": "system", "content": system_prompt}] + user_histories[user_id]
        
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            max_tokens=1000,
            messages=messages
        )
        
        reply_text = response.choices[0].message.content
        user_histories[user_id].append({"role": "assistant", "content": reply_text})
        
        await message.answer(reply_text)

        # Отправка заказа администратору
        if "ЗАМОВЛЕННЯ ПРИЙНЯТО" in reply_text.upper():
            order_details = "\n".join([f"{msg['role']}: {msg['content']}" for msg in user_histories[user_id][-4:]])
            
            if my_real_chat_id:
                await bot.send_message(
                    chat_id=my_real_chat_id, 
                    text=f"🔥 НОВЕ ЗАМОВЛЕННЯ!\nКлієнт: @{message.from_user.username or 'без ніка'}\nID: {user_id}\n\nОстанні повідомлення:\n{order_details}"
                )
            
    except Exception as e:
        logging.error(f"Ошибка при запросе к Groq API: {e}")
        await message.answer(f"Помилка: {str(e)}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
