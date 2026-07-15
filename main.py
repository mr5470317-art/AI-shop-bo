import os, asyncio, google.generativeai as genai
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command

bot = Bot(token=os.getenv("BOT_TOKEN", ""))
dp = Dispatcher()
genai.configure(api_key=os.getenv("GEMINI_API_KEY", ""))
model = genai.GenerativeModel('gemini-2.0-flash')

# Упрощенный каталог (без лишнего текста)
def get_prompt(user_text):
    cat = open("products.txt", "r", encoding="utf-8").read()[:1000] # Берем только 1000 знаков
    return f"Ти — StyleHub. Товари: {cat}. Правила: продавай тільки це, пиши українською, будь лаконічним. Клієнт: {user_text}"

@dp.message(F.text)
async def handle(m):
    try:
        response = model.generate_content(get_prompt(m.text))
        await m.answer(response.text)
    except:
        await m.answer("Трохи завантажений, спробуй через 30 секунд.")

async def main(): await dp.start_polling(bot)
if __name__ == "__main__": asyncio.run(main())
