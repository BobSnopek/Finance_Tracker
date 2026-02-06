import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import re
from typing import Optional
from datetime import datetime

class InputCleaner:
    """Utility to scrub user input and return clean numbers."""
    
    @staticmethod
    def clean_to_float(user_input: str) -> float:
        """Removes all non-numeric characters except the first decimal point."""
        # Replace comma with dot for decimal consistency
        sanitized = user_input.replace(',', '.')
        # Remove everything except digits and the dot
        sanitized = re.sub(r'[^0-9.]', '', sanitized)
        
        try:
            val = float(sanitized)
            # Logic for yields: If user enters "9", they likely mean 0.09
            # We will handle this specific logic in the setup_profile method
            return val
        except ValueError:
            return 0.0

class FinanceDatabase:
    """Handles SQLite persistence."""
    def __init__(self, db_name: str = "finance_tracker.db"):
        self.conn = sqlite3.connect(db_name)
        self._create_tables()

    def _create_tables(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS profile (
                    id INTEGER PRIMARY KEY,
                    currency TEXT,
                    total_debt REAL,
                    monthly_income REAL,
                    monthly_expenses REAL,
                    annual_yield REAL,
                    exchange_rate REAL
                )
            """)

    def save_profile(self, data: dict):
        with self.conn:
            self.conn.execute("DELETE FROM profile")
            self.conn.execute("""
                INSERT INTO profile (currency, total_debt, monthly_income, monthly_expenses, annual_yield, exchange_rate)
                VALUES (:currency, :debt, :income, :expenses, :yield, :rate)
            """, data)

    def get_profile(self) -> Optional[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM profile LIMIT 1")
        row = cursor.fetchone()
        if row:
            return {
                "currency": row[1], "debt": row[2], "income": row[3], 
                "expenses": row[4], "yield": row[5], "rate": row[6]
            }
        return None

class InvestmentEngine:
    def __init__(self, yield_rate: float):
        self.monthly_yield = yield_rate / 12

    def calculate_projection(self, monthly_cont: float, years: int = 10) -> pd.DataFrame:
        data = []
        current_balance = 0
        for month in range(1, (years * 12) + 1):
            current_balance = (current_balance * (1 + self.monthly_yield)) + monthly_cont
            data.append({"Month": month, "NetWorth": round(current_balance, 2)})
        return pd.DataFrame(data)

class FinanceApp:
    def __init__(self):
        self.db = FinanceDatabase()
        self.cleaner = InputCleaner()
        self.profile = self.db.get_profile()

    def setup_profile(self):
        print("\n--- Configuration (Press Enter for Defaults) ---")
        
        # 1. Currency
        curr = input("Preferred Currency (EUR/CZK) [Default: CZK]: ").upper() or "CZK"
        
        # 2. Exchange Rate
        raw_rate = input("CZK/EUR Exchange Rate [Default: 25]: ")
        rate = self.cleaner.clean_to_float(raw_rate) if raw_rate else 25.0
        
        # 3. Debt
        default_debt = 250000 if curr == "CZK" else 10000
        raw_debt = input(f"Total Debt Amount [Default: {default_debt}]: ")
        debt = self.cleaner.clean_to_float(raw_debt) if raw_debt else float(default_debt)
        
        # 4. Annual Yield
        raw_yield = input("Annual Interest Rate % (e.g., 9 or 0.05) [Default: 5%]: ")
        if not raw_yield:
            y_val = 0.05
        else:
            y_val = self.cleaner.clean_to_float(raw_yield)
            # If user entered "9", convert to 0.09. If "0.09", keep as is.
            if y_val >= 1:
                y_val = y_val / 100

        # 5. Income/Expenses
        income = self.cleaner.clean_to_float(input("Monthly Net Income: "))
        expenses = self.cleaner.clean_to_float(input("Monthly Expenses: "))

        profile_data = {
            "currency": curr, "debt": debt, "income": income, 
            "expenses": expenses, "yield": y_val, "rate": rate
        }
        
        self.db.save_profile(profile_data)
        self.profile = self.db.get_profile()
        print(f"✅ Profile updated! Yield set to {y_val*100:.1f}%.")

    def run_report(self):
        if not self.profile:
            print("Please setup profile first.")
            return
        
        p = self.profile
        surplus = p['income'] - p['expenses']
        
        print(f"\n--- Strategy for {p['currency']} ---")
        if p['debt'] > 0:
            months = int(p['debt'] / surplus) if surplus > 0 else "Infinity"
            print(f"Repaying {p['debt']} debt first. Time: {months} months.")
        
        engine = InvestmentEngine(p['yield'])
        df = engine.calculate_projection(surplus)
        
        plt.plot(df['Month'], df['NetWorth'])
        plt.title(f"10-Year Growth at {p['yield']*100}% p.a.")
        plt.show()

if __name__ == "__main__":
    app = FinanceApp()
    # Simplified menu for this example
    print("1. Setup | 2. Report")
    choice = input("> ")
    if choice == '1': app.setup_profile()
    else: app.run_report()
