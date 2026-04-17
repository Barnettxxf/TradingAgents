import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text, Index, Float, Numeric, UniqueConstraint, BigInteger, \
    create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class MarketIndicatorHistory(Base):
    """
    市场指标历史表：存储多维量化指标，供 Agent 进行复盘与策略决策。
    """
    __tablename__ = 'market_indicator_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True, comment="交易对名称，如 BTC/USDT")
    timeframe = Column(String(10), nullable=False, index=True, comment="K线周期，如 15m, 1H, 4H")

    report_time = Column(DateTime, index=True, comment="指标归属的K线开启时间")
    created_at = Column(DateTime, default=datetime.datetime.now, index=True, comment="记录入库的系统时间")

    # --- 核心价格与量化指标 ---
    price = Column(Float, comment="当前标记价格 (Mark Price)")
    basis = Column(Float, comment="基差 (现货价 - 合约价)，用于衡量溢价水平")
    atr = Column(Float, comment="ATR")
    rsi = Column(Float, comment="RSI 相对强弱指标，用于判断超买超卖")
    mfi = Column(Float, comment="MFI 资金流量指标，结合成交量的强弱指标")
    top_account_ratio = Column(Float, comment="大户账户多空比")
    top_position_ratio = Column(Float, comment="大户持仓量多空比")
    volume = Column(Float, comment="该周期的成交总量")
    td_sequential = Column(Float, comment="TD 序列指标，用于判断趋势衰竭（如 TD9, TD13）")
    taker_ls_ratio = Column(Float, comment="主动成交多空比 (Taker Buy/Sell Ratio)")
    volatility = Column(Float, comment="价格波动率（通常为 ATR 或标准差的百分比）")
    oi = Column(Numeric(20, 2), comment="合约持仓量 (Open Interest)")
    cvd = Column(Float, comment="累计成交量偏差 (Cumulative Volume Delta)")
    fund_rate = Column(Float, comment="资金费率 (Funding Rate)，为百分比，即数值已经乘以100")
    signal = Column(Float, comment="系统生成的综合信号分值")

    # --- MACD 组 ---
    macd_dif = Column(Float, comment="MACD 快线 (DIF)")
    macd_dea = Column(Float, comment="MACD 慢线 (DEA)")
    macd_hist = Column(Float, comment="MACD 柱状图 (Histogram)")

    # --- 盘口墙组 (Wall) ---
    wall_ratio = Column(Float, comment="盘口挂单墙比例 (卖盘墙总深度 / 买盘墙总深度)")
    wall_imbalance_pct = Column(Float, comment="盘口不平衡率，负数代表买盘强，正数代表卖盘强")

    # --- 复杂 JSON 数据 ---
    resistance_walls = Column(JSONB, comment="阻力墙列表，存储多个价格档位及其对应的压力强度")
    support_walls = Column(JSONB, comment="支撑墙列表，存储多个价格档位及其对应的支撑强度")
    emas = Column(JSONB, comment="指数移动平均线组，包含 E5, E15, E30, E120 等")
    vmas = Column(JSONB, comment="成交量均线组，包含 VMA20, VMA50 等")
    bolling_bands = Column(JSONB, comment="布林带数据，包含 upper, middle, lower 三轨值")

    # 复合索引：大幅提升按周期调取历史序列的速度
    __table_args__ = (
        Index('idx_tf_time_symbol', 'timeframe', 'report_time', 'symbol'),
    )

    def __repr__(self):
        return f"<MarketIndicator(tf={self.timeframe}, time={self.report_time}, price={self.price})>"


class KLine(Base):
    __tablename__ = 'kline'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(30), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False, index=True)

    # ts 是毫秒时间戳，存储为 bigint 方便计算，datetime 用于人类读取和分区
    ts = Column(Integer, nullable=False, index=True)
    report_time = Column(DateTime, nullable=False, index=True)

    open = Column(Numeric(24, 8), nullable=False)
    high = Column(Numeric(24, 8), nullable=False)
    low = Column(Numeric(24, 8), nullable=False)
    close = Column(Numeric(24, 8), nullable=False)

    # vol: 交易量（个/张）
    vol = Column(Numeric(24, 8), nullable=False)
    # volCcy: 成交量（币）
    vol_ccy = Column(Numeric(24, 8), nullable=True)
    # volCcyQuote: 成交量（计价货币，如 USDT）
    vol_ccy_quote = Column(Numeric(24, 8), nullable=True)

    # confirm: K线状态，0代表未完结，1代表已完结
    confirm = Column(Integer, default=1)

    created_at = Column(DateTime, default=datetime.datetime.now)

    __table_args__ = (
        # 核心：确保同一币种同一周期同一时间戳只有一条数据
        UniqueConstraint('symbol', 'timeframe', 'ts', name='uidx_symbol_tf_ts'),
        # 查询优化：常用于按时间范围拉取特定币种的K线
        Index('idx_query_logic', 'symbol', 'timeframe', 'report_time'),
    )


engine = create_engine('postgresql://postgres:admin@192.168.31.64:5432/miniflux?sslmode=disable')
session_factory = sessionmaker(engine)
