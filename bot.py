import time
import random
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from strategy import StrategyEngine


# ============================================================
# CONFIGURATION
# ============================================================

STARTING_BALANCE = 10_000.0

RISK_PER_TRADE = 0.01       # 1% of account
MAX_DAILY_LOSS = 0.03       # 3%
MAX_OPEN_TRADES = 5

SCAN_INTERVAL = 60           # seconds

# Paper binary settings
BINARY_PAYOUT = 0.80
BINARY_EXPIRY_MINUTES = 5


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

    expiry_time: datetime | None = None


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


    # --------------------------------------------------------
    # CAN TRADE?
    # --------------------------------------------------------

    def can_trade(self):

        if len(self.open_trades) >= MAX_OPEN_TRADES:

            logger.warning(
                "Maximum open trades reached."
            )

            return False

        daily_loss_limit = (
            self.starting_balance *
            MAX_DAILY_LOSS
        )

        if self.daily_pnl <= -daily_loss_limit:

            logger.warning(
                "Daily loss limit reached: %.2f",
                self.daily_pnl
            )

            return False

        return True


    # --------------------------------------------------------
    # POSITION SIZE
    # --------------------------------------------------------

    def position_size(
        self,
        entry,
        stop_loss
    ):

        risk_money = (
            self.balance *
            RISK_PER_TRADE
        )

        distance = abs(
            entry - stop_loss
        )

        if distance <= 0:

            return 0

        return risk_money / distance


    # --------------------------------------------------------
    # OPEN TRADE
    # --------------------------------------------------------

    def open_trade(self, trade):

        if not self.can_trade():

            return False

        # Prevent duplicate position
        # on the same market/symbol.

        for existing in self.open_trades:

            if (
                existing.market == trade.market
                and existing.symbol == trade.symbol
            ):

                return False

        self.open_trades.append(trade)

        logger.info(
            "OPEN | %s | %s | %s | Entry %.5f | "
            "Confidence %.2f",
            trade.market,
            trade.symbol,
            trade.direction,
            trade.entry,
            trade.confidence,
        )

        return True


    # --------------------------------------------------------
    # CLOSE TRADE
    # --------------------------------------------------------

    def close_trade(
        self,
        trade,
        exit_price,
        result=None
    ):

        # Binary trade
        if trade.market == "BINARY":

            stake = trade.amount

            if result == "WIN":

                pnl = stake * BINARY_PAYOUT

            else:

                pnl = -stake

        # Normal market trade
        else:

            if trade.direction == "BUY":

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

        if pnl > 0:

            self.wins += 1

        else:

            self.losses += 1


        if trade in self.open_trades:

            self.open_trades.remove(
                trade
            )

        self.closed_trades.append(
            trade
        )

        logger.info(
            "CLOSE | %s | %s | %s | "
            "Exit %.5f | P&L %.2f | Balance %.2f",
            trade.market,
            trade.symbol,
            trade.direction,
            exit_price,
            pnl,
            self.balance,
        )


    # --------------------------------------------------------
    # STATISTICS
    # --------------------------------------------------------

    def statistics(self):

        total = (
            self.wins +
            self.losses
        )

        if total > 0:

            win_rate = (
                self.wins /
                total
            ) * 100

        else:

            win_rate = 0


        return {
            "balance": self.balance,
            "daily_pnl": self.daily_pnl,
            "open_trades": len(
                self.open_trades
            ),
            "closed_trades": len(
                self.closed_trades
            ),
            "wins": self.wins,
            "losses": self.losses,
            "win_rate": win_rate,
        }


# ============================================================
# TEMPORARY MARKET DATA
# ============================================================

class MarketData:

    BASE_PRICES = {

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


    @classmethod
    def get_price(cls, symbol):

        base = cls.BASE_PRICES.get(
            symbol,
            100
        )

        movement = random.uniform(
            -0.002,
            0.002
        )

        return base * (
            1 + movement
        )


    @classmethod
    def get_candles(
        cls,
        symbol,
        count=300
    ):

        base = cls.BASE_PRICES.get(
            symbol,
            100
        )

        prices = []

        price = base

        for _ in range(count):

            movement = random.uniform(
                -0.003,
                0.003
            )

            price *= (
                1 + movement
            )

            prices.append(price)


        candles = []

        for price in prices:

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

            open_price = price * (
                1 + random.uniform(
                    -0.0005,
                    0.0005
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
                "volume": volume,
            })


        return candles


# ============================================================
# MARKET ENGINE
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


    # --------------------------------------------------------
    # SCAN
    # --------------------------------------------------------

    def scan(self):

        for symbol in self.symbols:

            if not self.account.can_trade():

                return

            try:

                candles = MarketData.get_candles(
                    symbol
                )

                import pandas as pd

                df = pd.DataFrame(
                    candles
                )

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
                    "%s scan error for %s: %s",
                    self.market,
                    symbol,
                    error,
                )


    # --------------------------------------------------------
    # EXECUTE PAPER TRADE
    # --------------------------------------------------------

    def execute(
        self,
        symbol,
        result
    ):

        entry = result["price"]

        atr = result.get(
            "atr",
            entry * 0.01
        )

        if not atr or atr <= 0:

            return


        # --------------------------------------------
        # CRYPTO
        # --------------------------------------------

        if self.market == "CRYPTO":

            stop_distance = atr * 1.5
            target_distance = atr * 3.0


        # --------------------------------------------
        # FOREX
        # --------------------------------------------

        elif self.market == "FOREX":

            stop_distance = atr * 1.5
            target_distance = atr * 3.0


        else:

            return


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

            confidence=result["confidence"],

            opened_at=datetime.now(
                timezone.utc
            ),
        )


        self.account.open_trade(
            trade
        )


# ============================================================
# BINARY ENGINE
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

                import pandas as pd

                df = pd.DataFrame(
                    candles
                )

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
                    "Binary error: %s",
                    error
                )


    def execute(
        self,
        symbol,
        result
    ):

        stake = (
            self.account.balance *
            0.005
        )

        now = datetime.now(
            timezone.utc
        )

        expiry = (
            now.timestamp() +
            BINARY_EXPIRY_MINUTES * 60
        )

        trade = Trade(

            market="BINARY",

            symbol=symbol,

            direction=result["signal"],

            entry=result["price"],

            stop_loss=0,

            take_profit=0,

            amount=stake,

            confidence=result["confidence"],

            opened_at=now,

            expiry_time=datetime.fromtimestamp(
                expiry,
                timezone.utc
            ),
        )


        self.account.open_trade(
            trade
        )


# ============================================================
# TRADE MONITOR
# ============================================================

class TradeMonitor:

    def __init__(self, account):

        self.account = account


    def check_trades(self):

        for trade in list(
            self.account.open_trades
        ):

            price = MarketData.get_price(
                trade.symbol
            )


            # =================================================
            # BINARY
            # =================================================

            if trade.market == "BINARY":

                if (
                    trade.expiry_time
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


            # =================================================
            # BUY
            # =================================================

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


            # =================================================
            # SELL
            # =================================================

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


    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    def status(self):

        stats = (
            self.account
            .statistics()
        )


        logger.info(
            "ACCOUNT | Balance %.2f | "
            "Daily P&L %.2f | "
            "Open %d | Closed %d | "
            "Wins %d | Losses %d | "
            "Win Rate %.2f%%",

            stats["balance"],
            stats["daily_pnl"],
            stats["open_trades"],
            stats["closed_trades"],
            stats["wins"],
            stats["losses"],
            stats["win_rate"],
        )


    # --------------------------------------------------------
    # MAIN LOOP
    # --------------------------------------------------------

    def run(self):

        logger.info("=" * 60)

        logger.info(
            "UNIFIED PAPER TRADING BOT"
        )

        logger.info(
            "CRYPTO + FOREX + BINARY"
        )

        logger.info(
            "PAPER MODE ONLY"
        )

        logger.info(
            "Starting balance: %.2f",
            self.account.balance
        )

        logger.info("=" * 60)


        while True:

            try:

                # --------------------------------------------
                # 1. Monitor existing trades
                # --------------------------------------------

                self.monitor.check_trades()


                # --------------------------------------------
                # 2. Find new trades
                # --------------------------------------------

                if self.account.can_trade():

                    self.crypto.scan()

                    self.forex.scan()

                    self.binary.scan()


                # --------------------------------------------
                # 3. Display statistics
                # --------------------------------------------

                self.status()


                # --------------------------------------------
                # 4. Wait
                # --------------------------------------------

                time.sleep(
                    SCAN_INTERVAL
                )


            except KeyboardInterrupt:

                logger.info(
                    "Bot stopped manually."
                )

                break


            except Exception as error:

                logger.exception(
                    "Main loop error: %s",
                    error
                )

                time.sleep(10)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    bot = UnifiedTradingBot()

    bot.run()
