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
    await message.answer("Привіт! Я твій консультант StyleHub. Чим можу допомогти?")

@dp.message(F.text)
async def handle_message(message: aiogram_types.Message):
    user_id = message.from_user.id
    
    if MY_TELEGRAM_ID and user_id == MY_TELEGRAM_ID:
        return

    if user_id not in user_sessions:
        user_sessions[user_id] = []

    user_sessions[user_id].append({"role": "user", "content": message.text})
    
    if len(user_sessions[user_id]) > 20:
        user_sessions[user_id] = user_sessions[user_id][-20:]

    catalog = get_products_data()
    
    system_instruction = (
        f"Ти — професійний консультант StyleHub. Асортимент: {catalog}. "
        "Твоя задача — допомагати з вибором, оформлювати та РЕДАГУВАТИ замовлення.\n"
        "ПРАВИЛА:\n"
        "1. Якщо клієнт просить змінити деталі (адресу, розмір) у вже оформленому замовленні — внеси зміну, обов'язково напиши фразу 'ЗАМОВЛЕННЯ ОНОВЛЕНО!' та підсумуй оновлені дані.\n"
        "2. Якщо клієнт хоче менеджера: запитай номер, перепитай підтвердження, після відповіді 'Так' напиши 'ЗАПИТ НА МЕНЕДЖЕРА ПРИЙНЯТО'.\n"
        "3. Якщо клієнт кидає номер телефону без контексту — запитай, для чого він (замовлення чи менеджер).\n"
        "4. ОФОРМЛЕННЯ: Коли є всі дані (товар, розмір, телефон, адреса) — напиши 'ЗАМОВЛЕННЯ ПРИЙНЯТО' та подякуй.\n"
        "Пиши виключно українською мовою, лаконічно."
    )

    try:
        messages_payload = [{"role": "system", "content": system_instruction}] + user_sessions[user_id]

        chat_completion = await client.chat.completions.create(
            messages=messages_payload,
            model="llama-3.3-70b-versatile",
            temperature=0.2
        )
        
        reply_text = chat_completion.choices[0].message.content
        user_sessions[user_id].append({"role": "assistant", "content": reply_text})
        
        await message.answer(reply_text)

        # Надежная отправка админу по любому ключевому слову статуса
        triggers = ["ЗАМОВЛЕННЯ ПРИЙНЯТО", "ЗАПИТ НА МЕНЕДЖЕРА ПРИЙНЯТО", "ЗАМОВЛЕННЯ ОНОВЛЕНО"]
        if any(trigger in reply_text.upper() for trigger in triggers):
            if MY_TELEGRAM_ID != 0:
                history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in user_sessions[user_id]])
                await bot.send_message(
                    chat_id=MY_TELEGRAM_ID, 
                    text=f"🔔 ЗМІНИ В ЗАМОВЛЕННІ / НОВИЙ ЗАПИТ!\nКлієнт: @{message.from_user.username or 'без ніка'}\nID: {user_id}\n\nЛог:\n{history_text}"
                )
            
        except Exception as e:
        logging.error(f"Ошибка: {e}")
        # Очищаем память пользователя при ошибке, чтобы убрать "битый" контекст
        user_sessions[user_id] = [] 
        await message.answer("Ой, здається, я заплутався. Давайте почнемо з чистого аркуша! Що вас цікавить з нашого асортименту?")
    

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
