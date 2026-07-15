import os
import asyncio
import logging
from groq import AsyncGroq
from aiogram import Bot, Dispatcher, types as aiogram_types, F
from aiogram.filters import Command

logging.basicConfig(level=logging.INFO)

GROQ_API_KEY = os.getenv("GROQ_API_KEY") 
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MY_TELEGRAM_ID = int(os.getenv("MY_TELEGRAM_ID", 0))

if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise ValueError("Не найдены переменные окружения TELEGRAM_TOKEN или GROQ_API_KEY!")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

client = AsyncGroq(api_key=GROQ_API_KEY.strip())

user_sessions = {}

def get_products_data():
    files = ["products.txt", "catalog.txt"]
    all_data = ""
    for file in files:
        try:
            with open(file, "r", encoding="utf-8") as f:
                all_data += f"\n--- {file} ---\n" + f.read()
        except FileNotFoundError:
            continue
    return all_data if all_data else "Асортимент наразі порожній."

@dp.message(Command("start"))
async def cmd_start(message: aiogram_types.Message):
    user_id = message.from_user.id
    user_sessions[user_id] = []
    
    if MY_TELEGRAM_ID and user_id == MY_TELEGRAM_ID:
        await message.answer("Привіт, адміне! Бот готовий до роботи.")
    else:
        await message.answer("Привіт! Я твій консультант StyleHub. Чим можу допомогти?")

@dp.message(F.text)
async def handle_message(message: aiogram_types.Message):
    user_id = message.from_user.id
    
    if MY_TELEGRAM_ID and user_id == MY_TELEGRAM_ID:
        return

    if user_id not in user_sessions:
        user_sessions[user_id] = []

    user_sessions[user_id].append({"role": "user", "content": message.text})
    
    if len(user_sessions[user_id]) > 10:
        user_sessions[user_id] = user_sessions[user_id][-10:]

    catalog = get_products_data()
    
    system_instruction = (
        f"Ти — професійний консультант магазину StyleHub. Твій асортимент: {catalog}. "
        "Твоя задача — допомагати з вибором одягу, оформлювати замовлення або з'єднувати з менеджером.\n"
        "ПРАВИЛА ДЛЯ МЕНЕДЖЕРА:\n"
        "1. Якщо клієнт просить живу людину або менеджера, ти ПОВИНЕН спочатку запитати: "
        "'Ви хочете зв'язатися з менеджером?' і чекати його відповіді.\n"
        "2. Якщо клієнт відповідає 'Так' на це питання, ти зобов'язаний написати фразу: "
        "'ЗАПИТ НА МЕНЕДЖЕРА ПРИЙНЯТО' та додати: 'З вами скоро зв'яжуться'.\n"
        "3. Якщо клієнт відповідає 'Ні', повертайся до консультації по товарах.\n"
        "ОФОРМЛЕННЯ ЗАМОВЛЕННЯ: Коли клієнт надає телефон і адресу, напиши 'ЗАМОВЛЕННЯ ПРИЙНЯТО' та подякуй.\n"
        "Пиши виключно українською мовою, лаконічно."
    )

    try:
        messages_payload = [{"role": "system", "content": system_instruction}] + user_sessions[user_id]

        chat_completion = await client.chat.completions.create(
            messages=messages_payload,
            model="llama-3.3-70b-versatile",
            temperature=0.3
        )
        
        reply_text = chat_completion.choices[0].message.content
        user_sessions[user_id].append({"role": "assistant", "content": reply_text})
        
        await message.answer(reply_text)

        # 1. Обработка подтвержденного запроса на менеджера
        if "ЗАПИТ НА МЕНЕДЖЕРА ПРИЙНЯТО" in reply_text.upper():
            if MY_TELEGRAM_ID != 0:
                history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in user_sessions[user_id]])
                await bot.send_message(
                    chat_id=MY_TELEGRAM_ID, 
                    text=f"🆘 КЛІЄНТ ПРОСИТЬ МЕНЕДЖЕРА!\nКлієнт: @{message.from_user.username or 'без ніка'}\nID: {user_id}\n\nЛог:\n{history_text}"
                )
            user_sessions[user_id] = [] # Очищаем сессию

        # 2. Обработка заказа
        elif "ЗАМОВЛЕННЯ ПРИЙНЯТО" in reply_text.upper():
            if MY_TELEGRAM_ID != 0:
                history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in user_sessions[user_id]])
                await bot.send_message(
                    chat_id=MY_TELEGRAM_ID, 
                    text=f"🔥 НОВЕ ЗАМОВЛЕННЯ!\nКлієнт: @{message.from_user.username or 'без ніка'}\nID: {user_id}\n\nЛог:\n{history_text}"
                )
            user_sessions[user_id] = []
            
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer("Вибачте, виникла технічна помилка.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
