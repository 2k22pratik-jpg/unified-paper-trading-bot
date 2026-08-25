"""
UNIFIED PAPER TRADING BOT
Crypto + Forex + Binary

PAPER TRADING ONLY
"""

import time
import random
import logging
from dataclasses import dataclass
from datetime import datetime, timezone


# ============================================================
# CONFIGURATION
# ============================================================

STARTING_BALANCE = 10000.0

MAX_RISK_PER_TRADE = 0.01       # 1%
MAX_DAILY_LOSS = 0.03           # 3%
MAX_OPEN_TRADES = 5

SCAN_INTERVAL = 60              # seconds


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
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("UnifiedBot")


# ============================================================
# DATA STRUCTURES
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


# ============================================================
# PAPER ACCOUNT
# ============================================================

class PaperAccount:

    def __init__(self, balance=STARTING_BALANCE):
        self.starting_balance = balance
        self.balance = balance
        self.equity = balance

        self.open_trades = []
        self.closed_trades = []

        self.daily_pnl = 0.0

    def can_trade(self):

        if len(self.open_trades) >= MAX_OPEN_TRADES:
            return False

        daily_loss_limit = self.starting_balance * MAX_DAILY_LOSS

        if self.daily_pnl <= -daily_loss_limit:
            logger.warning("Daily loss limit reached.")
            return False

        return True

    def position_size(self, entry, stop_loss):

        risk_money = self.balance * MAX_RISK_PER_TRADE

        distance = abs(entry - stop_loss)

        if distance <= 0:
            return 0

        return risk_money / distance

    def add_trade(self, trade):

        if not self.can_trade():
            return False

        self.open_trades.append(trade)

        logger.info(
            "OPEN | %s | %s | %s | Entry %.5f",
            trade.market,
            trade.symbol,
            trade.direction,
            trade.entry,
        )

        return True

    def close_trade(self, trade, exit_price):

        if trade.direction == "BUY":
            pnl = (exit_price - trade.entry) * trade.amount
        else:
            pnl = (trade.entry - exit_price) * trade.amount

        self.balance += pnl
        self.equity = self.balance

        self.daily_pnl += pnl

        if trade in self.open_trades:
            self.open_trades.remove(trade)

        self.closed_trades.append(trade)

        logger.info(
            "CLOSE | %s | %s | P&L %.2f | Balance %.2f",
            trade.market,
            trade.symbol,
            pnl,
            self.balance,
        )


# ============================================================
# MARKET DATA PLACEHOLDER
# ============================================================

class MarketData:

    @staticmethod
    def get_price(symbol):

        """
        Temporary paper-price generator.

        This will later be replaced with live market
        data/API connections.
        """

        base_prices = {
            "BTCUSDT": 110000,
            "ETHUSDT": 4000,
            "BNBUSDT": 800,
            "SOLUSDT": 200,

            "EURUSD": 1.17,
            "GBPUSD": 1.35,
            "USDJPY": 148,
            "USDCHF": 0.80,
            "AUDUSD": 0.65,
            "USDCAD": 1.38,
            "NZDUSD": 0.59,
            "EURGBP": 0.87,
            "EURJPY": 173,
            "GBPJPY": 200,
        }

        price = base_prices.get(symbol, 100)

        movement = random.uniform(-0.002, 0.002)

        return price * (1 + movement)


# ============================================================
# STRATEGY ENGINE
# ============================================================

class StrategyEngine:

    def analyze(self, market, symbol):

        price = MarketData.get_price(symbol)

        # Temporary signal generator.
        # The real multi-indicator strategy will replace this.

        score = random.uniform(-1, 1)

        if score > 0.55:

            return {
                "signal": "BUY",
                "price": price,
                "confidence": score,
            }

        if score < -0.55:

            return {
                "signal": "SELL",
                "price": price,
                "confidence": abs(score),
            }

        return {
            "signal": "HOLD",
            "price": price,
            "confidence": 0,
        }


# ============================================================
# CRYPTO ENGINE
# ============================================================

class CryptoEngine:

    def __init__(self, strategy, account):
        self.strategy = strategy
        self.account = account

    def scan(self):

        for symbol in CRYPTO_SYMBOLS:

            result = self.strategy.analyze("CRYPTO", symbol)

            if result["signal"] == "HOLD":
                continue

            self.execute(symbol, result)

    def execute(self, symbol, result):

        entry = result["price"]

        if result["signal"] == "BUY":

            stop_loss = entry * 0.99
            take_profit = entry * 1.02

        else:

            stop_loss = entry * 1.01
            take_profit = entry * 0.98

        amount = self.account.position_size(
            entry,
            stop_loss
        )

        trade = Trade(
            market="CRYPTO",
            symbol=symbol,
            direction=result["signal"],
            entry=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            amount=amount,
            confidence=result["confidence"],
            opened_at=datetime.now(timezone.utc),
        )

        self.account.add_trade(trade)


# ============================================================
# FOREX ENGINE
# ============================================================

class ForexEngine:

    def __init__(self, strategy, account):
        self.strategy = strategy
        self.account = account

    def scan(self):

        for symbol in FOREX_PAIRS:

            result = self.strategy.analyze("FOREX", symbol)

            if result["signal"] == "HOLD":
                continue

            self.execute(symbol, result)

    def execute(self, symbol, result):

        entry = result["price"]

        if result["signal"] == "BUY":

            stop_loss = entry * 0.995
            take_profit = entry * 1.01

        else:

            stop_loss = entry * 1.005
            take_profit = entry * 0.99

        amount = self.account.position_size(
            entry,
            stop_loss
        )

        trade = Trade(
            market="FOREX",
            symbol=symbol,
            direction=result["signal"],
            entry=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            amount=amount,
            confidence=result["confidence"],
            opened_at=datetime.now(timezone.utc),
        )

        self.account.add_trade(trade)


# ============================================================
# BINARY PAPER ENGINE
# ============================================================

class BinaryEngine:

    def __init__(self, strategy, account):
        self.strategy = strategy
        self.account = account

    def scan(self):

        for symbol in BINARY_SYMBOLS:

            result = self.strategy.analyze(
                "BINARY",
                symbol
            )

            if result["signal"] == "HOLD":
                continue

            self.execute(symbol, result)

    def execute(self, symbol, result):

        entry = result["price"]

        # Fixed paper stake.
        stake = self.account.balance * 0.005

        trade = Trade(
            market="BINARY",
            symbol=symbol,
            direction=result["signal"],
            entry=entry,
            stop_loss=0,
            take_profit=0,
            amount=stake,
            confidence=result["confidence"],
            opened_at=datetime.now(timezone.utc),
        )

        self.account.add_trade(trade)


# ============================================================
# BOT
# ============================================================

class UnifiedTradingBot:

    def __init__(self):

        self.account = PaperAccount()

        self.strategy = StrategyEngine()

        self.crypto = CryptoEngine(
            self.strategy,
            self.account
        )

        self.forex = ForexEngine(
            self.strategy,
            self.account
        )

        self.binary = BinaryEngine(
            self.strategy,
            self.account
        )

    def status(self):

        logger.info(
            "ACCOUNT | Balance: %.2f | Equity: %.2f | "
            "Open: %d | Closed: %d | Daily P&L: %.2f",
            self.account.balance,
            self.account.equity,
            len(self.account.open_trades),
            len(self.account.closed_trades),
            self.account.daily_pnl,
        )

    def run(self):

        logger.info("=" * 60)
        logger.info("UNIFIED PAPER TRADING BOT STARTED")
        logger.info("CRYPTO + FOREX + BINARY")
        logger.info("PAPER TRADING MODE")
        logger.info("=" * 60)

        while True:

            try:

                if self.account.can_trade():

                    self.crypto.scan()
                    self.forex.scan()
                    self.binary.scan()

                self.status()

                time.sleep(SCAN_INTERVAL)

            except KeyboardInterrupt:

                logger.info("Bot stopped.")
                break

            except Exception as error:

                logger.exception(
                    "Bot error: %s",
                    error
                )

                time.sleep(10)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    bot = UnifiedTradingBot()

    bot.run()
