import sqlite3

class Database:
    def __init__(self, db_file):
        self.connection = sqlite3.connect(db_file)
        self.cursor = self.connection.cursor()
        self.create_tables()
    
    def create_tables(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance INTEGER DEFAULT 0
        )
        """)
        self.connection.commit()
    
    def user_exists(self, user_id):
        result = self.cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
        return bool(len(result.fetchall()))
    
    def add_user(self, user_id, username):
        self.cursor.execute("INSERT INTO users (user_id, username, balance) VALUES (?, ?, ?)",
                           (user_id, username, 0))
        self.connection.commit()
    
    def get_balance(self, user_id):
        result = self.cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        return result.fetchone()[0]
    
    def update_balance(self, user_id, new_balance):
        self.cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?",
                           (new_balance, user_id))
        self.connection.commit()