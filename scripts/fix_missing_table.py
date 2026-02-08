
"""数据库缺失表修复和模拟数据初始化脚本。

该脚本用于创建 stock_prices 表，并为指定的公司填充 2018-2023 年的季度财务模拟数据。
"""

import os
from sqlalchemy import create_engine, text
from autoplan_agent.config import Settings


def main():
    """执行数据库表修复和数据填充。"""
    settings = Settings()
    dsn = settings.mysql_dsn()
    if not dsn:
        print("MySQL DSN not found")
        return
    
    engine = create_engine(dsn)
    
    with engine.begin() as conn:
        # Create stock_prices table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS stock_prices (
                id INT AUTO_INCREMENT PRIMARY KEY,
                company_id INT,
                ticker VARCHAR(20),
                market_cap DOUBLE,
                pe_ratio DOUBLE,
                fiscal_year INT,
                report_period VARCHAR(10)
            )
        """))
        
        # Clear existing dummy data if any
        conn.execute(text("DELETE FROM pv_financials WHERE report_period LIKE '201%' OR report_period LIKE '202%'"))
        conn.execute(text("DELETE FROM stock_prices WHERE report_period LIKE '201%' OR report_period LIKE '202%'"))
        conn.execute(text("DELETE FROM test_em_yjbb WHERE `股票简称` IN ('隆基绿能', '通威股份', '阳光电源')"))
        conn.execute(text("DELETE FROM test_em_xjll WHERE `股票简称` IN ('隆基绿能', '通威股份', '阳光电源')"))
        conn.execute(text("DELETE FROM test_em_zcfz WHERE `股票简称` IN ('隆基绿能', '通威股份', '阳光电源')"))

        # Companies to add data for
        companies = [
            ("隆基绿能", "601012"),
            ("通威股份", "600438"),
            ("阳光电源", "300274")
        ]

        # Generate quarterly data for 2018-2023
        for company_name, ticker in companies:
            for year in range(2018, 2024):
                for quarter in range(1, 5):
                    report_period = f"{year}Q{quarter}"
                    # In EM tables, it's YYYYMMDD string
                    em_report_date = f"{year}{quarter*3:02d}30" if quarter < 4 else f"{year}1231"
                    if quarter == 1: em_report_date = f"{year}0331"
                    elif quarter == 2: em_report_date = f"{year}0630"
                    elif quarter == 3: em_report_date = f"{year}0930"
                    
                    # Insert into pv_financials
                    conn.execute(text("""
                        INSERT INTO pv_financials (company_name, stock_code, report_period, revenue_billion, net_profit_billion, revenue_growth_pct, net_profit_growth_pct, gross_margin_pct, update_date)
                        VALUES (:company_name, :stock_code, :report_period, :revenue, :profit, :rev_growth, :profit_growth, :margin, :update_date)
                    """ ), {
                        "company_name": company_name, "stock_code": ticker, "report_period": report_period,
                        "revenue": 10.5 + year - 2018 + quarter*0.5, "profit": 1.2 + (year-2018)*0.2 + quarter*0.1,
                        "rev_growth": 15.5, "profit_growth": 12.0, "margin": 25.5, "update_date": f"{year}-{quarter*3:02d}-28"
                    })

                    # Insert into stock_prices
                    conn.execute(text("""
                        INSERT INTO stock_prices (ticker, market_cap, pe_ratio, report_period, fiscal_year)
                        VALUES (:ticker, :mc, :pe, :rp, :fy)
                    """ ), {
                        "ticker": company_name, "mc": 1000.0 + (year-2018)*100, "pe": 25.0 + (year-2018), "rp": report_period, "fy": year
                    })

                    # Insert into test_em_yjbb
                    conn.execute(text("""
                        INSERT INTO test_em_yjbb (`股票代码`, `股票简称`, `每股收益`, `营业总收入-营业总收入`, `营业总收入-同比增长`, `净利润-净利润`, `净利润-同比增长`, `净资产收益率`, `销售毛利率`, `最新公告日期`, `report_date`)
                        VALUES (:code, :name, :eps, :rev, :rev_g, :profit, :profit_g, :roe, :margin, :pub_date, :rdate)
                    """ ), {
                        "code": ticker, "name": company_name, "eps": 0.5 + quarter*0.1, "rev": (10.5 + year - 2018)*1e9, "rev_g": 15.5, 
                        "profit": (1.2 + (year-2018)*0.2)*1e9, "profit_g": 12.0, "roe": 15.2, "margin": 25.5, 
                        "pub_date": f"{year}-{quarter*3:02d}-28", "rdate": em_report_date
                    })

                    # Insert into test_em_xjll
                    conn.execute(text("""
                        INSERT INTO test_em_xjll (`股票代码`, `股票简称`, `经营性现金流-现金流量净额`, `净现金流-净现金流`, `公告日期`, `report_date`)
                        VALUES (:code, :name, :ocf, :ncf, :pub_date, :rdate)
                    """ ), {
                        "code": ticker, "name": company_name, "ocf": 1.5e9, "ncf": 0.5e9, "pub_date": f"{year}-{quarter*3:02d}-28", "rdate": em_report_date
                    })

                    # Insert into test_em_zcfz
                    conn.execute(text("""
                        INSERT INTO test_em_zcfz (`股票代码`, `股票简称`, `资产-总资产`, `资产-货币资金`, `资产-应收账款`, `负债-总负债`, `资产负债率`, `股东权益合计`, `公告日期`, `report_date`)
                        VALUES (:code, :name, :total_a, :cash, :ar, :total_l, :ratio, :equity, :pub_date, :rdate)
                    """ ), {
                        "code": ticker, "name": company_name, "total_a": 50e9, "cash": 10e9, "ar": 5e9, "total_l": 25e9, "ratio": 50.0, "equity": 25e9, 
                        "pub_date": f"{year}-{quarter*3:02d}-28", "rdate": em_report_date
                    })

        conn.commit()
    print(f"Inserted comprehensive dummy data for {len(companies)} companies across 2018-2023.")


if __name__ == '__main__':
    main()
