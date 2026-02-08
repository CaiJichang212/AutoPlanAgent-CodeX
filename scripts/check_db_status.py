
from sqlalchemy import create_engine, text
from autoplan_agent.config import Settings
import pandas as pd

def check_db():
    settings = Settings()
    engine = create_engine(settings.mysql_dsn())
    with engine.connect() as conn:
        for table in ['pv_financials', 'stock_prices', 'test_em_yjbb', 'test_em_xjll', 'test_em_zcfz']:
            count = conn.execute(text(f'SELECT COUNT(*) FROM {table}')).scalar()
            print(f'{table}: {count} rows')
        
        sql = """
        SELECT f.company_name, f.report_period, y.report_date, 
               CONCAT(LEFT(y.report_date, 4), 'Q', (CASE SUBSTR(y.report_date, 5, 2) WHEN '03' THEN 1 WHEN '06' THEN 2 WHEN '09' THEN 3 WHEN '12' THEN 4 END)) as y_period
        FROM pv_financials f
        JOIN test_em_yjbb y ON f.company_name = y.`股票简称`
        LIMIT 5
        """
        
        res = conn.execute(text(sql)).fetchall()
        print('Sample join results (pv_financials + test_em_yjbb) using SUBSTR:')
        for r in res:
            print(f"Name: {r[0]}, Period: {r[1]}, Raw Date: '{r[2]}', Period Result: {r[3]}")

        # Check other joins
        xjll_sql = """
        SELECT COUNT(*)
        FROM test_em_yjbb y
        JOIN test_em_xjll x ON x.`股票简称` = y.`股票简称` AND x.`公告日期` = y.`最新公告日期`
        """
        xjll_count = conn.execute(text(xjll_sql)).scalar()
        print(f'YJBB + XJLL join count: {xjll_count}')

        zcfz_sql = """
        SELECT COUNT(*)
        FROM test_em_yjbb y
        JOIN test_em_zcfz z ON z.`股票简称` = y.`股票简称` AND z.`公告日期` = y.`最新公告日期`
        """
        zcfz_count = conn.execute(text(zcfz_sql)).scalar()
        print(f'YJBB + ZCFZ join count: {zcfz_count}')
        
        # Check full join
        full_sql = """
        SELECT COUNT(*)
        FROM pv_financials AS f
        JOIN test_em_yjbb AS y ON f.company_name = y.`股票简称` 
             AND CONCAT(LEFT(y.report_date, 4), 'Q', (CASE SUBSTR(y.report_date, 5, 2) WHEN '03' THEN 1 WHEN '06' THEN 2 WHEN '09' THEN 3 WHEN '12' THEN 4 END)) = f.report_period
        JOIN test_em_xjll AS x ON f.company_name = x.`股票简称` AND x.`公告日期` = y.`最新公告日期`
        JOIN test_em_zcfz AS z ON f.company_name = z.`股票简称` AND z.`公告日期` = y.`最新公告日期`
        JOIN stock_prices AS s ON f.company_name = s.ticker AND f.report_period = s.report_period
        """
        full_count = conn.execute(text(full_sql)).scalar()
        print(f'Full join count (with SUBSTR): {full_count}')

if __name__ == '__main__':
    check_db()
