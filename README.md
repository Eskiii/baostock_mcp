# Baostock MCP Server

使用FastMCP和baoStock创建的MCP服务器。baoStock是一个免费、开源的证券数据平台，无需apikey。

## 功能

### 股票数据
- `get_stock_basic`: 获取股票基本信息
- `get_daily_price`: 获取日线价格数据
- `get_real_time_price`: 获取实时价格（近似）
- `search_stocks`: 搜索股票
- `get_all_stocks_daily_price`: 获取指定日期全部股票的日K线数据

### 财务数据
- `get_financial_data`: 获取财务数据（利润表、资产负债表、现金流量表等）
- `get_performance_express_report`: 获取季频公司业绩快报
- `get_forecast_report`: 获取季频公司业绩预告
- `get_dividend_data`: 获取分红送配数据
- `get_adjust_factor`: 获取复权因子信息

### 市场数据
- `get_trade_dates`: 获取交易日历
- `get_stock_industry`: 获取股票行业分类
- `get_index_data`: 获取指数数据
- `get_index_constituents`: 获取指数成分股（沪深300、中证500、上证50）
- `get_macro_data`: 获取宏观经济数据（GDP、PPI、CPI、PMI）

## 安装

1. 克隆或下载项目
2. 安装依赖：

```bash
pip install -r requirements.txt
```

## 使用

### 运行服务器

运行服务器：

```bash
python mcp_baostock.py
```

### 在 Cherry Studio 中使用

1. 启动服务器后，在 Cherry Studio 的设置中导入以下 JSON 配置：

```json
{
  "mcpServers": {
    "baostock_mcp": {
      "type": "streamableHttp",
      "url": "http://127.0.0.1:8000/mcp"
    }
  }
}
```

2. 保存配置后，即可在 Cherry Studio 中使用 Baostock MCP 工具。

## 依赖

- fastmcp
- baostock
- pandas

## 注意

- Baostock 是免费的开源证券数据平台，不需要 token
- 所有数据均为历史数据，实时性可能有延迟
- 部分工具可能因数据量大而设置了默认限制（如 `get_all_stocks_daily_price` 默认返回前100只股票）
- 建议在使用前检查 Baostock 官方文档以了解数据更新频率