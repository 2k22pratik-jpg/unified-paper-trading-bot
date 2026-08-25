import os
import time
import random
import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

import pandas as pd

from strategy import StrategyEngine


# ============================================================
# CONFIGURATION
# ============================================================

STARTING_BALANCE = 10000.0
RISK_PER_TRADE = 0.01
MAX_DAILY_LOSS = 0.03
MAX_OPEN_TRADES = 5

SCAN_INTERVAL = 60

BINARY_STAKE_PERCENT = 0.005
BINARY_PAYOUT = 0.80
BINARY_EXPIRY_MINUTES = 5

PORT = int(os.environ.get("PORT", "10000"))


CRYPTO_SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
    "BNBUSDT",
    "SOLUSDT",
]

FOREX_PAIRS = [
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "USDCHF",
    "AUDUSD",
    "USDCAD",
    "NZDUSD",
    "EURGBP",
    "EURJPY",
    "GBPJPY",
]

BINARY_SYMBOLS = [
    "BTCUSDT",
    "EURUSD",
    "GBPUSD",
]


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger("UnifiedPaperBot")


# ============================================================
# TRADE
# ============================================================

@dataclass
class Trade:
    market: str
    symbol: str
    direction: str
    entry: float
    stop_loss: float
    take_profit: float
    amount: float
    confidence: float
    opened_at: datetime
    expiry_time: object = None


# ============================================================
# PAPER ACCOUNT
# ============================================================

class PaperAccount:

    def __init__(self):
        self.starting_balance = STARTING_BALANCE
        self.balance = STARTING_BALANCE
        self.equity = STARTING_BALANCE

        self.daily_pnl = 0.0

        self.open_trades = []
        self.closed_trades = []

        self.wins = 0
        self.losses = 0

        self.lock = threading.RLock()

    def can_trade(self):

        with self.lock:

            if len(self.open_trades) >= MAX_OPEN_TRADES:
                return False

            max_loss = (
                self.starting_balance *
                MAX_DAILY_LOSS
            )

            if self.daily_pnl <= -max_loss:
                return False

            return True

    def position_size(self, entry, stop_loss):

        distance = abs(entry - stop_loss)

        if distance <= 0:
            return 0.0

        risk_money = (
            self.balance *
            RISK_PER_TRADE
        )

        return risk_money / distance

    def open_trade(self, trade):

        with self.lock:

            if not self.can_trade():
                return False

            for existing in self.open_trades:

                if (
                    existing.market == trade.market
                    and existing.symbol == trade.symbol
                ):
                    return False

            self.open_trades.append(trade)

            logger.info(
                "OPEN | %s | %s | %s | Entry %.5f | Confidence %.2f",
                trade.market,
                trade.symbol,
                trade.direction,
                trade.entry,
                trade.confidence
            )

            return True

    def close_trade(
        self,
        trade,
        exit_price,
        binary_result=None
    ):

        with self.lock:

            if trade not in self.open_trades:
                return

            if trade.market == "BINARY":

                if binary_result == "WIN":
                    pnl = trade.amount * BINARY_PAYOUT
                else:
                    pnl = -trade.amount

            elif trade.direction == "BUY":

                pnl = (
                    exit_price -
                    trade.entry
                ) * trade.amount

            else:

                pnl = (
                    trade.entry -
                    exit_price
                ) * trade.amount

            self.balance += pnl
            self.equity = self.balance
            self.daily_pnl += pnl

            self.open_trades.remove(trade)
            self.closed_trades.append(trade)

            if pnl > 0:
                self.wins += 1
            else:
                self.losses += 1

            logger.info(
                "CLOSE | %s | %s | P&L %.2f | Balance %.2f",
                trade.market,
                trade.symbol,
                pnl,
                self.balance
            )

    def statistics(self):

        with self.lock:

            total = self.wins + self.losses

            if total > 0:
                win_rate = (
                    self.wins / total
                ) * 100
            else:
                win_rate = 0.0

            return {
                "balance": round(self.balance, 2),
                "daily_pnl": round(self.daily_pnl, 2),
                "open_trades": len(self.open_trades),
                "closed_trades": len(self.closed_trades),
                "wins": self.wins,
                "losses": self.losses,
                "win_rate": round(win_rate, 2)
            }


# ============================================================
# SIMULATED MARKET DATA
# ============================================================

class MarketData:

    BASE_PRICES = {
        "BTCUSDT": 110000.0,
        "ETHUSDT": 4000.0,
        "BNBUSDT": 800.0,
        "SOLUSDT": 200.0,

        "EURUSD": 1.17,
        "GBPUSD": 1.35,
        "USDJPY": 148.0,
        "USDCHF": 0.80,
        "AUDUSD": 0.65,
        "USDCAD": 1.38,
        "NZDUSD": 0.59,
        "EURGBP": 0.87,
        "EURJPY": 173.0,
        "GBPJPY": 200.0
    }

    @classmethod
    def get_price(cls, symbol):

        base = cls.BASE_PRICES.get(
            symbol,
            100.0
        )

        movement = random.uniform(
            -0.002,
            0.002
        )

        return base * (1 + movement)

    @classmethod
    def get_candles(
        cls,
        symbol,
        count=300
    ):

        base = cls.BASE_PRICES.get(
            symbol,
            100.0
        )

        price = base
        candles = []

        for _ in range(count):

            movement = random.uniform(
                -0.003,
                0.003
            )

            price *= (1 + movement)

            open_price = price * (
                1 + random.uniform(
                    -0.0005,
                    0.0005
                )
            )

            high = price * (
                1 + random.uniform(
                    0,
                    0.001
                )
            )

            low = price * (
                1 - random.uniform(
                    0,
                    0.001
                )
            )

            volume = random.randint(
                100,
                10000
            )

            candles.append({
                "open": open_price,
                "high": high,
                "low": low,
                "close": price,
                "volume": volume
            })

        return candles


# ============================================================
# NORMAL MARKET ENGINE
# ============================================================

class MarketEngine:

    def __init__(
        self,
        market,
        symbols,
        strategy,
        account
    ):

        self.market = market
        self.symbols = symbols
        self.strategy = strategy
        self.account = account

    def scan(self):

        for symbol in self.symbols:

            if not self.account.can_trade():
                return

            try:

                candles = MarketData.get_candles(
                    symbol
                )

                df = pd.DataFrame(candles)

                result = (
                    self.strategy
                    .generate_signal(df)
                )

                signal = result.get(
                    "signal",
                    "HOLD"
                )

                if signal == "HOLD":
                    continue

                self.execute(
                    symbol,
                    result
                )

            except Exception as error:

                logger.exception(
                    "%s error for %s: %s",
                    self.market,
                    symbol,
                    error
                )

    def execute(
        self,
        symbol,
        result
    ):

        entry = float(
            result["price"]
        )

        atr = result.get("atr")

        if atr is None:
            return

        if atr <= 0:
            return

        stop_distance = atr * 1.5
        target_distance = atr * 3.0

        if result["signal"] == "BUY":

            stop_loss = (
                entry -
                stop_distance
            )

            take_profit = (
                entry +
                target_distance
            )

        else:

            stop_loss = (
                entry +
                stop_distance
            )

            take_profit = (
                entry -
                target_distance
            )

        amount = self.account.position_size(
            entry,
            stop_loss
        )

        if amount <= 0:
            return

        trade = Trade(
            market=self.market,
            symbol=symbol,
            direction=result["signal"],
            entry=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            amount=amount,
            confidence=float(
                result["confidence"]
            ),
            opened_at=datetime.now(
                timezone.utc
            )
        )

        self.account.open_trade(trade)


# ============================================================
# BINARY PAPER ENGINE
# ============================================================

class BinaryEngine:

    def __init__(
        self,
        strategy,
        account
    ):

        self.strategy = strategy
        self.account = account

    def scan(self):

        for symbol in BINARY_SYMBOLS:

            if not self.account.can_trade():
                return

            try:

                candles = MarketData.get_candles(
                    symbol
                )

                df = pd.DataFrame(candles)

                result = (
                    self.strategy
                    .generate_signal(df)
                )

                if result["signal"] == "HOLD":
                    continue

                self.execute(
                    symbol,
                    result
                )

            except Exception as error:

                logger.exception(
                    "Binary error for %s: %s",
                    symbol,
                    error
                )

    def execute(
        self,
        symbol,
        result
    ):

        stake = (
            self.account.balance *
            BINARY_STAKE_PERCENT
        )

        now = datetime.now(
            timezone.utc
        )

        expiry_seconds = (
            BINARY_EXPIRY_MINUTES *
            60
        )

        expiry = datetime.fromtimestamp(
            now.timestamp() +
            expiry_seconds,
            timezone.utc
        )

        trade = Trade(
            market="BINARY",
            symbol=symbol,
            direction=result["signal"],
            entry=float(result["price"]),
            stop_loss=0.0,
            take_profit=0.0,
            amount=stake,
            confidence=float(
                result["confidence"]
            ),
            opened_at=now,
            expiry_time=expiry
        )

        self.account.open_trade(trade)


# ============================================================
# TRADE MONITOR
# ============================================================

class TradeMonitor:

    def __init__(self, account):
        self.account = account

    def check(self):

        for trade in list(
            self.account.open_trades
        ):

            price = MarketData.get_price(
                trade.symbol
            )

            # ------------------------------------------------
            # BINARY
            # ------------------------------------------------

            if trade.market == "BINARY":

                if (
                    trade.expiry_time is not None
                    and datetime.now(
                        timezone.utc
                    ) >= trade.expiry_time
                ):

                    if trade.direction == "BUY":

                        result = (
                            "WIN"
                            if price > trade.entry
                            else "LOSS"
                        )

                    else:

                        result = (
                            "WIN"
                            if price < trade.entry
                            else "LOSS"
                        )

                    self.account.close_trade(
                        trade,
                        price,
                        result
                    )

                continue

            # ------------------------------------------------
            # BUY
            # ------------------------------------------------

            if trade.direction == "BUY":

                if price <= trade.stop_loss:

                    self.account.close_trade(
                        trade,
                        trade.stop_loss
                    )

                elif price >= trade.take_profit:

                    self.account.close_trade(
                        trade,
                        trade.take_profit
                    )

            # ------------------------------------------------
            # SELL
            # ------------------------------------------------

            else:

                if price >= trade.stop_loss:

                    self.account.close_trade(
                        trade,
                        trade.stop_loss
                    )

                elif price <= trade.take_profit:

                    self.account.close_trade(
                        trade,
                        trade.take_profit
                    )


# ============================================================
# UNIFIED BOT
# ============================================================

class UnifiedTradingBot:

    def __init__(self):

        self.account = PaperAccount()

        self.strategy = StrategyEngine()

        self.crypto = MarketEngine(
            "CRYPTO",
            CRYPTO_SYMBOLS,
            self.strategy,
            self.account
        )

        self.forex = MarketEngine(
            "FOREX",
            FOREX_PAIRS,
            self.strategy,
            self.account
        )

        self.binary = BinaryEngine(
            self.strategy,
            self.account
        )

        self.monitor = TradeMonitor(
            self.account
        )

    def run_cycle(self):

        self.monitor.check()

        if self.account.can_trade():

            self.crypto.scan()
            self.forex.scan()
            self.binary.scan()

        self.print_status()

    def print_status(self):

        stats = self.account.statistics()

        logger.info(
            "ACCOUNT | Balance %.2f | "
            "Daily P&L %.2f | "
            "Open %d | "
            "Closed %d | "
            "Wins %d | "
            "Losses %d | "
            "Win Rate %.2f%%",

            stats["balance"],
            stats["daily_pnl"],
            stats["open_trades"],
            stats["closed_trades"],
            stats["wins"],
            stats["losses"],
            stats["win_rate"]
        )


# ============================================================
# GLOBAL BOT
# ============================================================

bot = UnifiedTradingBot()


# ============================================================
# TRADING THREAD
# ============================================================

def trading_loop():

    logger.info(
        "============================================"
    )

    logger.info(
        "UNIFIED PAPER TRADING BOT STARTED"
    )

    logger.info(
        "CRYPTO + FOREX + BINARY"
    )

    logger.info(
        "PAPER TRADING ONLY"
    )

    logger.info(
        "Starting balance: %.2f",
        STARTING_BALANCE
    )

    logger.info(
        "============================================"
    )

    while True:

        try:

            bot.run_cycle()

        except Exception as error:

            logger.exception(
                "Trading loop error: %s",
                error
            )

        time.sleep(
            SCAN_INTERVAL
        )


# ============================================================
# WEB SERVER
# ============================================================

class HealthHandler(
    BaseHTTPRequestHandler
):

    def do_GET(self):

        if self.path == "/health":

            stats = bot.account.statistics()

            response = (
                "{"
                '"status":"ok",'
                f'"balance":{stats["balance"]},'
                f'"open_trades":{stats["open_trades"]},'
                f'"closed_trades":{stats["closed_trades"]},'
                f'"win_rate":{stats["win_rate"]}'
                "}"
            )

            self.send_response(200)

            self.send_header(
                "Content-Type",
                "application/json"
            )

            self.end_headers()

            self.wfile.write(
                response.encode("utf-8")
            )

            return

        if self.path == "/":

            stats = bot.account.statistics()

            html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Unified Paper Trading Bot</title>
</head>
<body>

<h1>Unified Paper Trading Bot</h1>

<p>Status: <strong>RUNNING</strong></p>

<p>Mode: <strong>PAPER TRADING ONLY</strong></p>

<hr>

<p>Balance: {stats["balance"]:.2f}</p>

<p>Daily P&L: {stats["daily_pnl"]:.2f}</p>

<p>Open Trades: {stats["open_trades"]}</p>

<p>Closed Trades: {stats["closed_trades"]}</p>

<p>Wins: {stats["wins"]}</p>

<p>Losses: {stats["losses"]}</p>

<p>Win Rate: {stats["win_rate"]:.2f}%</p>

</body>
</html>
"""

            self.send_response(200)

            self.send_header(
                "Content-Type",
                "text/html"
            )

            self.end_headers()

            self.wfile.write(
                html.encode("utf-8")
            )

            return

        self.send_response(404)
        self.end_headers()

    def log_message(
        self,
        format_string,
        *args
    ):
        return


# ============================================================
# START SERVER
# ============================================================

def start_server():

    server = HTTPServer(
        ("0.0.0.0", PORT),
        HealthHandler
    )

    logger.info(
        "HTTP server listening on port %d",
        PORT
    )

    server.serve_forever()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    trading_thread = threading.Thread(
        target=trading_loop,
        daemon=True
    )

    trading_thread.start()

    start_server()
