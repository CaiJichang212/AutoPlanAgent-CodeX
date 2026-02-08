
from sqlalchemy import create_engine, text
import pandas as pd

engine = create_engine("mysql+pymysql://root:shsh123@localhost:3306/test_trae")
with engine.connect() as conn:
    print("--- pv_financials periods ---")
    df = pd.read_sql(text("SELECT DISTINCT report_period FROM pv_financials"), conn)
    print(df)
    
    print("\n--- test_em_yjbb report_date format ---")
    df = pd.read_sql(text("SELECT report_date FROM test_em_yjbb LIMIT 5"), conn)
    print(df)
