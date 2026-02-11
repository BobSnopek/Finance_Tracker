import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import re
from typing import Optional

class InputCleaner:
    """Utility to scrub user input and return clean numbers."""
    @staticmethod
    def clean_to_float(user_input: str) -> float:
        if not user_input.strip():
            return 0.0
        sanitized = user_input.replace(',', '.')
        parts = sanitized.split('.')
        if len(parts) > 2:
            sanitized = parts[0] + '.' + ''.join(parts[1:])
        sanitized = re.sub(r'[^0-9.]', '', sanitized)
        try:
            val = float(sanitized)
            return max(0.0, val)
        except ValueError:
            return 0.0

class FinanceDatabase:
    """Handles SQLite persistence with named columns."""
    def __init__(self, db_name: str = "finance_tracker.db"):
        self.conn = sqlite3.connect(db_name)
        self.conn.row_factory = sqlite3.Row  # Access by column name
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
                    inflation REAL,
                    exchange_rate REAL
                )
            """)

    def save_profile(self, data: dict):
        with self.conn:
            # Upsert logic: always update record #1
            self.conn.execute("""
                INSERT OR REPLACE INTO profile (id, currency, total_debt, monthly_income, monthly_expenses, annual_yield, inflation, exchange_rate)
                VALUES (1, :currency, :debt, :income, :expenses, :yield, :inflation, :rate)
            """, data)

    def get_profile(self) -> Optional[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM profile WHERE id = 1")
        row = cursor.fetchone()
        return dict(row) if row else None

    def close(self):
        self.conn.close()

class InvestmentEngine:
    def __init__(self, nominal_yield: float, inflation: float):
        # Calculate the "Real" rate of return (Fisher Equation approximation)
        self.real_annual_yield = nominal_yield - inflation
        self.monthly_yield = self.real_annual_yield / 12

    def calculate_projection(self, initial_debt: float, monthly_surplus: float, years: int = 10) -> pd.DataFrame:
        data = []
        current_balance = -initial_debt  # Debt is negative net worth
        
        for month in range(0, (years * 12) + 1):
            data.append({
                "Month": month,
                "Year": month / 12,
                "NetWorth": round(current_balance, 2),
                "Status": "Debt" if current_balance < 0 else "Investing"
            })
            
            # Update for next month
            # While in debt, we assume 0% interest on debt for simplicity 
            # (or that surplus is just applied to principal).
            # Once positive, we apply the monthly yield.
            if current_balance < 0:
                current_balance += monthly_surplus
            else:
                current_balance = (current_balance * (1 + self.monthly_yield)) + monthly_surplus
                
        return pd.DataFrame(data)

class FinanceApp:
    def __init__(self):
        self.db = FinanceDatabase()
        self.cleaner = InputCleaner()
        self.profile = self.db.get_profile()

    def setup_profile(self):
        print("\n--- Configuration (Press Enter for Defaults) ---")
        
        curr = input("Preferred Currency (EUR/CZK) [Default: CZK]: ").upper() or "CZK"
        rate = self.cleaner.clean_to_float(input("CZK/EUR Rate [Default: 25]: ") or "25")
        debt = self.cleaner.clean_to_float(input("Current Total Debt: ") or "0")
        
        # Yield Logic
        raw_yield = input("Expected Annual Return % (e.g. 7) [Default: 5%]: ")
        y_val = self.cleaner.clean_to_float(raw_yield) / 100 if raw_yield else 0.05
        
        # Inflation Logic
        raw_inf = input("Expected Annual Inflation % (e.g. 3) [Default: 4.5%]: ")
        inf_val = self.cleaner.clean_to_float(raw_inf) / 100 if raw_inf else 0.045
        
        income = self.cleaner.clean_to_float(input("Monthly Net Income: "))
        expenses = self.cleaner.clean_to_float(input("Monthly Expenses: "))
        
        profile_data = {
            "currency": curr, "debt": debt, "income": income, 
            "expenses": expenses, "yield": y_val, "inflation": inf_val, "rate": rate
        }
        
        self.db.save_profile(profile_data)
        self.profile = self.db.get_profile()
        print(f"✅ Profile updated! Real return: {(y_val - inf_val)*100:.1f}%")

    def run_report(self):
        if not self.profile:
            print("❌ Please setup profile first.")
            return
        
        p = self.profile
        surplus = p['monthly_income'] - p['monthly_expenses']
        
        if surplus <= 0:
            print(f"⚠️ Warning: No surplus (Income: {p['monthly_income']} - Expenses: {p['monthly_expenses']})")
            return

        engine = InvestmentEngine(p['annual_yield'], p['inflation'])
        df = engine.calculate_projection(p['total_debt'], surplus)
        
        # Visualization
        plt.figure(figsize=(12, 6))
        
        # Split data for coloring
        debt_df = df[df['Status'] == "Debt"]
        inv_df = df[df['Status'] == "Investing"]

        if not debt_df.empty:
            plt.plot(debt_df['Year'], debt_df['NetWorth'], color='#e74c3c', label='Debt Repayment', linewidth=3)
        if not inv_df.empty:
            # Connect the last debt point to the first investment point
            plot_df = df[df['NetWorth'] >= -surplus] 
            plt.plot(plot_df['Year'], plot_df['NetWorth'], color='#2ecc71', label='Wealth Building', linewidth=3)

        plt.axhline(0, color='black', linestyle='--', alpha=0.3)
        plt.title(f"10-Year Financial Path ({p['currency']})\nNominal: {p['annual_yield']*100}% | Inflation: {p['inflation']*100}%", fontsize=14)
        plt.xlabel("Years")
        plt.ylabel(f"Net Worth ({p['currency']})")
        plt.legend()
        plt.grid(True, alpha=0.2)
        
        # Formatting y-axis
        plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}'))
        
        final_val = df['NetWorth'].iloc[-1]
        plt.annotate(f'Final: {final_val:,.0f}', xy=(10, final_val), xytext=(8.5, final_val*0.8),
                     arrowprops=dict(facecolor='black', shrink=0.05))
        
        plt.tight_layout()
        plt.show()

        print(f"\n📊 Report for the next 10 years:")
        print(f"Monthly Surplus: {surplus:,.2f} {p['currency']}")
        if p['total_debt'] > 0:
            months = p['total_debt'] / surplus
            print(f"Debt-Free In: {months:.1f} months ({months/12:.1f} years)")
        print(f"Projected Net Worth (Inflation Adjusted): {final_val:,.2f} {p['currency']}")

    def cleanup(self):
        self.db.close()

if __name__ == "__main__":
    app = FinanceApp()
    try:
        while True:
            print("\n" + "="*40)
            print("  PERSONAL FINANCE TRACKER (v2.0)")
            print("="*40)
            print("1. Setup Profile\n2. View Report\n3. Exit")
            choice = input("> ").strip()
            
            if choice == '1': app.setup_profile()
            elif choice == '2': app.run_report()
            elif choice == '3': break
            else: print("Invalid choice.")
    finally:
        app.cleanup()
