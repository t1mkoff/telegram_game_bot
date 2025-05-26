from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from database import Database
from wallet import Wallet
from game import MathGame
from config import BOT_TOKEN
import asyncio
import os
import random

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Инициализация базы данных
db = Database('game.db')

# Словари для хранения данных пользователей
user_answers = {}
user_bets = {}
REWARD = 100

# Создаем клавиатуру
def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💰 Баланс")],
            [KeyboardButton(text="💸 Заработать"), KeyboardButton(text="🎲 Играть в кости"), KeyboardButton(text="🎰 Слоты")]
        ],
        resize_keyboard=True,
        persistent=True
    )
    return keyboard

# Создаем клавиатуру для выбора типа ставки
def get_dice_bet_type_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Чёт/Нечет (x2)", callback_data="dice_even_odd")],
        [InlineKeyboardButton(text="Конкретное число (x6)", callback_data="dice_exact")]
    ])
    return keyboard

# Создаем клавиатуру для выбора чёт/нечет
def get_even_odd_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Чётное", callback_data="bet_even"),
         InlineKeyboardButton(text="Нечётное", callback_data="bet_odd")]
    ])
    return keyboard

# Создаем клавиатуру для выбора конкретного числа
def get_number_keyboard():
    buttons = []
    row = []
    for i in range(1, 7):
        row.append(InlineKeyboardButton(text=str(i), callback_data=f"bet_number_{i}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

# Add this helper function after the keyboard functions
def get_mention(user) -> str:
    if user.username:
        return f"@{user.username}"
    # Используем raw строки для экранирования специальных символов Markdown
    full_name = user.full_name.replace("_", r"\_").replace("*", r"\*").replace("[", r"\[").replace("]", r"\]").replace("`", r"\`")
    return f"[{full_name}](tg://user/{user.id})"

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    user_mention = get_mention(message.from_user)
    
    # Регистрация пользователя, если он новый
    if not db.user_exists(user_id):
        db.add_user(user_id, username)
        await message.answer(
            f"{user_mention}, добро пожаловать в игру! Ваш начальный баланс: 0 монет\n\n"
            f"Используйте кнопки ниже для навигации:",
            reply_markup=get_main_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        balance = db.get_balance(user_id)
        await message.answer(
            f"{user_mention}, с возвращением! Ваш баланс: {balance} монет\n\n"
            f"Используйте кнопки ниже для навигации:",
            reply_markup=get_main_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

@dp.message(lambda message: message.text == "💰 Баланс")
async def balance_button_handler(message: types.Message):
    user_id = message.from_user.id
    user_mention = get_mention(message.from_user)
    wallet = Wallet(db, user_id)
    balance = wallet.get_balance()
    sent_message = await message.answer(
        f"{user_mention}, 💰 Ваш текущий баланс: {balance} монет",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Создаем задачи на удаление сообщений
    asyncio.create_task(delete_message_after_delay(sent_message, 5))
    asyncio.create_task(delete_message_after_delay(message, 5))

@dp.message(lambda message: message.text == "💸 Заработать")
async def earn_button_handler(message: types.Message):
    user_id = message.from_user.id
    user_mention = get_mention(message.from_user)
    game = MathGame()
    problem, correct_answer = game.generate_problem()
    
    # Сохраняем правильный ответ для пользователя
    user_answers[user_id] = correct_answer
    
    # Отправляем сообщение и сохраняем его для последущего удаления
    sent_message = await message.answer(
        f"{user_mention}, решите пример:\n\n{problem}",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Создаем задачу на удаление сообщения через 5 секунд
    asyncio.create_task(delete_message_after_delay(sent_message, 5))

@dp.message(lambda message: message.text == "🎲 Играть в кости")
async def dice_game_handler(message: types.Message):
    sent_message = await message.answer(
        "Выберите тип ставки:\n\n"
        "• Чёт/Нечет - выигрыш x2\n"
        "• Конкретное число - выигрыш x6\n\n"
        "После выбора типа ставки, укажите сумму.",
        reply_markup=get_dice_bet_type_keyboard()
    )
    # Создаем задачи на удаление сообщений
    asyncio.create_task(delete_message_after_delay(sent_message, 5))
    asyncio.create_task(delete_message_after_delay(message, 5))

@dp.callback_query(lambda c: c.data == "dice_even_odd")
async def dice_even_odd_handler(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    user_bets[user_id] = {"type": "even_odd"}
    
    await callback_query.message.edit_text(
        "Выберите чётное или нечётное:\n\n"
        "Введите сумму ставки в следующем сообщении.",
        reply_markup=get_even_odd_keyboard()
    )

@dp.callback_query(lambda c: c.data == "dice_exact")
async def dice_exact_handler(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    user_bets[user_id] = {"type": "exact"}
    
    await callback_query.message.edit_text(
        "Выберите число от 1 до 6:\n\n"
        "Введите сумму ставки в следующем сообщении.",
        reply_markup=get_number_keyboard()
    )

@dp.callback_query(lambda c: c.data.startswith("bet_"))
async def process_bet_choice(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    choice = callback_query.data
    
    if user_id not in user_bets:
        await callback_query.answer("Начните игру заново.")
        return
    
    if choice.startswith("bet_number_"):
        number = int(choice.split("_")[2])
        user_bets[user_id]["choice"] = number
        sent_message = await callback_query.message.edit_text(f"Вы выбрали число {number}. Введите сумму ставки:")
    elif choice in ["bet_even", "bet_odd"]:
        user_bets[user_id]["choice"] = choice
        choice_text = "чётное" if choice == "bet_even" else "нечётное"
        sent_message = await callback_query.message.edit_text(f"Вы выбрали {choice_text}. Введите сумму ставки:")
    
    # Создаем задачу на удаление сообщения
    asyncio.create_task(delete_message_after_delay(sent_message, 5))

@dp.message(lambda message: message.text == "🎰 Слоты")
async def slots_game_handler(message: types.Message):
    user_id = message.from_user.id
    user_mention = get_mention(message.from_user)
    
    # Инициализируем игру в слоты
    user_bets[user_id] = {"type": "slots"}
    
    sent_message = await message.answer(
        f"{user_mention}, введите сумму ставки:\n\n"
        f"• Джекпот (три в ряд) - выигрыш x10\n"
        f"• Два одинаковых символа - возврат ставки\n"
        f"• Разные символы - проигрыш",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Создаем задачи на удаление сообщений
    asyncio.create_task(delete_message_after_delay(sent_message, 5))
    asyncio.create_task(delete_message_after_delay(message, 5))

@dp.message()
async def process_message(message: types.Message):
    user_id = message.from_user.id
    user_mention = get_mention(message.from_user)
    
    # Проверяем, играет ли пользователь в слоты
    if user_id in user_bets and user_bets[user_id].get("type") == "slots":
        try:
            bet_amount = int(message.text)
            if bet_amount <= 0:
                raise ValueError
            
            wallet = Wallet(db, user_id)
            balance = wallet.get_balance()
            
            if bet_amount > balance:
                sent_message = await message.answer(
                    f"{user_mention}, у вас недостаточно монет для такой ставки!",
                    parse_mode=ParseMode.MARKDOWN
                )
                asyncio.create_task(delete_message_after_delay(sent_message, 5))
                return
            
            # Списываем ставку
            wallet.subtract_coins(bet_amount)
            
            # Отправляем слот
            slot_message = await message.answer_dice(emoji="🎰")
            slot_value = slot_message.dice.value
            
            # Ждем анимацию
            await asyncio.sleep(5)
            
            # Определяем выигрыш
            if slot_value == 64:  # Джекпот (три в ряд)
                multiplier = 10
                win_amount = bet_amount * multiplier
                wallet.add_coins(win_amount)
                result_text = f"🎉 ДЖЕКПОТ! Вы выиграли {win_amount} монет!"
            elif slot_value in [1, 2, 3, 4, 5]:  # Два одинаковых символа
                multiplier = 1
                win_amount = bet_amount * multiplier
                wallet.add_coins(win_amount)
                result_text = f"🎯 Два одинаковых символа! Ваша ставка возвращена: {win_amount} монет."
            else:  # Проигрыш
                result_text = "😔 К сожалению, вы проиграли."
            
            # Отправляем результат
            sent_message = await message.answer(
                f"{user_mention}, {result_text}\n\n"
                f"💰 Ваш баланс: {wallet.get_balance()} монет",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Удаляем сообщения через 5 секунд
            asyncio.create_task(delete_message_after_delay(sent_message, 5))
            asyncio.create_task(delete_message_after_delay(message, 5))
            asyncio.create_task(delete_message_after_delay(slot_message, 5))
            
            # Очищаем данные ставки
            del user_bets[user_id]
            
        except ValueError:
            sent_message = await message.answer(
                f"{user_mention}, пожалуйста, введите корректную сумму ставки (целое число больше 0).",
                parse_mode=ParseMode.MARKDOWN
            )
            asyncio.create_task(delete_message_after_delay(sent_message, 5))
            return
    
    # Проверяем, есть ли активная игра в кости
    elif user_id in user_bets and "choice" in user_bets[user_id]:
        try:
            bet_amount = int(message.text)
            if bet_amount <= 0:
                raise ValueError
            
            wallet = Wallet(db, user_id)
            balance = wallet.get_balance()
            
            if bet_amount > balance:
                sent_message = await message.answer(
                    f"{user_mention}, у вас недостаточно монет для такой ставки!",
                    parse_mode=ParseMode.MARKDOWN
                )
                asyncio.create_task(delete_message_after_delay(sent_message, 5))
                return
            
            # Списываем ставку
            wallet.subtract_coins(bet_amount)
            
            # Отправляем кубик
            dice_message = await message.answer_dice(emoji="🎲")
            dice_value = dice_message.dice.value
            
            # Ждем анимацию
            await asyncio.sleep(5)
            
            # Определяем выигрыш для игры в кости
            bet_type = user_bets[user_id]["type"]
            choice = user_bets[user_id]["choice"]
            
            if bet_type == "exact" and choice == dice_value:
                # Выигрыш x6 за угаданное число
                multiplier = 6
                win_amount = bet_amount * multiplier
                wallet.add_coins(win_amount)
                result_text = f"🎉 Выпало число {dice_value}! Вы выиграли {win_amount} монет!"
            elif bet_type == "even_odd":
                is_even = dice_value % 2 == 0
                if (choice == "bet_even" and is_even) or (choice == "bet_odd" and not is_even):
                    # Выигрыш x2 за угаданную четность
                    multiplier = 2
                    win_amount = bet_amount * multiplier
                    wallet.add_coins(win_amount)
                    result_text = f"🎯 Выпало {'четное' if is_even else 'нечетное'} число {dice_value}! Вы выиграли {win_amount} монет!"
                else:
                    result_text = f"😔 Выпало {'четное' if is_even else 'нечетное'} число {dice_value}. Вы проиграли."
            else:
                result_text = f"😔 Выпало число {dice_value}. Вы проиграли."
            
            # Отправляем результат
            sent_message = await message.answer(
                f"{user_mention}, {result_text}\n\n"
                f"💰 Ваш баланс: {wallet.get_balance()} монет",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Удаляем сообщения через 5 секунд
            asyncio.create_task(delete_message_after_delay(sent_message, 5))
            asyncio.create_task(delete_message_after_delay(message, 5))
            asyncio.create_task(delete_message_after_delay(dice_message, 5))  # Добавляем удаление кубика
            
            # Очищаем данные ставки
            del user_bets[user_id]
            
        except ValueError:
            sent_message = await message.answer(
                f"{user_mention}, пожалуйста, введите корректную сумму ставки (целое число больше 0).",
                parse_mode=ParseMode.MARKDOWN
            )
            asyncio.create_task(delete_message_after_delay(sent_message, 5))
            return
    
    # Проверяем ответ на математический пример
    elif user_id in user_answers:
        try:
            user_answer = int(message.text)
            correct_answer = user_answers[user_id]
            
            if user_answer == correct_answer:
                # Начисляем награду
                wallet = Wallet(db, user_id)
                new_balance = wallet.add_coins(REWARD)
                
                sent_message = await message.answer(
                    f"{user_mention}, ✅ Правильно! На ваш баланс зачислено {REWARD} монет.\n"
                    f"Текущий баланс: {new_balance} монет."
                )
                
                # Удаляем ответ из словаря
                del user_answers[user_id]
                
            else:
                # Генерируем новый пример
                game = MathGame()
                problem, new_answer = game.generate_problem()
                
                # Обновляем правильный ответ
                user_answers[user_id] = new_answer
                
                sent_message = await message.answer(
                    f"{user_mention}, ❌ Неправильно, попробуйте ещё раз!\n\n"
                    f"Новый пример:\n{problem}"
                )
            
            # Создаем задачу на удаление сообщения через 5 секунд
            asyncio.create_task(delete_message_after_delay(sent_message, 5))
            # Также удаляем сообщение пользователя
            asyncio.create_task(delete_message_after_delay(message, 5))
                
        except ValueError:
            # Если введено не число, игнорируем
            return

# Удалите полностью функцию check_answer

@dp.message()
async def check_answer(message: types.Message):
    user_id = message.from_user.id
    
    # Проверяем, есть ли у пользователя активный пример
    if user_id not in user_answers:
        return
    
    try:
        user_answer = int(message.text)
        correct_answer = user_answers[user_id]
        
        if user_answer == correct_answer:
            # Начисляем награду
            wallet = Wallet(db, user_id)
            new_balance = wallet.add_coins(REWARD)
            
            sent_message = await message.answer(
                f"✅ Правильно! На ваш баланс зачислено {REWARD} монет.\n"
                f"Текущий баланс: {new_balance} монет."
            )
            
            # Удаляем ответ из словаря
            del user_answers[user_id]
            
        else:
            # Генерируем новый пример
            game = MathGame()
            problem, new_answer = game.generate_problem()
            
            # Обновляем правильный ответ
            user_answers[user_id] = new_answer
            
            sent_message = await message.answer(
                f"❌ Неправильно, попробуйте ещё раз!\n\n"
                f"Новый пример:\n{problem}"
            )
        
        # Создаем задачу на удаление сообщения через 5 секунд
        asyncio.create_task(delete_message_after_delay(sent_message, 5))
        # Также удаляем сообщение пользователя
        asyncio.create_task(delete_message_after_delay(message, 5))
            
    except ValueError:
        # Если введено не число, игнорируем
        return

# Функция для удаления сообщения после задержки
async def delete_message_after_delay(message: types.Message, delay: int):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        # Игнорируем ошибки при удалении сообщения
        pass

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())