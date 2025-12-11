# Baostock MCP Server

这是一个简单的 MCP (Model Context Protocol) 服务器示例，演示如何使用 Python 和 Baostock 库创建 MCP 工具来访问A股股票数据。

## 功能

- 获取股票基本信息
- 获取日线价格数据
- 获取实时价格（近似）
- 搜索股票
- 获取财务数据

## 安装

1. 克隆或下载项目
2. 安装依赖：

```bash
pip install -r requirements.txt
```

## 使用

运行服务器：

```bash
python mcp_baostock.py
```

## 依赖

- fastmcp
- baostock
- pandas

## 注意

Baostock 是免费的开源证券数据平台，不需要 token。