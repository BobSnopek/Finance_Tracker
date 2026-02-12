import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import re
from typing import Optional

class InputCleaner:
    """Utility to scrub user input and return clean numbers."""
    @staticmethod
    def clean_to_float(user_input: str) -> float:
        if not user_input or not user_input.strip():
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
    
    @staticmethod
    def parse_percentage(user_input: str) -> float:
        """Parse percentage input, handling both '5' and '0.05' formats."""
        if not user_input.strip():
            return 0.0
        val = InputCleaner.clean_to_float(user_input)
        return val / 100 if val >= 1 else val

class FinanceDatabase:
    def __init__(self, db_name: str = "finance_tracker.db"):
        try:
            self.conn = sqlite3.connect(db_name)
            self.conn.row_factory = sqlite3.Row
            self._create_tables()
        except sqlite3.Error as e:
            print(f"❌ Database initialization error: {e}")
            raise

    def _create_tables(self):
        try:
            with self.conn:
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS profile (
                        id INTEGER PRIMARY KEY,
                        currency TEXT NOT NULL,
                        total_debt REAL NOT NULL DEFAULT 0,
                        debt_interest REAL NOT NULL DEFAULT 0,
                        monthly_income REAL NOT NULL DEFAULT 0,
                        monthly_expenses REAL NOT NULL DEFAULT 0,
                        annual_yield REAL NOT NULL DEFAULT 0.05,
                        inflation REAL NOT NULL DEFAULT 0.045,
                        exchange_rate REAL NOT NULL DEFAULT 25.0,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
        except sqlite3.Error as e:
            print(f"❌ Table creation error: {e}")
            raise

    def save_profile(self, data: dict):
        try:
            with self.conn:
                self.conn.execute("""
                    INSERT OR REPLACE INTO profile 
                    (id, currency, total_debt, debt_interest, monthly_income, 
                     monthly_expenses, annual_yield, inflation, exchange_rate, updated_at)
                    VALUES (1, :currency, :debt, :debt_interest, :income, 
                            :expenses, :yield, :inflation, :rate, CURRENT_TIMESTAMP)
                """, data)
        except sqlite3.Error as e:
            print(f"❌ Profile save error: {e}")
            raise

    def get_profile(self) -> Optional[dict]:
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM profile WHERE id = 1")
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            print(f"❌ Profile retrieval error: {e}")
            return None

    def close(self):
        if self.conn: 
            self.conn.close()

class InvestmentEngine:
    def __init__(self, nominal_yield: float, inflation: float, debt_interest: float):
        self.real_annual_yield = nominal_yield - inflation
        self.monthly_yield = self.real_annual_yield / 12
        self.monthly_debt_interest = debt_interest / 12

    def calculate_projection(self, initial_debt: float, monthly_surplus: float, years: int = 10) -> pd.DataFrame:
        data = []
        current_balance = -initial_debt  # Debt is negative
        total_interest_paid = 0.0
        
        # Month 0: Starting state
        data.append({
            "Month": 0, 
            "Year": 0.0, 
            "NetWorth": round(current_balance, 2),
            "Status": "Debt" if current_balance < 0 else "Investing", 
            "InterestPaid": 0.0
        })

        for month in range(1, (years * 12) + 1):
            if current_balance < 0:
                # FIXED: Interest on debt should make it MORE negative
                interest_charge = abs(current_balance) * self.monthly_debt_interest
                total_interest_paid += interest_charge
                # Debt grows by interest, then reduced by surplus payment
                current_balance = current_balance - interest_charge + monthly_surplus
            else:
                # Investing: balance grows with returns
                current_balance = (current_balance * (1 + self.monthly_yield)) + monthly_surplus
                
            data.append({
                "Month": month,
                "Year": round(month / 12, 2),
                "NetWorth": round(current_balance, 2),
                "Status": "Debt" if current_balance < 0 else "Investing",
                "InterestPaid": round(total_interest_paid, 2)
            })
                
        return pd.DataFrame(data)

class FinanceApp:
    def __init__(self):
        self.db = FinanceDatabase()
        self.cleaner = InputCleaner()
        self.profile = self.db.get_profile()

    def _get_validated_input(self, prompt: str, default: str = "0", allow_zero: bool = True) -> float:
        """Helper to ensure we get a valid number."""
        while True:
            val = input(prompt) or default
            cleaned = self.cleaner.clean_to_float(val)
            if cleaned > 0 or (allow_zero and cleaned == 0): 
                return cleaned
            print("❌ Please enter a positive number.")

    def setup_profile(self):
        print("\n" + "="*50 + "\n  PROFILE SETUP\n" + "="*50)
        print("(Press Enter for default values)\n")
        
        # Currency with validation
        while True:
            curr = (input("💱 Currency (EUR/CZK) [Default: CZK]: ").upper() or "CZK")
            if curr in ["EUR", "CZK"]:
                break
            print("❌ Please enter EUR or CZK")
        
        rate = self._get_validated_input("💱 CZK/EUR Exchange Rate [Default: 25]: ", "25")
        debt = self._get_validated_input(f"💳 Total Debt ({curr}) [Default: 0]: ", "0")
        
        debt_int = 0.0
        if debt > 0:
            raw_di = input("💳 Annual Debt Interest % (e.g., 5) [Default: 0%]: ")
            debt_int = self.cleaner.parse_percentage(raw_di) if raw_di else 0.0
            # Sanity check
            if debt_int > 0.30:  # 30% seems excessive
                confirm = input(f"⚠️  {debt_int*100:.1f}% seems high. Continue? (y/n): ")
                if confirm.lower() != 'y':
                    debt_int = 0.05  # Reset to 5%

        raw_y = input("📈 Expected Annual Return % (e.g., 7) [Default: 5%]: ")
        y_val = self.cleaner.parse_percentage(raw_y) if raw_y else 0.05
        
        raw_inf = input("📉 Expected Annual Inflation % (e.g., 3) [Default: 4.5%]: ")
        inf_val = self.cleaner.parse_percentage(raw_inf) if raw_inf else 0.045
        
        # Warn about unrealistic values
        if y_val > 0.20:  # 20%+ returns
            print(f"⚠️  {y_val*100:.1f}% annual return is very optimistic")
        if inf_val > 0.15:  # 15%+ inflation
            print(f"⚠️  {inf_val*100:.1f}% inflation is quite high")
        
        income = self._get_validated_input(f"💰 Monthly Net Income ({curr}): ", "0", allow_zero=False)
        expenses = self._get_validated_input(f"💸 Monthly Expenses ({curr}): ", "0")
        
        surplus = income - expenses
        if surplus <= 0:
            print(f"⚠️  Warning: No surplus! (Income: {income:,.2f}, Expenses: {expenses:,.2f})")
            print("    You won't be able to pay off debt or invest.")
        
        # Warn if debt interest exceeds investment returns
        if debt > 0 and debt_int > 0 and debt_int > y_val:
            print(f"⚠️  Debt interest ({debt_int*100:.1f}%) exceeds investment return ({y_val*100:.1f}%)")
            print("    Prioritizing debt payoff is strongly recommended!")

        profile_data = {
            "currency": curr, "debt": debt, "debt_interest": debt_int,
            "income": income, "expenses": expenses, "yield": y_val, 
            "inflation": inf_val, "rate": rate
        }
        
        self.db.save_profile(profile_data)
        self.profile = self.db.get_profile()
        
        real_return = (y_val - inf_val) * 100
        print(f"\n✅ Profile saved successfully!")
        print(f"   Real investment return: {real_return:.2f}%")
        if debt > 0 and debt_int > 0:
            print(f"   Effective debt cost: {debt_int*100:.2f}%")

    def run_report(self):
        if not self.profile:
            print("❌ No profile found. Please setup profile first.")
            return
        
        p = self.profile
        surplus = p['monthly_income'] - p['monthly_expenses']
        
        if surplus <= 0:
            print(f"⚠️  No surplus available for projection.")
            print(f"    Income: {p['monthly_income']:,.2f} {p['currency']}")
            print(f"    Expenses: {p['monthly_expenses']:,.2f} {p['currency']}")
            return

        engine = InvestmentEngine(p['annual_yield'], p['inflation'], p.get('debt_interest', 0))
        df = engine.calculate_projection(p['total_debt'], surplus)
        
        # IMPROVED PLOTTING: Split into debt and investment segments
        plt.figure(figsize=(12, 7))
        
        # Find transition point from debt to investing
        debt_data = df[df['NetWorth'] < 0]
        invest_data = df[df['NetWorth'] >= 0]
        
        # Plot debt phase
        if not debt_data.empty:
            plt.plot(debt_data['Year'], debt_data['NetWorth'], 
                    color='#e74c3c', linewidth=2.5, label='Debt Phase')
        
        # Plot investment phase
        if not invest_data.empty:
            plt.plot(invest_data['Year'], invest_data['NetWorth'], 
                    color='#2ecc71', linewidth=2.5, label='Investing Phase')
        
        # Mark transition point
        if not debt_data.empty and not invest_data.empty:
            transition_month = invest_data.iloc[0]['Month']
            transition_year = invest_data.iloc[0]['Year']
            plt.axvline(transition_year, color='gold', linestyle=':', 
                       linewidth=2, alpha=0.7, 
                       label=f'Debt-Free (Month {transition_month})')

        plt.axhline(0, color='black', linestyle='--', alpha=0.4, linewidth=1)
        plt.grid(True, alpha=0.2)
        
        # Title
        title_parts = [
            f"10-Year Financial Projection ({p['currency']})",
            f"Investment: {p['annual_yield']*100:.1f}% | Inflation: {p['inflation']*100:.1f}%"
        ]
        if p.get('debt_interest', 0) > 0:
            title_parts.append(f"Debt Interest: {p['debt_interest']*100:.1f}%")
        
        plt.title('\n'.join(title_parts), fontsize=12, pad=15)
        plt.ylabel(f"Net Worth ({p['currency']})", fontsize=11)
        plt.xlabel("Years", fontsize=11)
        plt.legend(loc='best', fontsize=10)
        
        # Format y-axis with commas
        ax = plt.gca()
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, pos: f'{x:,.0f}'))
        
        # Annotation for final value
        final_val = df['NetWorth'].iloc[-1]
        y_offset = final_val * 0.15 if final_val > 0 else final_val * -0.15
        plt.annotate(f'Final: {final_val:,.0f}', 
                    xy=(10, final_val), 
                    xytext=(8.3, final_val - y_offset),
                    bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.4),
                    arrowprops=dict(arrowstyle='->', lw=1.5, color='black'),
                    fontsize=10)
        
        plt.tight_layout()
        plt.show()

        # Print summary
        print(f"\n📊 10-Year Projection Summary:")
        print(f"   Monthly Surplus: {surplus:,.2f} {p['currency']}")
        
        if p['total_debt'] > 0:
            total_interest = df['InterestPaid'].iloc[-1]
            debt_free_data = df[df['NetWorth'] >= 0]
            
            if not debt_free_data.empty:
                debt_free_month = debt_free_data.iloc[0]['Month']
                print(f"   Time to Debt-Free: {debt_free_month} months ({debt_free_month/12:.1f} years)")
                print(f"   Total Interest Paid: {total_interest:,.2f} {p['currency']}")
            else:
                remaining_debt = abs(df['NetWorth'].iloc[-1])
                print(f"   ⚠️  Still in debt after 10 years!")
                print(f"   Remaining Debt: {remaining_debt:,.2f} {p['currency']}")
                print(f"   Interest Paid So Far: {total_interest:,.2f} {p['currency']}")
        
        real_return_pct = (p['annual_yield'] - p['inflation']) * 100
        print(f"   Real Return Rate: {real_return_pct:.2f}%")
        print(f"   Final Net Worth: {final_val:,.2f} {p['currency']}")

    def cleanup(self):
        self.db.close()

if __name__ == "__main__":
    app = FinanceApp()
    try:
        while True:
            print("\n" + "="*50)
            print("  PERSONAL FINANCE TRACKER v2.2")
            print("="*50)
            choice = input("1. Setup Profile | 2. View Report | 3. Exit\n> ").strip()
            
            if choice == '1': 
                app.setup_profile()
            elif choice == '2': 
                app.run_report()
            elif choice == '3': 
                print("\n👋 Goodbye!")
                break
            else:
                print("❌ Invalid choice. Please enter 1, 2, or 3.")
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted. Exiting...")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        app.cleanup()
        
