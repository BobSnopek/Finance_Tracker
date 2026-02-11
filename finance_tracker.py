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
        sanitized = user_input.replace(',', '.')
        # Keep only first decimal point
        parts = sanitized.split('.')
        if len(parts) > 2:
            sanitized = parts[0] + '.' + ''.join(parts[1:])
        
        sanitized = re.sub(r'[^0-9.]', '', sanitized)
        
        try:
            val = float(sanitized)
            return max(0.0, val)  # Prevent negative values
        except ValueError:
            return 0.0

class FinanceDatabase:
    """Handles SQLite persistence."""
    def __init__(self, db_name: str = "finance_tracker.db"):
        try:
            self.conn = sqlite3.connect(db_name)
            self._create_tables()
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            raise

    def _create_tables(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS profile (
                    id INTEGER PRIMARY KEY,
                    currency TEXT NOT NULL,
                    total_debt REAL NOT NULL DEFAULT 0,
                    monthly_income REAL NOT NULL DEFAULT 0,
                    monthly_expenses REAL NOT NULL DEFAULT 0,
                    annual_yield REAL NOT NULL DEFAULT 0.05,
                    exchange_rate REAL NOT NULL DEFAULT 25.0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def save_profile(self, data: dict):
        try:
            with self.conn:
                self.conn.execute("DELETE FROM profile")
                self.conn.execute("""
                    INSERT INTO profile (currency, total_debt, monthly_income, monthly_expenses, annual_yield, exchange_rate)
                    VALUES (:currency, :debt, :income, :expenses, :yield, :rate)
                """, data)
        except sqlite3.Error as e:
            print(f"Error saving profile: {e}")
            raise

    def get_profile(self) -> Optional[dict]:
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM profile LIMIT 1")
            row = cursor.fetchone()
            if row:
                return {
                    "currency": row[1], "debt": row[2], "income": row[3], 
                    "expenses": row[4], "yield": row[5], "rate": row[6]
                }
            return None
        except sqlite3.Error as e:
            print(f"Error retrieving profile: {e}")
            return None
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

class InvestmentEngine:
    def __init__(self, yield_rate: float):
        self.annual_yield = yield_rate
        self.monthly_yield = yield_rate / 12

    def calculate_projection(self, monthly_cont: float, years: int = 10) -> pd.DataFrame:
        data = []
        current_balance = 0
        for month in range(1, (years * 12) + 1):
            current_balance = (current_balance * (1 + self.monthly_yield)) + monthly_cont
            data.append({
                "Month": month, 
                "Year": month / 12,
                "NetWorth": round(current_balance, 2)
            })
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
        if curr not in ["EUR", "CZK"]:
            print(f"Warning: Unknown currency '{curr}', using CZK")
            curr = "CZK"
        
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
            if y_val >= 1:
                y_val = y_val / 100
            if y_val > 1:  # Still too high after conversion
                print(f"Warning: {y_val*100}% seems unusually high")

        # 5. Income/Expenses
        income = self.cleaner.clean_to_float(input("Monthly Net Income: "))
        expenses = self.cleaner.clean_to_float(input("Monthly Expenses: "))
        
        if expenses > income:
            print("⚠️  Warning: Expenses exceed income!")

        profile_data = {
            "currency": curr, "debt": debt, "income": income, 
            "expenses": expenses, "yield": y_val, "rate": rate
        }
        
        self.db.save_profile(profile_data)
        self.profile = self.db.get_profile()
        print(f"✅ Profile updated! Yield set to {y_val*100:.1f}%.")

    def run_report(self):
        if not self.profile:
            print("❌ Please setup profile first.")
            return
        
        p = self.profile
        surplus = p['income'] - p['expenses']
        
        print(f"\n--- Financial Strategy Report ({p['currency']}) ---")
        print(f"Monthly Surplus: {surplus:,.2f} {p['currency']}")
        
        if p['debt'] > 0:
            if surplus > 0:
                months_to_payoff = p['debt'] / surplus
                years_to_payoff = months_to_payoff / 12
                print(f"Debt Repayment: {p['debt']:,.2f} {p['currency']}")
                print(f"Time to Pay Off: {months_to_payoff:.1f} months ({years_to_payoff:.1f} years)")
            else:
                print(f"⚠️  Cannot repay debt of {p['debt']:,.2f} with no surplus!")
                return
        
        if surplus <= 0:
            print("⚠️  No surplus available for investment projections.")
            return
        
        engine = InvestmentEngine(p['yield'])
        df = engine.calculate_projection(surplus)
        
        # Enhanced plotting
        plt.figure(figsize=(10, 6))
        plt.plot(df['Year'], df['NetWorth'], linewidth=2)
        plt.title(f"10-Year Investment Growth at {p['yield']*100:.1f}% Annual Return", fontsize=14)
        plt.xlabel("Years", fontsize=12)
        plt.ylabel(f"Net Worth ({p['currency']})", fontsize=12)
        plt.grid(True, alpha=0.3)
        
        # Format y-axis as currency
        ax = plt.gca()
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}'))
        
        # Add final value annotation
        final_value = df['NetWorth'].iloc[-1]
        plt.annotate(f'Final: {final_value:,.0f}', 
                    xy=(10, final_value), 
                    xytext=(8, final_value * 0.9),
                    arrowprops=dict(arrowstyle='->', color='red'))
        
        plt.tight_layout()
        plt.show()
        
        print(f"\n📊 Projected net worth after 10 years: {final_value:,.2f} {p['currency']}")
    
    def cleanup(self):
        """Clean up resources."""
        self.db.close()

if __name__ == "__main__":
    app = FinanceApp()
    try:
        print("=" * 50)
        print("  Personal Finance Tracker")
        print("=" * 50)
        print("\n1. Setup Profile | 2. View Report | 3. Exit")
        choice = input("> ").strip()
        
        if choice == '1': 
            app.setup_profile()
        elif choice == '2': 
            app.run_report()
        elif choice == '3':
            print("Goodbye!")
        else:
            print("Invalid choice")
    finally:
        app.cleanup()
