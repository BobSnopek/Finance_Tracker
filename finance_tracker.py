import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import re
import os
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

# Optional PDF support
try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False
    print("! fpdf not installed. PDF reports disabled.")
    print("  Install with: pip install fpdf")

# --- Models & Enums ---

class Phase(Enum):
    """Represents the current stage of the financial waterfall."""
    DEBT = "Repaying Creditors" [cite: 1]
    EMERGENCY = "Emergency Fund" [cite: 1]
    INVESTING = "Wealth Building" [cite: 1]

@dataclass
class Creditor:
    """Structure for individual debt records."""
    name: str [cite: 1]
    balance: float [cite: 1]
    interest_rate: float [cite: 1]
    min_payment: float [cite: 1]
    payoff_month: Optional[int] = None [cite: 1]

# --- Utility Classes ---

class InputCleaner:
    """Handles sanitization of messy user inputs."""
    @staticmethod
    def clean_to_float(user_input: str, allow_zero: bool = True) -> float:
        if not user_input or not user_input.strip():
            return 0.0 [cite: 1]
        
        sanitized = user_input.replace(',', '.') [cite: 1]
        parts = sanitized.split('.') [cite: 1]
        if len(parts) > 2:
            sanitized = parts[0] + '.' + "".join(parts[1:]) [cite: 1]
        
        sanitized = re.sub(r'[^0-9.]', '', sanitized) [cite: 1]
        try:
            val = float(sanitized) if sanitized else 0.0 [cite: 1]
            return max(0.0, val) if allow_zero else max(0.01, val) [cite: 1]
        except ValueError:
            return 0.0 [cite: 1]

    @staticmethod
    def parse_percentage(user_input: str) -> float:
        val = InputCleaner.clean_to_float(user_input) [cite: 1]
        if val >= 1: # Convert whole numbers like '9' to 0.09
            val = val / 100 [cite: 1]
        return min(max(val, 0.0), 1.0) [cite: 1]

class FinanceDatabase:
    """Manages SQLite storage for the financial profile and creditors."""
    def __init__(self, db_name: str = "finance_master.db"):
        try:
            self.conn = sqlite3.connect(db_name) [cite: 1]
            self.conn.row_factory = sqlite3.Row [cite: 1]
            self._setup() [cite: 1]
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            raise

    def _setup(self):
        try:
            with self.conn:
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS profile (
                        id INTEGER PRIMARY KEY CHECK (id=1),
                        income REAL, expenses REAL, emergency_months REAL,
                        stock_yield REAL, bond_yield REAL, stock_ratio REAL,
                        inflation REAL, tax_rate REAL, annual_raise REAL, strategy TEXT
                    )
                """) [cite: 1]
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS creditors (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT, balance REAL, interest_rate REAL, min_payment REAL
                    )
                """) [cite: 1]
        except sqlite3.Error as e:
            print(f"Table setup error: {e}")
            raise

        def save_all(self, prof: dict, creditors: List[Creditor]) -> bool:
        try:
            with self.conn:
                self.conn.execute("DELETE FROM profile") [cite: 1]
                self.conn.execute("DELETE FROM creditors") [cite: 1]
                
                # Corrected placeholders to match dictionary keys
                self.conn.execute("""
                    INSERT INTO profile VALUES (1, :income, :expenses, :emergency_months,
                    :stock_yield, :bond_yield, :stock_ratio, :inflation, :tax_rate,
                    :annual_raise, :strategy)
                """, prof) [cite: 1]
                
                for c in creditors:
                    self.conn.execute(
                        "INSERT INTO creditors (name, balance, interest_rate, min_payment) VALUES (?, ?, ?, ?)",
                        (c.name, c.balance, c.interest_rate, c.min_payment)
                    ) [cite: 1]
            return True
        except sqlite3.Error as e:
            print(f"Save error: {e}")
            return False

    def get_data(self) -> Tuple[Optional[dict], List[Creditor]]:
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM profile WHERE id = 1") [cite: 1]
            prof = cursor.fetchone()
            
            cursor.execute("SELECT * FROM creditors ORDER BY interest_rate DESC") [cite: 1]
            debts = [Creditor(r['name'], r['balance'], r['interest_rate'], r['min_payment']) 
                     for r in cursor.fetchall()] [cite: 1]
            
            return (dict(prof) if prof else None, debts) [cite: 1]
        except sqlite3.Error as e:
            print(f"Retrieval error: {e}")
            return (None, []) [cite: 1]

    def close(self):
        if self.conn: 
            self.conn.close() [cite: 1]

class InvestmentEngine:
    """Core projection engine implementing the waterfall strategy."""
    def __init__(self, p: dict):
        self.p = p [cite: 1]

    def run_projection(self, debts: List[Creditor], years: int = 10) -> Tuple[pd.DataFrame, List[Dict]]:
        current_debts = [Creditor(c.name, c.balance, c.interest_rate, c.min_payment) for c in debts] [cite: 1]
        income, expenses = self.p['income'], self.p['expenses'] [cite: 1]
        emergency_fund, investment = 0.0, 0.0 [cite: 1]
        e_target = self.p['emergency_months'] * expenses [cite: 1]
        payoffs = []
        total_interest, total_taxes = 0.0, 0.0 [cite: 1]
        
        weighted_yield = (self.p['stock_ratio'] * self.p['stock_yield']) + \
                         ((1 - self.p['stock_ratio']) * self.p['bond_yield']) [cite: 1]
        
        data = []
        for month in range(0, (years * 12) + 1):
            if month > 0 and month % 12 == 0:
                income *= (1 + self.p['annual_raise']) [cite: 1]
                expenses *= (1 + self.p['inflation']) [cite: 1]
            
            surplus = income - expenses [cite: 1]
            active_debts = [d for d in current_debts if d.balance > 0] [cite: 1]
            total_debt = sum(d.balance for d in active_debts) [cite: 1]
            
            if total_debt > 0: 
                phase = Phase.DEBT [cite: 1]
            elif emergency_fund < e_target: 
                phase = Phase.EMERGENCY [cite: 1]
            else: 
                phase = Phase.INVESTING [cite: 1]
            
            inf_factor = (1 + self.p['inflation']) ** (month / 12) [cite: 1]
            net_worth = investment + emergency_fund - total_debt [cite: 1]
            
            data.append({
                "Month": month, "Year": round(month/12, 2), "NetWorth": round(net_worth, 2),
                "RealNetWorth": round(net_worth / inf_factor, 2), "Phase": phase.value,
                "Income": round(income, 2), "Expenses": round(expenses, 2),
                "TotalDebt": round(total_debt, 2), "Emergency Fund": round(emergency_fund, 2),
                "Investment": round(investment, 2), "Interest Paid": round(total_interest, 2),
                "TaxesPaid": round(total_taxes, 2)
            }) [cite: 1]
            
            if month > 0 and surplus > 0:
                rem_surplus = surplus
                if phase == Phase.DEBT:
                    for d in active_debts:
                        interest = d.balance * (d.interest_rate / 12) [cite: 1]
                        d.balance += interest [cite: 1]
                        total_interest += interest [cite: 1]
                    
                    # Minimum Payments
                    for d in active_debts:
                        payment = min(d.min_payment, d.balance, rem_surplus) [cite: 1]
                        d.balance -= payment [cite: 1]
                        rem_surplus -= payment [cite: 1]
                        if d.balance <= 0.01 and d.payoff_month is None:
                            d.balance, d.payoff_month = 0, month [cite: 1]
                            payoffs.append({"name": d.name, "month": month, "year": round(month/12, 1)}) [cite: 1]
                    
                    # Strategic (Avalanche/Snowball) Extra Payments
                    if rem_surplus > 0:
                        active_debts = [d for d in current_debts if d.balance > 0] [cite: 1]
                        if active_debts:
                            if self.p['strategy'] == 'Avalanche':
                                active_debts.sort(key=lambda x: x.interest_rate, reverse=True) [cite: 1]
                            else:
                                active_debts.sort(key=lambda x: x.balance) [cite: 1]
                            
                            for d in active_debts:
                                if rem_surplus <= 0: break
                                p = min(rem_surplus, d.balance) [cite: 1]
                                d.balance -= p [cite: 1]
                                rem_surplus -= p [cite: 1]
                                if d.balance <= 0.01 and d.payoff_month is None:
                                    d.balance, d.payoff_month = 0, month [cite: 1]
                                    payoffs.append({"name": d.name, "month": month, "year": round(month/12, 1)}) [cite: 1]
                    
                    # Overflow to Emergency Fund if debt cleared in same month
                    if rem_surplus > 0 and emergency_fund < e_target:
                        contribution = min(rem_surplus, e_target - emergency_fund) [cite: 1]
                        emergency_fund += contribution [cite: 1]
                
                elif phase == Phase.EMERGENCY:
                    contribution = min(rem_surplus, e_target - emergency_fund) [cite: 1]
                    emergency_fund += contribution [cite: 1]
                    rem_surplus -= contribution [cite: 1]
                    # If emergency fund is filled, the remaining surplus goes to investing next loop
                
                elif phase == Phase.INVESTING:
                    growth = investment * (weighted_yield / 12) [cite: 1]
                    tax = growth * self.p['tax_rate'] [cite: 1]
                    investment += (growth - tax) + rem_surplus [cite: 1]
                    total_taxes += tax [cite: 1]
                    
        return pd.DataFrame(data), payoffs

        def visualize_report(df: pd.DataFrame, payoffs: List[Dict], folder: str) -> Tuple[str, Any]:
    plt.style.use('dark_background')
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10)) [cite: 1]
    
    # Plot 1: Net Worth
    ax1.plot(df['Year'], df['NetWorth'], color='#2ecc71', label='Nominal Net Worth') [cite: 1]
    ax1.plot(df['Year'], df['RealNetWorth'], color='#3498db', linestyle='--', label="Real Net Worth") [cite: 1]
    
    for phase, color in [(Phase.DEBT.value, '#e74c3c'), (Phase.EMERGENCY.value, '#f39c12'), (Phase.INVESTING.value, '#2ecc71')]:
        p_df = df[df['Phase'] == phase]
        if not p_df.empty: 
            ax1.axvspan(p_df['Year'].min(), p_df['Year'].max(), alpha=0.1, color=color) [cite: 1]
            
    ax1.set_title("10-Year Net Worth Projection", fontweight='bold') [cite: 1]
    ax1.legend() [cite: 1]
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}')) [cite: 1]
    
    # Plot 2: Cash Flow
    ax2.fill_between(df['Year'], 0, df['Expenses'], color='#e74c3c', alpha=0.4, label='Expenses') [cite: 1]
    ax2.fill_between(df['Year'], df['Expenses'], df['Income'], color='#2ecc71', alpha=0.4, label='Surplus') [cite: 1]
    ax2.plot(df['Year'], df['Income'], color='#f39c12', label='Income') [cite: 1]
    ax2.set_title("Income & Expense Growth", fontweight='bold') [cite: 1]
    ax2.legend() [cite: 1]
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}')) [cite: 1]
    
    plt.tight_layout()
    path = os.path.join(folder, "temp_chart.png")
    plt.savefig(path, dpi=300) [cite: 1]
    return path, fig

if FPDF_AVAILABLE:
    class PDFGenerator(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 16)
            self.set_text_color(46, 204, 113)
            self.cell(0, 15, 'FINANCIAL FREEDOM MASTERPLAN', 0, 1, 'C')
            self.ln(5)

        def add_section(self, title, body):
            self.set_font('Arial', 'B', 12)
            self.cell(0, 10, title, 0, 1, 'L')
            self.set_font('Arial', '', 10)
            self.multi_cell(0, 7, body)
            self.ln(5)

class FinanceApp:
    def __init__(self):
        self.db = FinanceDatabase() [cite: 1]
        self.cleaner = InputCleaner() [cite: 1]
        self.profile, self.debts = self.db.get_data() [cite: 1]

    def setup(self):
        print("\n" + "="*60 + "\n SETUP PROFILE\n" + "="*60)
        inc = self.cleaner.clean_to_float(input("Monthly Net Income: "), False) [cite: 1]
        exp = self.cleaner.clean_to_float(input("Monthly Expenses: ")) [cite: 1]
        
        if (inc - exp) <= 0:
            if input("WARNING: No surplus! Continue? (y/n): ").lower() != 'y': 
                return [cite: 1]
        
        raw_num = self.cleaner.clean_to_float(input("Number of creditors (0-20)? ")) [cite: 1]
        num_debts = int(min(20, max(0, raw_num))) [cite: 1]
        
        creditors = []
        for i in range(num_debts):
            print(f"\n Creditor #{i+1}:")
            name = input(" Name: ").strip() or f"Debt {i+1}" [cite: 1]
            bal = self.cleaner.clean_to_float(input(" Balance: ")) [cite: 1]
            rate = self.cleaner.parse_percentage(input(" Interest %: ")) [cite: 1]
            min_p = self.cleaner.clean_to_float(input(" Min Payment: ")) [cite: 1]
            creditors.append(Creditor(name, bal, rate, min_p)) [cite: 1]
            
        strat = "Avalanche" if input("\nStrategy: [A]valanche or [S]nowball? ").upper() == 'A' else "Snowball" [cite: 1]
        s_ratio = self.cleaner.parse_percentage(input("Portfolio % in Stocks (Default 80): ") or "80") [cite: 1]
        
        self.db.save_all({
            "income": inc, "expenses": exp, "emergency_months": 3,
            "stock_yield": 0.10, "bond_yield": 0.04, "stock_ratio": s_ratio,
            "inflation": 0.03, "tax_rate": 0.15, "annual_raise": 0.02, "strategy": strat
        }, creditors) [cite: 1]
        self.profile, self.debts = self.db.get_data() [cite: 1]
        print("\n Profile Saved!")

    def run_full_report(self):
        if not self.profile: 
            return print("Run setup first.") [cite: 1]
        
        folder = "PDF_Reports"
        if not os.path.exists(folder): os.makedirs(folder) [cite: 1]
        
        engine = InvestmentEngine(self.profile) [cite: 1]
        df, payoffs = engine.run_projection(self.debts) [cite: 1]
        chart_path, fig = visualize_report(df, payoffs, folder) [cite: 1]
        
        if FPDF_AVAILABLE:
            pdf = PDFGenerator()
            pdf.add_page()
            pdf.add_section("Summary", f"Strategy: {self.profile['strategy']}\nFinal Net Worth: {df.iloc[-1]['NetWorth']:,.2f}") [cite: 1]
            pdf.image(chart_path, x=10, w=190) [cite: 1]
            pdf.output(os.path.join(folder, f"Report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf")) [cite: 1]
            
        plt.show()

if __name__ == "__main__":
    app = FinanceApp()
    while True:
        choice = input("\n1. Setup | 2. Run Report | 3. Exit\n> ") [cite: 1]
        if choice == '1': app.setup()
        elif choice == '2': app.run_full_report()
        elif choice == '3': break
