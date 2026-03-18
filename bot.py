import os
import re
from aiogram import Bot, Dispatcher
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import CommandStart, Command
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

# Вопросы анкеты
questions = [
    "1. Наименование вашего юридического лица с указанием инн (Отвечать только в таком формате: ООО «Ромашка» 765432675)",
    "2. Номер и дата договора между нами (При наличии приложения указать договор + приложение)",
    "3. Сумма услуг (общая сумма) (При наличии в договоре детализации на размещение - указать сумму на размещение и сумму общую. Отвечать только в таком формате: 25324,33 или 25324,33 - размещение, 50000 - общая)",
    "4. Рекламодатель (Обязательно указание инн. Отвечать только в таком формате: ООО «Ромашка» 784565432)",
    "5. Первый исполнитель в цепочке договоров с рекламодателем (Обязательно указание инн. Отвечать только в таком формате: ООО «Ромашка» 784565432)",
    "6. Номер и дата изначального договора (между рекламодателем и первым исполнителем в цепочке договоров с рекламодателем) (Отвечать только в таком формате: № 1882 от 21.06.2025)",
    "7. Вид (оказание услуг, посредничество, дополнительное соглашение) и предмет договора (посредничество, распространение рекламы, организация распространения рекламы, представительство, иное) (Отвечать только в таком формате: Оказание услуг, организация распространение)",
    "8. Название проекта",
    "9. Площадка и тип размещения (Пример: ВК, пост)",
    "10. Срок размещения публикации (Дата, после которой возможно удаление)"
]

class Form(StatesGroup):
    step = State()

# Создаём клавиатуру для навигации
def get_nav_keyboard():
    buttons = [
        [KeyboardButton(text="⬅️ Назад"), KeyboardButton(text="🔄 Заполнить заново")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# Функция для проверки ответов
def validate_answer(question_index: int, answer: str) -> tuple[bool, str]:
    """
    Проверяет ответ на соответствие формату.
    Возвращает (прошло_проверку, сообщение_об_ошибке)
    """
    
    # Проверка для вопросов с ИНН (вопросы 0, 3, 4)
    if question_index in [0, 3, 4]:  # Название юрлица с ИНН
        # Ищем 10 или 12 цифр подряд (ИНН юрлица или ИП)
        if not re.search(r'\b\d{10}\b|\b\d{12}\b', answer):
            return False, "❌ В ответе должен быть указан ИНН (10 или 12 цифр).\nПример: ООО «Ромашка» 765432675"
    
    # Проверка для вопроса с суммой (вопрос 2)
    elif question_index == 2:
        # Проверяем, есть ли в ответе число с запятой или точкой
        if not re.search(r'\d+[.,]?\d*', answer):
            return False, "❌ Укажите сумму в формате: 25324,33 или 25324,33 - размещение, 50000 - общая"
    
    # Проверка для вопроса с датой договора (вопросы 1 и 5)
    elif question_index in [1, 5]:
        # Проверяем наличие номера и даты
        if not re.search(r'№?\s*\d+', answer) or not re.search(r'\d{1,2}\.\d{1,2}\.\d{2,4}', answer):
            return False, "❌ Укажите номер и дату договора.\nПример: № 1882 от 21.06.2025"
    
    # Проверка для вопроса с проектом (вопрос 7) - тут особая логика
    elif question_index == 7:
        # Проверяем, что выбрано хотя бы одно из ключевых слов
        keywords = ['оказание услуг', 'посредничество', 'дополнительное соглашение', 
                   'распространение рекламы', 'представительство', 'иное']
        found = any(keyword in answer.lower() for keyword in keywords)
        if not found:
            return False, f"❌ Укажите вид и предмет договора.\nПример: Оказание услуг, организация распространение"
    
    return True, ""

# Обработчик команды /start
@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.set_state(Form.step)
    await state.update_data(answers=[], step=0)
    await message.answer(
        "📋 Заполните информацию:\n\n" + questions[0],
        reply_markup=get_nav_keyboard()
    )

# Обработчик команды /cancel (для выхода)
@dp.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "❌ Заполнение отменено. Чтобы начать заново, нажмите /start",
        reply_markup=ReplyKeyboardRemove()
    )

# Основной обработчик анкеты
@dp.message(Form.step)
async def process_form(message: Message, state: FSMContext):
    # Получаем текущее состояние
    data = await state.get_data()
    answers = data.get("answers", [])
    step = data.get("step", 0)
    
    # Обработка кнопки "Заполнить заново"
    if message.text == "🔄 Заполнить заново":
        await state.set_state(Form.step)
        await state.update_data(answers=[], step=0)
        await message.answer(
            "🔄 Начинаем сначала!\n\n" + questions[0],
            reply_markup=get_nav_keyboard()
        )
        return
    
    # Обработка кнопки "Назад"
    if message.text == "⬅️ Назад":
        if step > 0:
            # Удаляем последний ответ и уменьшаем шаг
            answers = answers[:-1]
            step -= 1
            await state.update_data(answers=answers, step=step)
            await message.answer(
                f"⬅️ Возвращаемся к предыдущему вопросу:\n\n{questions[step]}",
                reply_markup=get_nav_keyboard()
            )
        else:
            await message.answer(
                "⛔ Это первый вопрос. Вы не можете вернуться назад.",
                reply_markup=get_nav_keyboard()
            )
        return
    
    # ВАЛИДАЦИЯ: проверяем ответ перед сохранением
    is_valid, error_message = validate_answer(step, message.text)
    
    if not is_valid:
        await message.answer(
            f"{error_message}\n\nПопробуйте ещё раз:",
            reply_markup=get_nav_keyboard()
        )
        return
    
    # Если проверка пройдена, сохраняем ответ
    answers.append(message.text)
    step += 1
    
    # Переходим к следующему вопросу или завершаем
    if step < len(questions):
        await state.update_data(answers=answers, step=step)
        await message.answer(
            questions[step],
            reply_markup=get_nav_keyboard()
        )
    else:
        # Формируем результат
        result = "✅ Новая анкета:\n\n"
        result += f"👤 От: @{message.from_user.username or 'нет username'} (ID: {message.from_user.id})\n"
        result += f"📅 Дата: {message.date.strftime('%d.%m.%Y %H:%M')}\n\n"
        
        for i, answer in enumerate(answers):
            result += f"❓ {questions[i]}\n📝 {answer}\n\n{'-'*30}\n"
        
        # Отправляем админу
        await bot.send_message(ADMIN_ID, result)
        
        # Отправляем подтверждение пользователю
        await message.answer(
            "✅ Спасибо! Ваши данные успешно отправлены.\n"
            "Чтобы заполнить новую анкету, нажмите /start",
            reply_markup=ReplyKeyboardRemove()
        )
        
        # Очищаем состояние
        await state.clear()

# Команда для админа - статистика (простая версия)
@dp.message(Command("stats"))
async def stats(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Эта команда только для администратора")
        return
    
    # Здесь можно добавить реальную статистику из БД
    await message.answer(
        "📊 Статистика:\n"
        "• Функция в разработке\n"
        "• Для продвинутой статистики нужно подключить базу данных"
    )

async def main():
    print("🤖 Бот запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
