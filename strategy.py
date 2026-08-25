import pandas as pd
import numpy as np


class StrategyEngine:

    def __init__(self):
        self.min_confidence = 0.65

    # =========================================================
    # INDICATORS
    # =========================================================

    @staticmethod
    def ema(series, period):
        return series.ewm(
            span=period,
            adjust=False
        ).mean()

    @staticmethod
    def rsi(series, period=14):

        delta = series.diff()

        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.ewm(
            alpha=1 / period,
            adjust=False
        ).mean()

        avg_loss = loss.ewm(
            alpha=1 / period,
            adjust=False
        ).mean()

        rs = avg_gain / avg_loss.replace(0, np.nan)

        return 100 - (100 / (1 + rs))

    @staticmethod
    def macd(series):

        ema12 = series.ewm(
            span=12,
            adjust=False
        ).mean()

        ema26 = series.ewm(
            span=26,
            adjust=False
        ).mean()

        macd_line = ema12 - ema26

        signal = macd_line.ewm(
            span=9,
            adjust=False
        ).mean()

        histogram = macd_line - signal

        return macd_line, signal, histogram

    @staticmethod
    def atr(df, period=14):

        high_low = df["high"] - df["low"]

        high_close = (
            df["high"] -
            df["close"].shift()
        ).abs()

        low_close = (
            df["low"] -
            df["close"].shift()
        ).abs()

        true_range = pd.concat(
            [
                high_low,
                high_close,
                low_close
            ],
            axis=1
        ).max(axis=1)

        return true_range.rolling(period).mean()

    # =========================================================
    # PREPARE DATA
    # =========================================================

    def prepare_data(self, df):

        df = df.copy()

        required = [
            "open",
            "high",
            "low",
            "close",
            "volume"
        ]

        for column in required:

            if column not in df.columns:
                raise ValueError(
                    f"Missing column: {column}"
                )

        df["ema20"] = self.ema(
            df["close"],
            20
        )

        df["ema50"] = self.ema(
            df["close"],
            50
        )

        df["ema200"] = self.ema(
            df["close"],
            200
        )

        df["rsi"] = self.rsi(
            df["close"],
            14
        )

        (
            df["macd"],
            df["macd_signal"],
            df["macd_hist"]
        ) = self.macd(df["close"])

        df["atr"] = self.atr(
            df,
            14
        )

        df["volume_avg"] = (
            df["volume"]
            .rolling(20)
            .mean()
        )

        return df

    # =========================================================
    # TREND ANALYSIS
    # =========================================================

    @staticmethod
    def trend_score(row):

        score = 0

        if row["close"] > row["ema20"]:
            score += 1
        else:
            score -= 1

        if row["ema20"] > row["ema50"]:
            score += 1
        else:
            score -= 1

        if row["ema50"] > row["ema200"]:
            score += 1
        else:
            score -= 1

        return score

    # =========================================================
    # SIGNAL GENERATION
    # =========================================================

    def generate_signal(self, df):

        df = self.prepare_data(df)

        if len(df) < 220:
            return {
                "signal": "HOLD",
                "confidence": 0,
                "reason": "Not enough candle data"
            }

        row = df.iloc[-1]

        score = 0
        reasons = []

        # -----------------------------------------------------
        # TREND
        # -----------------------------------------------------

        trend = self.trend_score(row)

        if trend >= 2:

            score += 3

            reasons.append(
                "Strong bullish trend"
            )

        elif trend <= -2:

            score -= 3

            reasons.append(
                "Strong bearish trend"
            )

        # -----------------------------------------------------
        # RSI
        # -----------------------------------------------------

        if 50 <= row["rsi"] <= 70:

            score += 2

            reasons.append(
                "Bullish RSI momentum"
            )

        elif 30 <= row["rsi"] < 50:

            score -= 2

            reasons.append(
                "Bearish RSI momentum"
            )

        # Avoid buying extremely overbought markets.

        if row["rsi"] > 75:

            score -= 1

            reasons.append(
                "RSI overbought"
            )

        if row["rsi"] < 25:

            score += 1

            reasons.append(
                "RSI oversold"
            )

        # -----------------------------------------------------
        # MACD
        # -----------------------------------------------------

        if row["macd"] > row["macd_signal"]:

            score += 2

            reasons.append(
                "MACD bullish"
            )

        else:

            score -= 2

            reasons.append(
                "MACD bearish"
            )

        # -----------------------------------------------------
        # VOLUME
        # -----------------------------------------------------

        if row["volume"] > row["volume_avg"]:

            if score > 0:

                score += 1

                reasons.append(
                    "Volume confirmation"
                )

            elif score < 0:

                score -= 1

                reasons.append(
                    "Bearish volume confirmation"
                )

        # -----------------------------------------------------
        # NORMALIZE SCORE
        # -----------------------------------------------------

        max_score = 8

        confidence = min(
            abs(score) / max_score,
            1.0
        )

        # -----------------------------------------------------
        # FINAL SIGNAL
        # -----------------------------------------------------

        if confidence < self.min_confidence:

            signal = "HOLD"

        elif score > 0:

            signal = "BUY"

        else:

            signal = "SELL"

        return {
            "signal": signal,
            "confidence": round(
                confidence,
                3
            ),
            "score": score,
            "price": float(row["close"]),
            "rsi": round(
                float(row["rsi"]),
                2
            ),
            "atr": float(row["atr"]),
            "reason": ", ".join(reasons)
        }


# =============================================================
# SIMPLE TEST
# =============================================================

if __name__ == "__main__":

    np.random.seed(42)

    candles = 300

    prices = (
        100 +
        np.cumsum(
            np.random.normal(
                0,
                0.5,
                candles
            )
        )
    )

    data = pd.DataFrame({
        "open": prices,
        "high": prices + 1,
        "low": prices - 1,
        "close": prices,
        "volume": np.random.randint(
            100,
            1000,
            candles
        )
    })

    strategy = StrategyEngine()

    result = strategy.generate_signal(
        data
    )

    print("\nSTRATEGY TEST")
    print("-" * 40)

    for key, value in result.items():
        print(
            f"{key}: {value}"
  )
