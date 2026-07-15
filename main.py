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

# Инициализация Groq
client = AsyncGroq(api_key=GROQ_API_KEY.strip())

# Словарь для хранения истории сообщений каждого пользователя (память бота)
user_sessions = {}

def get_products_data():
    files = ["products.txt", "catalog.txt"]  # Читаем оба файла
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
    # Очищаем историю при новом старте
    if user_id in user_sessions:
        user_sessions[user_id] = []

    if MY_TELEGRAM_ID and user_id == MY_TELEGRAM_ID:
        await message.answer("Привіт, адміне! Це службовий чат.")
    else:
        await message.answer("Привіт! Я твій інтелектуальний помічник-консультант StyleHub. Чим можу допомогти?")

@dp.message(F.text)
async def handle_message(message: aiogram_types.Message):
    user_id = message.from_user.id
    
    if MY_TELEGRAM_ID and user_id == MY_TELEGRAM_ID:
        await message.answer("Це службовий чат адміністратора. Клієнтів тут немає.")
        return

    # Инициализируем историю для пользователя, если её нет
    if user_id not in user_sessions:
        user_sessions[user_id] = []

    # Добавляем свежее сообщение пользователя в историю
    user_sessions[user_id].append({"role": "user", "content": message.text})

    # Ограничиваем историю последними 10 сообщениями, чтобы бот не «перегружался»
    if len(user_sessions[user_id]) > 10:
        user_sessions[user_id] = user_sessions[user_id][-10:]

    # Собираем данные из файлов
    catalog = get_products_data()
    
    system_instruction = (
        f"Ти — професійний консультант магазину одягу StyleHub. "
        f"Твій асортимент та дані про товари з файлів: {catalog}. "
        "Твоя задача — допомагати клієнтам обирати одяг, пам'ятати контекст розмови (обраний товар, розмір тощо) та відповідати за цим списком. "
        "ВАЖЛИВО: Якщо питання не стосується одягу, стилю чи нашого магазину — ввічливо відмовляйся: "
        "'Вибачте, я можу допомогти лише з питаннями щодо одягу та стилю StyleHub.' "
        "ОФОРМЛЕННЯ ЗАМОВЛЕННЯ: Якщо клієнт погоджується купувати та надав контактні дані (номер телефону, адресу), обов'язково відповідай покупцю фразою "
        "'ЗАМОВЛЕННЯ ПРИЙНЯТО' і додай: 'Дякуємо за покупку, нам було приємно з вами працювати!' "
        "Відповідай виключно лаконічно та грамотною українською мовою, не перепитуй те, що клієнт уже назвав."
    )

    try:
        # Отправляем системный промпт + всю историю диалога
        messages_payload = [{"role": "system", "content": system_instruction}] + user_sessions[user_id]

        chat_completion = await client.chat.completions.create(
            messages=messages_payload,
            model="llama-3.3-70b-versatile",
            temperature=0.3
        )
        
        reply_text = chat_completion.choices[0].message.content
        
        # Сохраняем ответ бота в историю
        user_sessions[user_id].append({"role": "assistant", "content": reply_text})
        
        await message.answer(reply_text)

        # Проверка на успешное оформление заказа
        if "ЗАМОВЛЕННЯ ПРИЙНЯТО" in reply_text.upper():
            if MY_TELEGRAM_ID != 0:
                await bot.send_message(
                    chat_id=MY_TELEGRAM_ID, 
                    text=f"🔥 НОВЕ ЗАМОВЛЕННЯ!\nКлієнт: @{message.from_user.username or 'без ніка'}\nID: {user_id}\n\nВідповідь бота:\n{reply_text}"
                )
            
    except Exception as e:
        logging.error(f"Ошибка Groq API: {e}")
        await message.answer(f"Помилка: {str(e)}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
