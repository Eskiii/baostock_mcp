"""
MCP Server 示例 - 使用 Baostock 数据接口

这是一个简单的 MCP (Model Context Protocol) 服务器示例，
演示如何使用 Python 和 Baostock 库创建 MCP 工具来访问A股股票数据。

Baostock 是免费的开源证券数据平台，提供：
- A股历史K线数据（日线、周线、月线、分钟级）
- 财务报表数据
- 股票基本信息
- 宏观经济数据

要求：
- pip install fastmcp baostock pandas

运行：
- python mcp_baostock_example.py
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Any
from fastmcp import FastMCP
import baostock as bs
import pandas as pd

# 初始化 Baostock
# Baostock 是免费的，不需要token
print("正在连接 Baostock...")
result = bs.login()
if result.error_code != '0':
    raise ValueError(f"Baostock 登录失败: {result.error_msg}")
print("✅ Baostock 连接成功")

# 创建 MCP 服务器
mcp = FastMCP(name="baostock-mcp-example", version="1.0.0")

def bs_code_to_internal(bs_code: str) -> str:
    """将 Baostock 代码转换为内部格式"""
    if bs_code.startswith("sh."):
        return f"SSE:{bs_code[3:]}"
    elif bs_code.startswith("sz."):
        return f"SZSE:{bs_code[3:]}"
    else:
        return bs_code

def internal_to_bs_code(ticker: str) -> str:
    """将内部格式转换为 Baostock 代码"""
    if ":" in ticker:
        exchange, symbol = ticker.split(":", 1)
        if exchange == "SSE":
            return f"sh.{symbol}"
        elif exchange == "SZSE":
            return f"sz.{symbol}"
    return ticker

@mcp.tool(tags={"stock"})
async def get_stock_basic(bs_code: str = "") -> List[Dict[str, Any]]:
    """
    获取股票基本信息

    Args:
        bs_code: 股票代码，如 "sh.600000" 或 "sz.000001"，留空获取全部

    Returns:
        股票基本信息列表
    """
    try:
        rs = bs.query_stock_basic(code=bs_code)

        if rs.error_code != '0':
            return [{"error": f"查询失败: {rs.error_msg}"}]

        # 转换为列表
        data_list = []
        while (rs.error_code == '0') and rs.next():
            data_list.append(rs.get_row_data())

        if not data_list:
            return [{"error": "未找到股票信息"}]

        # 转换为字典列表
        result = []
        for row in data_list:
            result.append({
                "code": row[0],  # 证券代码
                "name": row[1],  # 证券名称
                "ipo_date": row[2],  # IPO日期
                "out_date": row[3],  # 退市日期
                "type": row[4],  # 证券类型
                "status": row[5],  # 证券状态
                "internal_ticker": bs_code_to_internal(row[0])
            })

        return result

    except Exception as e:
        return [{"error": str(e)}]

@mcp.tool(tags={"stock"})
async def get_daily_price(bs_code: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    获取股票日线数据

    Args:
        bs_code: 股票代码，如 "sh.600000"
        start_date: 开始日期，格式 YYYY-MM-DD
        end_date: 结束日期，格式 YYYY-MM-DD

    Returns:
        日线价格数据列表
    """
    try:
        rs = bs.query_history_k_data_plus(
            code=bs_code,
            fields="date,code,open,high,low,close,volume,amount,turn",
            start_date=start_date,
            end_date=end_date,
            frequency="d",
            adjustflag="3"  # 后复权
        )

        if rs.error_code != '0':
            return [{"error": f"查询失败: {rs.error_msg}"}]

        # 转换为列表
        data_list = []
        while (rs.error_code == '0') and rs.next():
            data_list.append(rs.get_row_data())

        if not data_list:
            return [{"error": "未找到价格数据"}]

        # 转换为字典列表
        result = []
        for row in data_list:
            result.append({
                "date": row[0],
                "code": row[1],
                "open": float(row[2]) if row[2] else None,
                "high": float(row[3]) if row[3] else None,
                "low": float(row[4]) if row[4] else None,
                "close": float(row[5]) if row[5] else None,
                "volume": int(float(row[6])) if row[6] else None,
                "amount": float(row[7]) if row[7] else None,
                "turnover": float(row[8]) if row[8] else None,
                "internal_ticker": bs_code_to_internal(row[1])
            })

        return result

    except Exception as e:
        return [{"error": str(e)}]

@mcp.tool(tags={"stock"})
async def get_real_time_price(bs_code: str) -> Dict[str, Any]:
    """
    获取实时股价（使用最新日线数据作为近似）

    Args:
        bs_code: 股票代码，如 "sh.600000"

    Returns:
        最新价格信息
    """
    try:
        # 获取最近一个月的数据
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now().replace(day=1)).strftime("%Y-%m-%d")

        rs = bs.query_history_k_data_plus(
            code=bs_code,
            fields="date,code,open,high,low,close,volume,amount,turn",
            start_date=start_date,
            end_date=end_date,
            frequency="d",
            adjustflag="3"
        )

        if rs.error_code != '0':
            return {"error": f"查询失败: {rs.error_msg}"}

        # 获取最新数据
        data_list = []
        while (rs.error_code == '0') and rs.next():
            data_list.append(rs.get_row_data())

        if not data_list:
            return {"error": "未找到价格数据"}

        # 取最新一条
        row = data_list[-1]

        return {
            "date": row[0],
            "code": row[1],
            "price": float(row[5]) if row[5] else None,
            "open": float(row[2]) if row[2] else None,
            "high": float(row[3]) if row[3] else None,
            "low": float(row[4]) if row[4] else None,
            "close": float(row[5]) if row[5] else None,
            "volume": int(float(row[6])) if row[6] else None,
            "amount": float(row[7]) if row[7] else None,
            "turnover": float(row[8]) if row[8] else None,
            "internal_ticker": bs_code_to_internal(row[1])
        }

    except Exception as e:
        return {"error": str(e)}

@mcp.tool(tags={"stock"})
async def search_stocks(keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    搜索股票

    Args:
        keyword: 搜索关键词（股票名称或代码）
        limit: 返回结果数量限制

    Returns:
        匹配的股票列表
    """
    try:
        # 获取所有A股股票
        today = datetime.now().strftime("%Y-%m-%d")
        rs = bs.query_all_stock(day=today)

        if rs.error_code != '0':
            return [{"error": f"查询失败: {rs.error_msg}"}]

        # 转换为DataFrame进行搜索
        data_list = []
        while (rs.error_code == '0') and rs.next():
            data_list.append(rs.get_row_data())

        if not data_list:
            return [{"error": "未找到股票数据"}]

        df = pd.DataFrame(data_list, columns=rs.fields)

        # 过滤包含关键词的股票
        mask = (
            df['code_name'].str.contains(keyword, case=False, na=False) |
            df['code'].str.contains(keyword, case=False, na=False)
        )

        results = df[mask].head(limit)

        # 转换为字典列表
        result = []
        for _, row in results.iterrows():
            bs_code = str(row['code'])
            result.append({
                "code": bs_code,
                "name": str(row['code_name']),
                "internal_ticker": bs_code_to_internal(bs_code)
            })

        return result

    except Exception as e:
        return [{"error": str(e)}]

@mcp.tool(tags={"finance"})
async def get_financial_data(bs_code: str, year: int = None, quarter: int = None) -> Dict[str, Any]:
    """
    获取财务数据

    Args:
        bs_code: 股票代码，如 "sh.600000"
        year: 年份，默认最新年份
        quarter: 季度(1-4)，默认最新季度

    Returns:
        财务数据字典
    """
    try:
        # 默认使用最新年季
        if year is None or quarter is None:
            now = datetime.now()
            year = now.year
            quarter = (now.month - 1) // 3 + 1

            # 如果是季度初，可能数据还没出，用上季度
            if now.month % 3 == 1 and now.day < 15:
                quarter -= 1
                if quarter == 0:
                    quarter = 4
                    year -= 1

        # 并行获取各种财务数据
        profit_rs = bs.query_profit_data(code=bs_code, year=year, quarter=quarter)
        operation_rs = bs.query_operation_data(code=bs_code, year=year, quarter=quarter)
        growth_rs = bs.query_growth_data(code=bs_code, year=year, quarter=quarter)
        balance_rs = bs.query_balance_data(code=bs_code, year=year, quarter=quarter)
        cash_rs = bs.query_cash_flow_data(code=bs_code, year=year, quarter=quarter)

        def rs_to_dict(rs):
            if rs.error_code != '0':
                return None
            data_list = []
            while (rs.error_code == '0') and rs.next():
                data_list.append(rs.get_row_data())
            if not data_list:
                return None
            df = pd.DataFrame(data_list, columns=rs.fields)
            return df.iloc[0].to_dict() if not df.empty else None

        return {
            "year": year,
            "quarter": quarter,
            "code": bs_code,
            "internal_ticker": bs_code_to_internal(bs_code),
            "profitability": rs_to_dict(profit_rs),
            "operation": rs_to_dict(operation_rs),
            "growth": rs_to_dict(growth_rs),
            "balance": rs_to_dict(balance_rs),
            "cash_flow": rs_to_dict(cash_rs)
        }

    except Exception as e:
        return {"error": str(e)}

@mcp.tool(tags={"market"})
async def get_trade_dates(start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    获取交易日历

    Args:
        start_date: 开始日期，格式 YYYY-MM-DD
        end_date: 结束日期，格式 YYYY-MM-DD

    Returns:
        交易日期列表
    """
    try:
        rs = bs.query_trade_dates(start_date=start_date, end_date=end_date)

        if rs.error_code != '0':
            return [{"error": f"查询失败: {rs.error_msg}"}]

        # 转换为列表
        data_list = []
        while (rs.error_code == '0') and rs.next():
            data_list.append(rs.get_row_data())

        if not data_list:
            return [{"error": "未找到交易日期数据"}]

        # 转换为字典列表
        result = []
        for row in data_list:
            result.append({
                "calendar_date": row[0],  # 日历日期
                "is_trading_day": int(row[1]) == 1  # 是否交易日
            })

        return result

    except Exception as e:
        return [{"error": str(e)}]

@mcp.tool(tags={"stock"})
async def get_dividend_data(bs_code: str, year: str = "", year_type: str = "report") -> List[Dict[str, Any]]:
    """
    获取分红送配数据

    Args:
        bs_code: 股票代码，如 "sh.600000"
        year: 年份，格式 YYYY，默认空表示全部
        year_type: 年份类型，"report"表示年报，"operation"表示年报

    Returns:
        分红送配数据列表
    """
    try:
        rs = bs.query_dividend_data(code=bs_code, year=year, yearType=year_type)

        if rs.error_code != '0':
            return [{"error": f"查询失败: {rs.error_msg}"}]

        # 转换为列表
        data_list = []
        while (rs.error_code == '0') and rs.next():
            data_list.append(rs.get_row_data())

        if not data_list:
            return [{"error": "未找到分红数据"}]

        # 转换为字典列表
        result = []
        for row in data_list:
            result.append({
                "code": row[0],  # 证券代码
                "divid_pre_tax": float(row[1]) if row[1] else None,  # 预案税前分红
                "divid_after_tax": float(row[2]) if row[2] else None,  # 预案税后分红
                "record_date": row[3],  # 股权登记日
                "ex_dividend_date": row[4],  # 除权除息日
                "dividend_date": row[5],  # 分红到账日
                "dividend_year": row[6],  # 分红年度
                "internal_ticker": bs_code_to_internal(row[0])
            })

        return result

    except Exception as e:
        return [{"error": str(e)}]

@mcp.tool(tags={"stock"})
async def get_stock_industry(bs_code: str = "") -> List[Dict[str, Any]]:
    """
    获取股票行业分类信息

    Args:
        bs_code: 股票代码，如 "sh.600000"，留空获取全部

    Returns:
        行业分类信息列表
    """
    try:
        rs = bs.query_stock_industry(code=bs_code)

        if rs.error_code != '0':
            return [{"error": f"查询失败: {rs.error_msg}"}]

        # 转换为列表
        data_list = []
        while (rs.error_code == '0') and rs.next():
            data_list.append(rs.get_row_data())

        if not data_list:
            return [{"error": "未找到行业分类数据"}]

        # 转换为字典列表
        result = []
        for row in data_list:
            result.append({
                "update_date": row[0],  # 更新日期
                "code": row[1],  # 证券代码
                "code_name": row[2],  # 证券名称
                "industry": row[3],  # 所属行业
                "industry_classification": row[4],  # 行业分类
                "internal_ticker": bs_code_to_internal(row[1])
            })

        return result

    except Exception as e:
        return [{"error": str(e)}]

@mcp.tool(tags={"index"})
async def get_index_data(index_code: str, start_date: str, end_date: str, frequency: str = "d") -> List[Dict[str, Any]]:
    """
    获取指数数据

    Args:
        index_code: 指数代码，如 "sh.000001" (上证指数), "sz.399001" (深证成指)
        start_date: 开始日期，格式 YYYY-MM-DD
        end_date: 结束日期，格式 YYYY-MM-DD
        frequency: 频率，"d"日线，"w"周线，"m"月线

    Returns:
        指数数据列表
    """
    try:
        rs = bs.query_history_k_data_plus(
            code=index_code,
            fields="date,code,open,high,low,close,volume,amount",
            start_date=start_date,
            end_date=end_date,
            frequency=frequency,
            adjustflag="3"
        )

        if rs.error_code != '0':
            return [{"error": f"查询失败: {rs.error_msg}"}]

        # 转换为列表
        data_list = []
        while (rs.error_code == '0') and rs.next():
            data_list.append(rs.get_row_data())

        if not data_list:
            return [{"error": "未找到指数数据"}]

        # 转换为字典列表
        result = []
        for row in data_list:
            result.append({
                "date": row[0],
                "code": row[1],
                "open": float(row[2]) if row[2] else None,
                "high": float(row[3]) if row[3] else None,
                "low": float(row[4]) if row[4] else None,
                "close": float(row[5]) if row[5] else None,
                "volume": int(float(row[6])) if row[6] else None,
                "amount": float(row[7]) if row[7] else None,
                "internal_ticker": bs_code_to_internal(row[1])
            })

        return result

    except Exception as e:
        return [{"error": str(e)}]

@mcp.tool(tags={"macro"})
async def get_macro_data(data_type: str, year: str = "") -> List[Dict[str, Any]]:
    """
    获取宏观经济数据

    Args:
        data_type: 数据类型，"gdp"GDP, "ppi"PPI, "cpi"CPI, "pmi"PMI
        year: 年份，格式 YYYY，默认空表示全部

    Returns:
        宏观经济数据列表
    """
    try:
        if data_type == "gdp":
            rs = bs.query_gdp_data(year=year)
        elif data_type == "ppi":
            rs = bs.query_ppi_data(year=year)
        elif data_type == "cpi":
            rs = bs.query_cpi_data(year=year)
        elif data_type == "pmi":
            rs = bs.query_pmi_data(year=year)
        else:
            return [{"error": f"不支持的数据类型: {data_type}"}]

        if rs.error_code != '0':
            return [{"error": f"查询失败: {rs.error_msg}"}]

        # 转换为列表
        data_list = []
        while (rs.error_code == '0') and rs.next():
            data_list.append(rs.get_row_data())

        if not data_list:
            return [{"error": "未找到宏观数据"}]

        # 转换为字典列表
        result = []
        for row in data_list:
            result.append({
                "stat_year": row[0],  # 统计年度
                "stat_quarter": row[1],  # 统计季度
                "data_value": float(row[2]) if row[2] else None,  # 数据值
                "data_type": data_type
            })

        return result

    except Exception as e:
        return [{"error": str(e)}]

@mcp.tool(tags={"index"})
async def get_index_constituents(index_code: str, date: str = "") -> List[Dict[str, Any]]:
    """
    获取指数成分股

    Args:
        index_code: 指数代码，"hs300"沪深300, "zz500"中证500, "sz50"上证50
        date: 日期，格式 YYYY-MM-DD，默认最新

    Returns:
        指数成分股列表
    """
    try:
        if index_code == "hs300":
            rs = bs.query_hs300_stocks(date=date)
        elif index_code == "zz500":
            rs = bs.query_zz500_stocks(date=date)
        elif index_code == "sz50":
            rs = bs.query_sz50_stocks(date=date)
        else:
            return [{"error": f"不支持的指数: {index_code}"}]

        if rs.error_code != '0':
            return [{"error": f"查询失败: {rs.error_msg}"}]

        # 转换为列表
        data_list = []
        while (rs.error_code == '0') and rs.next():
            data_list.append(rs.get_row_data())

        if not data_list:
            return [{"error": "未找到成分股数据"}]

        # 转换为字典列表
        result = []
        for row in data_list:
            result.append({
                "update_date": row[0],  # 更新日期
                "code": row[1],  # 证券代码
                "code_name": row[2],  # 证券名称
                "weight": float(row[3]) if row[3] else None,  # 权重
                "index_code": index_code,
                "internal_ticker": bs_code_to_internal(row[1])
            })

        return result

    except Exception as e:
        return [{"error": str(e)}]

@mcp.tool(tags={"stock"})
async def get_adjust_factor(bs_code: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    获取复权因子信息

    Args:
        bs_code: 股票代码，如 "sh.600000"
        start_date: 开始日期，格式 YYYY-MM-DD
        end_date: 结束日期，格式 YYYY-MM-DD

    Returns:
        复权因子数据列表
    """
    try:
        rs = bs.query_adjust_factor(code=bs_code, start_date=start_date, end_date=end_date)

        if rs.error_code != '0':
            return [{"error": f"查询失败: {rs.error_msg}"}]

        # 转换为列表
        data_list = []
        while (rs.error_code == '0') and rs.next():
            data_list.append(rs.get_row_data())

        if not data_list:
            return [{"error": "未找到复权因子数据"}]

        # 转换为字典列表
        result = []
        for row in data_list:
            result.append({
                "date": row[0],  # 日期
                "code": row[1],  # 证券代码
                "fore_adjust_factor": float(row[2]) if row[2] else None,  # 前复权因子
                "back_adjust_factor": float(row[3]) if row[3] else None,  # 后复权因子
                "adjust_factor": float(row[4]) if row[4] else None,  # 复权因子
                "internal_ticker": bs_code_to_internal(row[1])
            })

        return result

    except Exception as e:
        return [{"error": str(e)}]

@mcp.tool(tags={"finance"})
async def get_performance_express_report(bs_code: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    获取季频公司业绩快报

    Args:
        bs_code: 股票代码，如 "sh.600000"
        start_date: 开始日期，格式 YYYY-MM-DD
        end_date: 结束日期，格式 YYYY-MM-DD

    Returns:
        业绩快报数据列表
    """
    try:
        rs = bs.query_performance_express_report(code=bs_code, start_date=start_date, end_date=end_date)

        if rs.error_code != '0':
            return [{"error": f"查询失败: {rs.error_msg}"}]

        # 转换为列表
        data_list = []
        while (rs.error_code == '0') and rs.next():
            data_list.append(rs.get_row_data())

        if not data_list:
            return [{"error": "未找到业绩快报数据"}]

        # 转换为字典列表
        result = []
        for row in data_list:
            result.append({
                "code": row[0],  # 证券代码
                "ann_date": row[1],  # 公告日期
                "report_date": row[2],  # 报告期
                "eps": float(row[3]) if row[3] else None,  # 每股收益
                "roe": float(row[4]) if row[4] else None,  # 净资产收益率
                "net_profit": float(row[5]) if row[5] else None,  # 净利润
                "revenue": float(row[6]) if row[6] else None,  # 营业收入
                "internal_ticker": bs_code_to_internal(row[0])
            })

        return result

    except Exception as e:
        return [{"error": str(e)}]

@mcp.tool(tags={"finance"})
async def get_forecast_report(bs_code: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    获取季频公司业绩预告

    Args:
        bs_code: 股票代码，如 "sh.600000"
        start_date: 开始日期，格式 YYYY-MM-DD
        end_date: 结束日期，格式 YYYY-MM-DD

    Returns:
        业绩预告数据列表
    """
    try:
        rs = bs.query_forecast_report(code=bs_code, start_date=start_date, end_date=end_date)

        if rs.error_code != '0':
            return [{"error": f"查询失败: {rs.error_msg}"}]

        # 转换为列表
        data_list = []
        while (rs.error_code == '0') and rs.next():
            data_list.append(rs.get_row_data())

        if not data_list:
            return [{"error": "未找到业绩预告数据"}]

        # 转换为字典列表
        result = []
        for row in data_list:
            result.append({
                "code": row[0],  # 证券代码
                "ann_date": row[1],  # 公告日期
                "forecast_type": row[2],  # 业绩预告类型
                "forecast_content": row[3],  # 业绩预告内容
                "profit_min": float(row[4]) if row[4] else None,  # 净利润最小值
                "profit_max": float(row[5]) if row[5] else None,  # 净利润最大值
                "last_year_profit": float(row[6]) if row[6] else None,  # 上年同期净利润
                "forecast_date": row[7],  # 预告日期
                "internal_ticker": bs_code_to_internal(row[0])
            })

        return result

    except Exception as e:
        return [{"error": str(e)}]

@mcp.tool(tags={"stock"})
async def get_all_stocks_daily_price(date: str, limit: int = 100) -> List[Dict[str, Any]]:
    """
    获取指定日期全部股票的日K线数据

    Args:
        date: 指定日期，格式 YYYY-MM-DD
        limit: 返回股票数量限制，默认100（避免返回过多数据）

    Returns:
        指定日期全部股票的日K线数据列表
    """
    try:
        # 获取所有A股股票列表
        rs = bs.query_all_stock(day=date)

        if rs.error_code != '0':
            return [{"error": f"查询股票列表失败: {rs.error_msg}"}]

        # 转换为股票代码列表
        stock_codes = []
        while (rs.error_code == '0') and rs.next():
            row = rs.get_row_data()
            stock_codes.append(row[0])  # code字段

        if not stock_codes:
            return [{"error": "未找到股票列表"}]

        # 限制数量
        stock_codes = stock_codes[:limit]

        # 获取每个股票的日K线数据
        result = []
        for code in stock_codes:
            try:
                price_rs = bs.query_history_k_data_plus(
                    code=code,
                    fields="date,code,open,high,low,close,volume,amount,turn",
                    start_date=date,
                    end_date=date,
                    frequency="d",
                    adjustflag="3"
                )

                if price_rs.error_code == '0':
                    data_list = []
                    while (price_rs.error_code == '0') and price_rs.next():
                        data_list.append(price_rs.get_row_data())

                    if data_list:
                        row = data_list[0]  # 取第一条（当天数据）
                        result.append({
                            "date": row[0],
                            "code": row[1],
                            "open": float(row[2]) if row[2] else None,
                            "high": float(row[3]) if row[3] else None,
                            "low": float(row[4]) if row[4] else None,
                            "close": float(row[5]) if row[5] else None,
                            "volume": int(float(row[6])) if row[6] else None,
                            "amount": float(row[7]) if row[7] else None,
                            "turnover": float(row[8]) if row[8] else None,
                            "internal_ticker": bs_code_to_internal(row[1])
                        })
            except Exception as e:
                # 跳过单个股票的错误，继续下一个
                continue

        if not result:
            return [{"error": "未找到日K线数据"}]

        return result

    except Exception as e:
        return [{"error": str(e)}]

if __name__ == "__main__":
    # 运行 MCP 服务器
    print("🚀 启动 Baostock MCP Server 示例")
    print("可用的工具:")
    print("- get_stock_basic: 获取股票基本信息")
    print("- get_daily_price: 获取日线价格数据")
    print("- get_real_time_price: 获取实时价格")
    print("- search_stocks: 搜索股票")
    print("- get_financial_data: 获取财务数据")
    print("- get_trade_dates: 获取交易日历")
    print("- get_dividend_data: 获取分红送配数据")
    print("- get_stock_industry: 获取股票行业分类")
    print("- get_index_data: 获取指数数据")
    print("- get_macro_data: 获取宏观经济数据")
    print("- get_index_constituents: 获取指数成分股")
    print("- get_adjust_factor: 获取复权因子信息")
    print("- get_performance_express_report: 获取季频公司业绩快报")
    print("- get_forecast_report: 获取季频公司业绩预告")
    print("- get_all_stocks_daily_price: 获取指定日期全部股票的日K线数据")
    print()

    try:
        # 使用 stdio 传输运行
        asyncio.run(mcp.run_streamable_http_async())
    finally:
        # 退出时登出
        try:
            bs.logout()
            print("\n👋 已断开 Baostock 连接")
        except:
            pass  # 忽略退出时的I/O错误