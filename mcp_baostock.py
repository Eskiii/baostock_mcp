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

if __name__ == "__main__":
    # 运行 MCP 服务器
    print("🚀 启动 Baostock MCP Server 示例")
    print("可用的工具:")
    print("- get_stock_basic: 获取股票基本信息")
    print("- get_daily_price: 获取日线价格数据")
    print("- get_real_time_price: 获取实时价格")
    print("- search_stocks: 搜索股票")
    print("- get_financial_data: 获取财务数据")
    print()

    try:
        # 使用 stdio 传输运行
        asyncio.run(mcp.run_stdio_async())
    finally:
        # 退出时登出
        try:
            bs.logout()
            print("\n👋 已断开 Baostock 连接")
        except:
            pass  # 忽略退出时的I/O错误