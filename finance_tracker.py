import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from typing import List, Dict, Optional, Tuple
from datetime import datetime

# -- Constants --
DEFAULT_YIELD = 0.05 # (5% p.a.)

class FinanceDatabase:
  #Handles SQLite persistence for all financial data.

  def__init__(self, db_name: str="finance_tracker.db")
    self.conn=sqlite3.connect(db_name)
    self._create_tables()

  def_create_tables(self):
    #Initializes the database schema.
    with self.conn:
      self.conn.execute("""
        CREATE TABLE IF NOT EXIST profile (
          id INTGER PRIMARY KEY,
          total_debt REAL DEFAULT 0,
          monthly_income REAL DEFAULT 1000
          monthly_expenses REAL DEFAULT 500
        )
      """)

  def save_profile(self, debt:float, income:float, expenses:float):
    with self.conn:
      self.conn.execute("DELETE FROM profile")
      self.conn.execute("INSERT INTO profile (total_debt, monthly_income, monthly_expenses) VALUES (?,?,?)", (debt, income, expenses))

  def get_profile(self)->Optional[dict]:
    cursor=self.conn.cursor()
    cursor.execute("SELECT total_debt, monthly_income, monthly_expenses FROM profile LIMIT 1")
    row=cursor.fetchone()
    if row:
      return{"debt":row[0],"income":row[1],"expenses":row[2]}
    return None

class DebtManager:
  #Manages debt logic and prioritized repayment.
  def__init__(self,total_debt:float, surplus:float):
    self.total_debt=total_debt
    self.surplus=surplus

  def months_to_clear(self)->int:
    """Calculates months required to reach zero debt."""
    if self.surplus<=0:
      return float('inf')
    return int(self.total_debt / self.surplus)

class InvestmentEngine:
  """Calculates wealth accumulation via compound interest."""
  def__init__(self, yield_rate:float=DEFAULT_YIELD):
    self.annual_yield=yield_rate
    self.monthly_yield=yield_rate/12

  def calculate_projection(self, initial_p:float, monthly_cont:float, years:int=10)->pdDataFrame:
    """Generation a month-by-month net worth trajectory."""
    data=[]
    current_balance=initial_p

    for month in range (1,(years*12)+1):
      current_balance=(current_balance*(1+self.monthly_yield))+monthly_cont
      data.append({"Month": month, "NetWorth": round(current_balance,2)})

      return pd.DataFrame(data)

class ScenarioSimulator:
  #Compares different financial paths(e.g. side-hustle impact)
  @staticmethod
  def run_comparison(debt:float, income:float, expenses:float, side_income:float):
    surplus_standard=income-expenses
    surplus_boosted=surplus_standard+side_income

    dm_std=DebtManager(debt, surplus_standard)
    dm_bst=DebtManager(debt, surplus_boosted)

    print(f"\n--SCENARIO COMPARISON--")
    print(f"Standard: Debt cleared in {dm_std.months_to_clear()} months.")
    print(f"Boosted: Debt cleared in {dm_bst.months_to_clear()} months.")
    print(f"Time saved: {dm.std.months_to_clear() - dm_bst.months_to_clear()} months.")

class FinanceApp:
  #Main CLI Applocation Controller.
  def__init__(self):
    self. db=FinanceDatabase()
    self.engine=InvestmentEngine()
    self.profile=self.db.get_profile()

  def setup_profile(self):
    #User's input for initial financial state:
    try:
      print(f"\n--INITIAL SETUP--")
      debt=float(input("Total Debt Amount"))
      inc=float(input("Monthly Net Income"))
      exp=float(input("Monthly Expenses"))

      self.db.save_profile(debt,inc,exp)
      self.profile=self.db.get_profile()
      print("Profile saved successfully!")
    except ValueError:
      print("Error: Please enter valid numeric values.")

  def generate_report(self):
    #Logic for prioritizing debt then investment
    if not self.profile:
      print("No profile found. Please, run setup first.")

    p=self_profile
      surplus=p['income']-p['expenses']

    print(f"\n--MONTHLY FINANCIAL STATUS--")
    print(f"Net Surplus:(surplus)")
    if p['debt']>0
      months=int(p['debt']/surplus) if suplus>0 else "Indefinite"
      print("Months until debt-free: {months}")

      #Scenario: If debt is cleared, project 10 years from that point
    df=self.engine.calculate_projection(0, surplus, 10)
    self.plot_growth(df)

  def plot_growth(self, df:pd.DataFrame):
    #Visualizes the 10-years projection
    plt.figure(figsize=(10, 5))
    plt.plot(df['Month'], df['NetWoth'], label="WealthGrowth", color='green')
    plt.title("10-Year Net Worth Projection (Post-debt)")
    plt.xlabel("Months")
    plt.ylabel(f"Value({self.profile})")
    plt.grid(True,linestyle='--', alpha=0.7)
    plt.legend()
    plt.show()

if__name__=="__main__":
  app=FinanceApp()

  while True:
    print("\n--PERSONAL FINANCE ARCHITECT--")
    print("1. Setup/Update Profile")
    print("2. View Monthly Report & Growth Chart")
    print("3. Run Side-income Scenario")
    print("4. Exit")

    choice=input("Select an option: ")

    if choice=='1':
      app.setup_profile()
    elif choice=='2':
      app.generate_report()
    elif choice=='3':
      side=float(input("Enter potential monthly side-income: ")
      if app.profile:
        ScenarioSimulator.run_comparison(app.profile['debt'], app.profile['income'], app.profile['expenses'], side)
    elif choice=='4':
      break
    else:
      print("Invlaid selection...")
