import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from openai import OpenAI

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Твой цифровой ID из переменных окружения Railway (или можно подставить число для теста)
MY_TELEGRAM_ID = int(os.getenv("MY_TELEGRAM_ID", 0))

if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise ValueError("Не найдены TELEGRAM_TOKEN или GROQ_API_KEY в переменных окружения!")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

# Память диалогов для каждого пользователя
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
        await message.answer("Привіт, админе! Це службовий чат. Сюди надходитимуть сповіщення про замовлення.")
    else:
        await message.answer("Привіт! Я твій інтелектуальний помічник-консультант. Готовий допомагати з вибором товарів.")

@dp.message(F.text)
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    
    # Защита, чтобы админ случайно не вел диалог как клиент сам с собой
    if MY_TELEGRAM_ID and user_id == MY_TELEGRAM_ID:
        await message.answer("Це службовий чат адміністратора. Клієнтів тут немає.")
        return

    if user_id not in user_histories:
        user_histories[user_id] = []

    user_histories[user_id].append({"role": "user", "content": message.text})
    
    # Ограничиваем историю 10 сообщениями
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
6. ОФОРМЛЕННЯ ЗАМОВЛЕННЯ: Якщо клієнт погоджується купувати, чітко попроси його написати ДВІ речі: номер телефону та адресу доставки (місто, відділення пошти). Як тільки він надасть ці дані, ти обов'язково відповідаєш покупцю фразою "ЗАМОВЛЕННЯ ПРИЙНЯТО" і дякуєш за покупку."""

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

        # Отправка уведомления продавцу (тебе) в личку
        if "ЗАМОВЛЕННЯ ПРИЙНЯТО" in reply_text.upper():
            order_details = "\n".join([f"{msg['role']}: {msg['content']}" for msg in user_histories[user_id][-5:]])
            
            if MY_TELEGRAM_ID != 0:
                await bot.send_message(
                    chat_id=MY_TELEGRAM_ID, 
                    text=f"🔥 НОВЕ ЗАМОВЛЕННЯ!\nКлієнт: @{message.from_user.username or 'без ніка'}\nID: {user_id}\n\nДані з чату:\n{order_details}"
                )
            
    except Exception as e:
        logging.error(f"Ошибка при запросе к Groq API: {e}")
        await message.answer(f"Помилка: {str(e)}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
