import random

class MathGame:
    def __init__(self):
        self.operators = ['+', '-', '*']
        self.max_number = 10
        self.reward = 5  # награда за правильный ответ
    
    def generate_problem(self):
        num1 = random.randint(1, self.max_number)
        num2 = random.randint(1, self.max_number)
        operator = random.choice(self.operators)
        
        problem = f"{num1} {operator} {num2}"
        
        if operator == '+':
            answer = num1 + num2
        elif operator == '-':
            answer = num1 - num2
        else:  # operator == '*'
            answer = num1 * num2
        
        return problem, answer
    
    def check_answer(self, user_answer, correct_answer):
        try:
            return int(user_answer) == correct_answer
        except ValueError:
            return False