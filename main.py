from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from database import Database
from wallet import Wallet
from game import MathGame
from config import BOT_TOKEN
import asyncio
import os

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# Инициализация базы данных
db = Database('game.db')

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    
    # Регистрация пользователя, если он новый
    if not db.user_exists(user_id):
        db.add_user(user_id, username)
        await message.answer(f"Добро пожаловать в игру! Ваш начальный баланс: 0 монет")
    else:
        balance = db.get_balance(user_id)
        await message.answer(f"С возвращением! Ваш баланс: {balance} монет")

@dp.message_handler(commands=['balance'])
async def balance_handler(message: types.Message):
    user_id = message.from_user.id
    wallet = Wallet(db, user_id)
    balance = wallet.get_balance()
    await message.answer(f"Ваш текущий баланс: {balance} монет")

@dp.message_handler(commands=['play'])
async def play_handler(message: types.Message):
    user_id = message.from_user.id
    game = MathGame()
    problem, correct_answer = game.generate_problem()
    
    # Сохраняем правильный ответ в базе данных или временном хранилище
    # Здесь нужно будет добавить логику для хранения ответа
    
    await message.answer(f"Решите пример: {problem}")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)