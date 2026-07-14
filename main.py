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

def get_products_data():
    files = ["products.txt", "catalog.txt"]  # Читаем сразу оба файла, если они есть
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

    # Собираем данные из файлов
    catalog = get_products_data()
    
    system_instruction = (
        f"Ти — професійний консультант магазину одягу StyleHub. "
        f"Твій асортимент та дані про товари з файлів: {catalog}. "
        "Твоя задача — допомагати клієнтам обирати одяг та відповідати на питання за цим списком. "
        "ВАЖЛИВО: Якщо питання не стосується одягу, стилю чи нашого магазину — ввічливо відмовляйся: "
        "'Вибачте, я можу допомогти лише з питаннями щодо одягу та стилю StyleHub.' "
        "ОФОРМЛЕННЯ ЗАМОВЛЕННЯ: Якщо клієнт погоджується купувати, попроси номер телефону та адресу доставки. "
        "Як тільки він надасть дані, обов'язково відповідай покупцю фразою 'ЗАМОВЛЕННЯ ПРИЙНЯТО' і додай: "
        "'Дякуємо за покупку, нам було приємно з вами працювати!' "
        "Відповідай виключно грамотною українською мовою."
    )

    try:
        chat_completion = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": message.text}
            ],
            model="llama-3.3-70b-versatile",  # Топовая бесплатная модель с отличным знанием украинского
            temperature=0.4
        )
        
        reply_text = chat_completion.choices[0].message.content
        await message.answer(reply_text)

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
