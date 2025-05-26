class Wallet:
    def __init__(self, database, user_id):
        self.db = database
        self.user_id = user_id
    
    def get_balance(self):
        return self.db.get_balance(self.user_id)
    
    def add_coins(self, amount):
        current_balance = self.get_balance()
        new_balance = current_balance + amount
        self.db.update_balance(self.user_id, new_balance)
        return new_balance
    
    def subtract_coins(self, amount):
        current_balance = self.get_balance()
        if current_balance >= amount:
            new_balance = current_balance - amount
            self.db.update_balance(self.user_id, new_balance)
            return True, new_balance
        return False, current_balance