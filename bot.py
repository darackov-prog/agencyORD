
import os
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
import asyncio

load_dotenv()

API_TOKEN = os.getenv("TG_BOT_API_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

questions = [
    "1. Наименование юрлица с ИНН",
    "2. Номер и дата договора",
    "3. Сумма услуг",
    "4. Блогеры",
    "5. Рекламодатель с ИНН",
    "6. Первый исполнитель с ИНН",
    "7. Номер и дата изначального договора",
    "8. Вид и предмет договора",
    "9. ККТУ и ОКВЭД",
    "10. Изготовитель токена",
    "11. Название проекта",
    "12. Ссылка на сайт",
    "13. Описание",
    "14. Площадка и тип",
    "15. Срок размещения"
]

class Form(StatesGroup):
    step = State()

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.set_state(Form.step)
    await state.update_data(answers=[], step=0)
    await message.answer("Заполните информацию:\n" + questions[0])

@dp.message(Form.step)
async def process_form(message: Message, state: FSMContext):
    data = await state.get_data()
    answers = data["answers"]
    step = data["step"]

    answers.append(message.text)
    step += 1

    if step < len(questions):
        await state.update_data(answers=answers, step=step)
        await message.answer(questions[step])
    else:
        result = "Новая анкета:\n\n"
        for i, answer in enumerate(answers):
            result += f"{questions[i]}:\n{answer}\n\n"

        await bot.send_message(ADMIN_ID, result)
        await message.answer("Спасибо! Данные отправлены.")
        await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
