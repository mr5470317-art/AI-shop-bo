import os
import logging
from aiogram import Bot, Dispatcher, F, types as aiogram_types
from aiogram.filters import Command
from groq import Groq

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Получаем ключи и ID администратора
BOT_TOKEN = os.getenv("BOT_TOKEN", "ТВОЙ_ТОКЕН_ТЕЛЕГРАМ_БОТА")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "ТВОЙ_КЛЮЧ_GROQ")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))  # Твой Telegram ID из переменных Railway

# Инициализация бота и клиента Groq
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = Groq(api_key=GROQ_API_KEY)

# Словарь для хранения истории диалогов пользователей
user_sessions = {}

# Функция для чтения каталога из файла
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
async def cmd_start(message: aiogram_types.Message):
    user_id = message.from_user.id
    user_sessions[user_id] = []
    await message.answer("Привіт! Я твій консультант у StyleHub. Як я можу тобі допомогти сьогодні?")

@dp.message(Command("reset"))
async def cmd_reset(message: aiogram_types.Message):
    user_id = message.from_user.id
    user_sessions[user_id] = []
    await message.answer("Історію очищено! Давайте почнемо спочатку.")

@dp.message(F.text)
async def handle_message(message: aiogram_types.Message):
    user_id = message.from_user.id
    user_text = message.text

    # Инициализируем историю для нового пользователя, если её нет
    if user_id not in user_sessions:
        user_sessions[user_id] = []

    # Добавляем сообщение пользователя в историю
    user_sessions[user_id].append({"role": "user", "content": user_text})

    try:
        # Читаем актуальный каталог из файла на лету
        catalog_text = load_catalog()

        # Системный промпт с жестким требованием адреса и телефона
        system_prompt = {
            "role": "system", 
            "content": (
                f"Ти — професійний консультант StyleHub. ТЕКУЧИЙ АСОРИМЕНТ МАГАЗИНУ: [{catalog_text}].\n"
                "ПРАВИЛА:\n"
                "1. Продавай та пропонуй покупцям ВИКЛЮЧНО товари з поточного асортименту вище. Категорично заборонено вигадувати інші моделі, бренди чи товари, яких немає в цьому списку.\n"
                "2. Якщо клієнт просить змінити деталі (адресу, розмір) у вже оформленому замовленні — внеси зміну, обов'язково напиши фразу 'ЗАМОВЛЕННЯ ОНОВЛЕНО!' та підсумуй оновлені дані.\n"
                "3. Якщо клієнт хоче менеджера: запитай номер, перепитай підтвердження, після відповіді 'Так' напиши 'ЗАПИТ НА МЕНЕДЖЕРА ПРИЙНЯТО'.\n"
                "4. Якщо клієнт кидає номер телефону без контексту — запитай, для чого він (замовлення чи менеджер).\n"
                "5. ОФОРМЛЕННЯ (СУВОРО): Коли є всі дані — товар, колір, розмір, телефон ТА адреса доставки — тоді напиши 'ЗАМОВЛЕННЯ ПРИЙНЯТО' та подякуй. ЗАБОРОНЕНО писати 'ЗАМОВЛЕННЯ ПРИЙНЯТО', якщо клієнт ще не назвав адресу або телефон!\n"
                "Пиши виключно українською мовою, лаконічно."
            )
        }

        # ЕКОНОМІЯ ТОКЕНОВ: берем последние 4 сообщения, чтобы не превышать суточные лимиты
        recent_history = user_sessions[user_id][-4:]

        # Отправляем запрос к мощной модели Groq API
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[system_prompt] + recent_history,
            temperature=0.7,
            max_tokens=500
        )

        bot_response = completion.choices[0].message.content

        # Добавляем ответ бота в историю
        user_sessions[user_id].append({"role": "assistant", "content": bot_response})

        # Отправляем ответ пользователю в Telegram
        await message.answer(bot_response)

        # УВЕДОМЛЕНИЕ АДМИНУ С РАЗЛИЧЕНИЕМ ТИПОВ СОБЫТИЙ
        if any(marker in bot_response for marker in ["ЗАМОВЛЕННЯ ПРИЙНЯТО", "ЗАМОВЛЕННЯ ОНОВЛЕНО!", "ЗАПИТ НА МЕНЕДЖЕРА ПРИЙНЯТО"]):
            if ADMIN_ID and ADMIN_ID != 0:
                
                # Определяем заголовок в зависимости от того, что ответил бот
                if "ЗАПИТ НА МЕНЕДЖЕРА ПРИЙНЯТО" in bot_response:
                    alert_title = "🚨 **КЛІЄНТ ПРОСИТЬ МЕНЕДЖЕРА!**"
                    task_instruction = "Виділи з діалогу останній номер телефону та ім'я клієнта (або контекст питання). Коротко."
                elif "ЗАМОВЛЕННЯ ОНОВЛЕНО!" in bot_response:
                    alert_title = "🔄 **ЗАМОВЛЕННЯ ОНОВЛЕНО!**"
                    task_instruction = "Виділи з діалогу оновлені дані замовлення (товар, розмір, телефон, адреса). Коротко."
                else:
                    alert_title = "📦 **НОВЕ ЗАМОВЛЕННЯ ПРИЙНЯТО!**"
                    task_instruction = "Виділи з діалогу деталі замовлення (товар, розмір, телефон, адреса). Коротко."

                # Делаем короткий запрос для выжимки данных
                summary_prompt = [
                    {"role": "system", "content": f"{task_instruction} Виведи інформацію чітко і лаконічно, без зайвих слів."},
                    {"role": "user", "content": "\n".join([f"{m['role']}: {m['content']}" for m in user_sessions[user_id]])}
                ]
                
                try:
                    summary_resp = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=summary_prompt,
                        temperature=0.3,
                        max_tokens=150
                    )
                    order_details = summary_resp.choices[0].message.content
                except:
                    order_details = "Не вдалося автоматично згорнути деталі."

                admin_text = (
                    f"{alert_title}\n\n"
                    f"👤 **Клієнт:** {message.from_user.full_name} (@{message.from_user.username}, ID: `{user_id}`)\n\n"
                    f"📋 **Інформація:**\n{order_details}"
                )
                try:
                    await bot.send_message(chat_id=ADMIN_ID, text=admin_text, parse_mode="Markdown")
                except Exception as admin_err:
                    logging.error(f"Помилка відправки адміну: {admin_err}")

    except Exception as e:
        logging.error(f"Ошибка API или сети: {e}")
        user_sessions[user_id] = []
        await message.answer("Ой, здається, сталася невеличка технічна помилка або я втомився. Давайте почнемо з чистого аркуша! Що вас цікавить?")

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
