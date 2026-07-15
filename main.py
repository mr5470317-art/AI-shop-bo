import os
import asyncio
import logging
from groq import AsyncGroq
from aiogram import Bot, Dispatcher, types as aiogram_types, F
from aiogram.filters import Command

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Получение переменных окружения
GROQ_API_KEY = os.getenv("GROQ_API_KEY") 
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MY_TELEGRAM_ID = int(os.getenv("MY_TELEGRAM_ID", 0))

if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise ValueError("Не найдены переменные окружения TELEGRAM_TOKEN или GROQ_API_KEY!")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# Инициализация клиента Groq
client = AsyncGroq(api_key=GROQ_API_KEY.strip())

# Словарь для хранения памяти диалогов (user_id: [history])
user_sessions = {}

def get_products_data():
    """Читает данные из файлов ассортимента и каталога."""
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
    user_sessions[user_id] = [] # Сброс памяти при старте
    
    if MY_TELEGRAM_ID and user_id == MY_TELEGRAM_ID:
        await message.answer("Привіт, адміне! Бот готовий до роботи.")
    else:
        await message.answer("Привіт! Я твій консультант StyleHub. Чим можу допомогти?")

@dp.message(F.text)
async def handle_message(message: aiogram_types.Message):
    user_id = message.from_user.id
    
    if MY_TELEGRAM_ID and user_id == MY_TELEGRAM_ID:
        return # Игнорируем админа в рабочем чате

    # Инициализация памяти для пользователя
    if user_id not in user_sessions:
        user_sessions[user_id] = []

    # Добавляем сообщение пользователя в память
    user_sessions[user_id].append({"role": "user", "content": message.text})
    
    # Ограничение памяти (последние 10 сообщений)
    if len(user_sessions[user_id]) > 10:
        user_sessions[user_id] = user_sessions[user_id][-10:]

    catalog = get_products_data()
    
    system_instruction = (
        f"Ти — професійний консультант StyleHub. Твій асортимент: {catalog}. "
        "Твоя задача — допомагати клієнтам обирати товари. "
        "ВАЖЛИВО: Якщо питання не стосується одягу або магазину — ввічливо відмовляйся і повертай клієнта до теми. "
        "ОФОРМЛЕННЯ ЗАМОВЛЕННЯ: Коли клієнт надасть номер телефону та адресу, напиши 'ЗАМОВЛЕННЯ ПРИЙНЯТО' "
        "та подякуй за покупку. "
        "Підсумуй обраний товар, розмір та дані клієнта в кінці повідомлення. "
        "Відповідай грамотною українською мовою."
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

        # Отправка заказа админу
        if "ЗАМОВЛЕННЯ ПРИЙНЯТО" in reply_text.upper():
            if MY_TELEGRAM_ID != 0:
                history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in user_sessions[user_id]])
                await bot.send_message(
                    chat_id=MY_TELEGRAM_ID, 
                    text=f"🔥 НОВЕ ЗАМОВЛЕННЯ!\nКлієнт: @{message.from_user.username or 'без ніка'}\n\nЛог:\n{history_text}"
                )
            user_sessions[user_id] = [] # Очистка после заказа
            
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer("Вибачте, виникла технічна помилка.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
