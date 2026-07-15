import os
import logging
import asyncio
import google.generativeai as genai
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel(
    model_name='gemini-2.0-flash',
    generation_config={"temperature": 0.7, "max_output_tokens": 400}
)

user_sessions = {}

def load_catalog():
    try:
        if os.path.exists("products.txt"):
            with open("products.txt", "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
                return ", ".join(lines)
        return "Асортимент тимчасово відсутній."
    except Exception as e:
        logging.error(f"Ошибка чтения файла каталога: {e}")
        return "Асортимент тимчасово відсутній."

@dp.message(Command("start"))
async def cmd_start(message):
    user_sessions[message.from_user.id] = []
    await message.answer("Привіт! Я твій консультант у StyleHub. Як я можу тобі допомогти сьогодні?")

@dp.message(Command("reset"))
async def cmd_reset(message):
    user_sessions[message.from_user.id] = []
    await message.answer("Історію очищено! Давайте почнемо спочатку.")

@dp.message(F.text)
async def handle_message(message):
    user_id = message.from_user.id
    user_text = message.text

    if user_id not in user_sessions:
        user_sessions[user_id] = []

    # Ограничиваем историю последними 6 сообщениями, чтобы экономить бесплатные токены
    if len(user_sessions[user_id]) > 6:
        user_sessions[user_id] = user_sessions[user_id][-6:]

    user_sessions[user_id].append({"role": "user", "parts": [user_text]})

    try:
        catalog_text = load_catalog()
        
        system_instruction = (
            f"Ти — професійний консультант StyleHub. АСОРИМЕНТ: [{catalog_text}].\n"
            "ПРАВИЛА:\n"
            "1. Продавай ТІЛЬКИ товари з цього списку. Не вигадуй інші.\n"
            "2. Якщо змінюють замовлення — напиши 'ЗАМОВЛЕННЯ ОНОВЛЕНО!' та деталі.\n"
            "3. Якщо просять менеджера і підтвердили 'Так' — напиши 'ЗАПИТ НА МЕНЕДЖЕРА ПРИЙНЯТО'.\n"
            "4. Коли є товар, колір, розмір, телефон та адреса — напиши 'ЗАМОВЛЕННЯ ПРИЙНЯТО'.\n"
            "Пиши українською, коротко."
        )

        chat = model.start_chat(history=user_sessions[user_id][:-1])
        full_prompt = f"[ІНСТРУКЦІЯ]: {system_instruction}\n\nПовідомлення: {user_text}"
        
        response = chat.send_message(full_prompt)
        bot_response = response.text

        user_sessions[user_id].append({"role": "model", "parts": [bot_response]})
        await message.answer(bot_response)

        if any(marker in bot_response for marker in ["ЗАМОВЛЕННЯ ПРИЙНЯТО", "ЗАМОВЛЕННЯ ОНОВЛЕНО!", "ЗАПИТ НА МЕНЕДЖЕРА ПРИЙНЯТО"]):
            if ADMIN_ID and ADMIN_ID != 0:
                if "ЗАПИТ НА МЕНЕДЖЕРА ПРИЙНЯТО" in bot_response:
                    alert_title = "🚨 **КЛІЄНТ ПРОСИТЬ МЕНЕДЖЕРА!**"
                elif "ЗАМОВЛЕННЯ ОНОВЛЕНО!" in bot_response:
                    alert_title = "🔄 **ЗАМОВЛЕННЯ ОНОВЛЕНО!**"
                else:
                    alert_title = "📦 **НОВЕ ЗАМОВЛЕННЯ ПРИЙНЯТО!**"

                admin_text = (
                    f"{alert_title}\n\n"
                    f"👤 **Клієнт:** {message.from_user.full_name} (@{message.from_user.username}, ID: `{user_id}`)\n\n"
                    f"📋 **Деталі:**\n{bot_response}"
                )
                try:
                    await bot.send_message(chat_id=ADMIN_ID, text=admin_text, parse_mode="Markdown")
                except Exception as admin_err:
                    logging.error(f"Помилка відправки адміну: {admin_err}")

    except Exception as e:
        logging.error(f"Ошибка API или сети: {e}")
        await message.answer("Забагато запитів за хвилину, я трохи втомився. Зачекайте хвилину і повторіть повідомлення.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
