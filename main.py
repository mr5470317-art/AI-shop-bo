import os
import asyncio
import logging
from groq import AsyncGroq # Используем библиотеку groq
from aiogram import Bot, Dispatcher, types as aiogram_types, F
from aiogram.filters import Command

logging.basicConfig(level=logging.INFO)

# Твой ключ с console.groq.com
GROQ_API_KEY = os.getenv("GROQ_API_KEY") 
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# Инициализация Groq
client = AsyncGroq(api_key=GROQ_API_KEY.strip())

@dp.message(F.text)
async def handle_message(message: aiogram_types.Message):
    system_instruction = "Ти — професійний консультант StyleHub. Твої відповіді мають бути літературною, грамотною українською мовою. Будь ввічливим."

    try:
        chat_completion = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": message.text}
            ],
            model="llama-3.3-70b-versatile", # Самая мощная модель, которая понимает укр идеально
            temperature=0.5
        )
        
        await message.answer(chat_completion.choices[0].message.content)
    except Exception as e:
        await message.answer(f"Помилка Groq: {str(e)}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
