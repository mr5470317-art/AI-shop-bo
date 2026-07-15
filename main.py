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

# Память диалогов
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
        f"Ти — професійний консультант StyleHub. Твій асортимент: {catalog}. "
        "Твоя задача — допомагати з вибором одягу, оформлювати замовлення або з'єднувати з менеджером.\n\n"
        "ПРАВИЛА ДЛЯ ЗВ'ЯЗКУ З МЕНЕДЖЕРОМ:\n"
        "1. Якщо клієнт просить покликати менеджера чи людину, ввічливо запитай його номер телефону.\n"
        "2. Коли клієнт у відповідь на це пише номер телефону, ти повинен ОБОВ'ЯЗКОВО перепитати для підтвердження: "
        "'Ви підтверджуєте запит на дзвінок менеджера на номер [вказаний номер]?'\n"
        "3. ТІЛЬКИ після того, як клієнт відповість 'Так' або підтвердить це, напиши фінальну фразу: "
        "'ЗАПИТ НА МЕНЕДЖЕРА ПРИЙНЯТО. Адміністратор скоро вам зателефонує.'\n\n"
        "ПРАВИЛА ДЛЯ ОФОРМЛЕННЯ ЗАМОВЛЕННЯ:\n"
        "1. Якщо клієнт купує товар і просто залишив номер телефону без адреси, НЕ відправляй його до менеджера. "
        "Замість цього запитай адресу доставки, щоб завершити оформлення замовлення.\n"
        "2. Коли у тебе є всі дані (товар, розмір, телефон та адреса), напиши фразу: "
        "'ЗАМОВЛЕННЯ ПРИЙНЯТО' та подякуй за покупку.\n\n"
        "ЗАГАЛЬНІ ПРАВИЛА:\n"
        "- Якщо клієнт просто надіслав номер телефону БЕЗ будь-якого контексту, запитай: "
        "'Ви бажаєте зв'язатися з менеджером чи оформити замовлення?'\n"
        "- Пиши виключно українською мовою, лаконічно, без зайвих роздумів."
    )

    try:
        messages_payload = [{"role": "system", "content": system_instruction}] + user_sessions[user_id]

        chat_completion = await client.chat.completions.create(
            messages=messages_payload,
            model="llama-3.3-70b-versatile",
            temperature=0.2  # Немного снизили температуру для еще большей точности
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
                    text=f"🆘 ДЗВІНОК МЕНЕДЖЕРА!\nКлієнт: @{message.from_user.username or 'без ніка'}\nID: {user_id}\n\nЛог розмови:\n{history_text}"
                )
            user_sessions[user_id] = [] # Очищаем сессию

        # 2. Обработка заказа товара
        elif "ЗАМОВЛЕННЯ ПРИЙНЯТО" in reply_text.upper():
            if MY_TELEGRAM_ID != 0:
                history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in user_sessions[user_id]])
                await bot.send_message(
                    chat_id=MY_TELEGRAM_ID, 
                    text=f"🔥 НОВЕ ЗАМОВЛЕННЯ!\nКлієнт: @{message.from_user.username or 'без ніка'}\nID: {user_id}\n\nДеталі:\n{history_text}"
                )
            user_sessions[user_id] = []
            
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer("Вибачте, виникла технічна помилка.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
