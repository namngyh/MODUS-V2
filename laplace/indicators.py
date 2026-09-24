"""Cac nhom indicator TA-Lib: candles, cycles, momentum, overlap, statistic,
volatility, volume.

Moi indicator duoc khai bao bang mot `Spec` gom: ten ham TA-Lib, chuoi dau vao,
tham so, va - quan trong nhat - kieu chuan hoa cho *tung output*. Nho vay them mot
indicator moi chi la them mot dong, va khong bao gio quen mat buoc doi don vi.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import talib

from .config import FeatureConfig
from .norms import NormContext, apply_norm, make_context
from .utils import prefix, safe_log


@dataclass(frozen=True)
class Spec:
    func: str                              # ten ham trong talib
    inputs: tuple[str, ...]                # cot dau vao, dung thu tu TA-Lib yeu cau
    norms: tuple[str, ...]                 # mot kieu chuan hoa cho moi output
    params: dict = field(default_factory=dict)
    tag: str = ""                          # tien to cot; mac dinh la ten ham
    out_names: tuple[str, ...] = ()        # ten hau to khi ham tra nhieu output
    slope: bool = False                    # them do doc log(x_t / x_{t-1})

    @property
    def label(self) -> str:
        return self.tag or self.func


def _column_names(spec: Spec) -> list[str]:
    if len(spec.norms) == 1:
        return [spec.label]
    names = spec.out_names or tuple(str(i) for i in range(len(spec.norms)))
    return [f"{spec.label}_{n}" for n in names]


def run_specs(specs: list[Spec], df: pd.DataFrame, ctx: NormContext) -> pd.DataFrame:
    arrays = {c: df[c].to_numpy(dtype="float64")
              for c in ("open", "high", "low", "close", "volume")}
    cols: dict[str, np.ndarray] = {}

    for spec in specs:
        fn = getattr(talib, spec.func)
        try:
            raw = fn(*[arrays[i] for i in spec.inputs], **spec.params)
        except Exception as exc:                      # tham so xau / khong du du lieu
            raise RuntimeError(f"{spec.label} that bai: {exc}") from exc
        outs = raw if isinstance(raw, tuple) else (raw,)
        names = _column_names(spec)

        for name, out, kind in zip(names, outs, spec.norms, strict=True):
            cols[name] = apply_norm(kind, out, ctx)
            if spec.slope:
                # Do doc cua duong trung binh: xu the cua chinh indicator, doc lap
                # voi khoang cach gia-den-duong ma cot goc da nam bat.
                lg = safe_log(out)
                slope = lg - np.roll(lg, 1)
                slope[0] = np.nan
                cols[f"{name}_slope"] = slope

    return pd.DataFrame(cols, index=df.index)


# --------------------------------------------------------------------------- #
# Overlap studies - duong bao / trung binh truot (tat ca deu la muc gia)
# --------------------------------------------------------------------------- #
_MA_FUNCS = ("SMA", "EMA", "WMA", "DEMA", "TEMA", "TRIMA", "KAMA", "T3", "MIDPOINT")


def overlap_specs(cfg: FeatureConfig) -> list[Spec]:
    specs: list[Spec] = []
    for p in cfg.all_periods:
        for f in _MA_FUNCS:
            specs.append(Spec(f, ("close",), ("price",), {"timeperiod": p}, f"{f}{p}", slope=True))
        specs.append(Spec("MIDPRICE", ("high", "low"), ("price",),
                          {"timeperiod": p}, f"MIDPRICE{p}"))
    for p in cfg.mid_periods:
        specs.append(Spec("BBANDS", ("close",), ("price", "price", "price"),
                          {"timeperiod": p, "nbdevup": 2.0, "nbdevdn": 2.0},
                          f"BBANDS{p}", ("upper", "middle", "lower")))
        specs.append(Spec("ACCBANDS", ("high", "low", "close"), ("price", "price", "price"),
                          {"timeperiod": p}, f"ACCBANDS{p}", ("upper", "middle", "lower")))
    specs += [
        Spec("MAMA", ("close",), ("price", "price"), {}, "MAMA", ("mama", "fama"), slope=True),
        Spec("HT_TRENDLINE", ("close",), ("price",), {}, "HT_TRENDLINE", slope=True),
        Spec("SAR", ("high", "low"), ("price",), {"acceleration": 0.02, "maximum": 0.2}, "SAR"),
        # SAREXT tra ve gia tri am khi o chieu ban -> tach thanh muc va chieu.
        Spec("SAREXT", ("high", "low"), ("absprice",), {}, "SAREXT"),
        Spec("SAREXT", ("high", "low"), ("sign",), {}, "SAREXT_side"),
    ]
    return specs


# --------------------------------------------------------------------------- #
# Momentum
# --------------------------------------------------------------------------- #
def momentum_specs(cfg: FeatureConfig) -> list[Spec]:
    specs: list[Spec] = []
    for p in cfg.all_periods:
        specs += [
            Spec("RSI", ("close",), ("pct100",), {"timeperiod": p}, f"RSI{p}"),
            Spec("CMO", ("close",), ("signed100",), {"timeperiod": p}, f"CMO{p}"),
            Spec("MOM", ("close",), ("pdiff",), {"timeperiod": p}, f"MOM{p}"),
            Spec("ROCP", ("close",), ("pass",), {"timeperiod": p}, f"ROCP{p}"),
            Spec("ROCR100", ("close",), ("pct",), {"timeperiod": p}, f"ROCR100{p}"),
            Spec("CCI", ("high", "low", "close"), ("div100",), {"timeperiod": p}, f"CCI{p}"),
            Spec("WILLR", ("high", "low", "close"), ("pct100n",), {"timeperiod": p}, f"WILLR{p}"),
            Spec("MFI", ("high", "low", "close", "volume"), ("pct100",),
                 {"timeperiod": p}, f"MFI{p}"),
            Spec("ADX", ("high", "low", "close"), ("pct100",), {"timeperiod": p}, f"ADX{p}"),
            Spec("ADXR", ("high", "low", "close"), ("pct100",), {"timeperiod": p}, f"ADXR{p}"),
            Spec("DX", ("high", "low", "close"), ("pct100",), {"timeperiod": p}, f"DX{p}"),
            Spec("PLUS_DI", ("high", "low", "close"), ("pct100",),
                 {"timeperiod": p}, f"PLUS_DI{p}"),
            Spec("MINUS_DI", ("high", "low", "close"), ("pct100",),
                 {"timeperiod": p}, f"MINUS_DI{p}"),
            Spec("PLUS_DM", ("high", "low"), ("pdiff",), {"timeperiod": p}, f"PLUS_DM{p}"),
            Spec("MINUS_DM", ("high", "low"), ("pdiff",), {"timeperiod": p}, f"MINUS_DM{p}"),
            Spec("AROON", ("high", "low"), ("pct100", "pct100"),
                 {"timeperiod": p}, f"AROON{p}", ("down", "up")),
            Spec("AROONOSC", ("high", "low"), ("signed100",), {"timeperiod": p}, f"AROONOSC{p}"),
            Spec("IMI", ("open", "close"), ("pct100",), {"timeperiod": p}, f"IMI{p}"),
            Spec("STOCHRSI", ("close",), ("pct100", "pct100"),
                 {"timeperiod": p}, f"STOCHRSI{p}", ("k", "d")),
        ]
    for p in cfg.mid_periods + cfg.slow_periods:
        specs.append(Spec("TRIX", ("close",), ("pct",), {"timeperiod": p}, f"TRIX{p}"))

    # Cac cap nhanh/cham cho ho MACD - quet nhieu ty le thoi gian.
    for fast, slow, sig in ((6, 12, 5), (12, 26, 9), (24, 51, 18), (51, 102, 36)):
        specs += [
            Spec("MACD", ("close",), ("pdiff", "pdiff", "pdiff"),
                 {"fastperiod": fast, "slowperiod": slow, "signalperiod": sig},
                 f"MACD_{fast}_{slow}", ("macd", "signal", "hist")),
            Spec("APO", ("close",), ("pdiff",),
                 {"fastperiod": fast, "slowperiod": slow}, f"APO_{fast}_{slow}"),
            Spec("PPO", ("close",), ("pct",),
                 {"fastperiod": fast, "slowperiod": slow}, f"PPO_{fast}_{slow}"),
        ]
    specs += [
        Spec("MACDFIX", ("close",), ("pdiff", "pdiff", "pdiff"),
             {"signalperiod": 9}, "MACDFIX", ("macd", "signal", "hist")),
        Spec("BOP", ("open", "high", "low", "close"), ("pass",), {}, "BOP"),
        Spec("ULTOSC", ("high", "low", "close"), ("pct100",),
             {"timeperiod1": 7, "timeperiod2": 14, "timeperiod3": 28}, "ULTOSC"),
        Spec("ULTOSC", ("high", "low", "close"), ("pct100",),
             {"timeperiod1": 12, "timeperiod2": 51, "timeperiod3": 102}, "ULTOSCslow"),
    ]
    for fk, sk, sd in ((5, 3, 3), (14, 3, 3), (51, 5, 5)):
        specs += [
            Spec("STOCH", ("high", "low", "close"), ("pct100", "pct100"),
                 {"fastk_period": fk, "slowk_period": sk, "slowd_period": sd},
                 f"STOCH{fk}", ("k", "d")),
            Spec("STOCHF", ("high", "low", "close"), ("pct100", "pct100"),
                 {"fastk_period": fk, "fastd_period": sd}, f"STOCHF{fk}", ("k", "d")),
        ]
    return specs


# --------------------------------------------------------------------------- #
# Cycles (Hilbert transform)
# --------------------------------------------------------------------------- #
def cycle_specs(cfg: FeatureConfig) -> list[Spec]:
    return [
        Spec("HT_DCPERIOD", ("close",), ("dcperiod",), {}, "HT_DCPERIOD"),
        Spec("HT_DCPHASE", ("close",), ("deg180",), {}, "HT_DCPHASE"),
        Spec("HT_PHASOR", ("close",), ("pdiff", "pdiff"), {}, "HT_PHASOR",
             ("inphase", "quadrature")),
        Spec("HT_SINE", ("close",), ("pass", "pass"), {}, "HT_SINE", ("sine", "leadsine")),
        Spec("HT_TRENDMODE", ("close",), ("pass",), {}, "HT_TRENDMODE"),
    ]


# --------------------------------------------------------------------------- #
# Statistic
# --------------------------------------------------------------------------- #
def statistic_specs(cfg: FeatureConfig) -> list[Spec]:
    specs: list[Spec] = []
    for p in cfg.all_periods:
        specs += [
            Spec("LINEARREG", ("close",), ("price",), {"timeperiod": p}, f"LINEARREG{p}"),
            Spec("LINEARREG_ANGLE", ("close",), ("deg90",),
                 {"timeperiod": p}, f"LINEARREG_ANGLE{p}"),
            Spec("LINEARREG_SLOPE", ("close",), ("pdiff",),
                 {"timeperiod": p}, f"LINEARREG_SLOPE{p}"),
            Spec("LINEARREG_INTERCEPT", ("close",), ("price",),
                 {"timeperiod": p}, f"LINEARREG_INTERCEPT{p}"),
            Spec("TSF", ("close",), ("price",), {"timeperiod": p}, f"TSF{p}"),
            Spec("STDDEV", ("close",), ("pdiff",), {"timeperiod": p}, f"STDDEV{p}"),
            Spec("VAR", ("close",), ("pvar",), {"timeperiod": p}, f"VAR{p}"),
            Spec("AVGDEV", ("close",), ("pdiff",), {"timeperiod": p}, f"AVGDEV{p}"),
            # BETA/CORREL giua high va low do "do chat" cua bien do trong bar.
            Spec("BETA", ("high", "low"), ("pass",), {"timeperiod": p}, f"BETA{p}"),
            Spec("CORREL", ("high", "low"), ("pass",), {"timeperiod": p}, f"CORREL{p}"),
        ]
    return specs


# --------------------------------------------------------------------------- #
# Volatility / Volume / Price transform
# --------------------------------------------------------------------------- #
def volatility_specs(cfg: FeatureConfig) -> list[Spec]:
    specs: list[Spec] = [Spec("TRANGE", ("high", "low", "close"), ("pdiff",), {}, "TRANGE")]
    for p in cfg.all_periods:
        specs += [
            Spec("ATR", ("high", "low", "close"), ("pdiff",), {"timeperiod": p}, f"ATR{p}"),
            Spec("NATR", ("high", "low", "close"), ("pct",), {"timeperiod": p}, f"NATR{p}"),
        ]
    return specs


def volume_specs(cfg: FeatureConfig) -> list[Spec]:
    specs: list[Spec] = [
        # AD va OBV la tong tich luy tu dau chuoi -> chi lay sai phan (xem norms.py).
        Spec("AD", ("high", "low", "close", "volume"), ("flow_diff",), {}, "AD"),
        Spec("OBV", ("close", "volume"), ("flow_diff",), {}, "OBV"),
    ]
    for fast, slow in ((3, 10), (12, 51), (51, 102)):
        specs.append(Spec("ADOSC", ("high", "low", "close", "volume"), ("flow",),
                          {"fastperiod": fast, "slowperiod": slow}, f"ADOSC_{fast}_{slow}"))
    return specs


def price_transform_specs(cfg: FeatureConfig) -> list[Spec]:
    return [
        Spec("AVGPRICE", ("open", "high", "low", "close"), ("price",), {}, "AVGPRICE"),
        Spec("MEDPRICE", ("high", "low"), ("price",), {}, "MEDPRICE"),
        Spec("TYPPRICE", ("high", "low", "close"), ("price",), {}, "TYPPRICE"),
        Spec("WCLPRICE", ("high", "low", "close"), ("price",), {}, "WCLPRICE"),
    ]


# --------------------------------------------------------------------------- #
# Candlestick patterns
# --------------------------------------------------------------------------- #
def candle_specs(cfg: FeatureConfig) -> list[Spec]:
    names = talib.get_function_groups()["Pattern Recognition"]
    return [Spec(n, ("open", "high", "low", "close"), ("signed100",), {}, n) for n in names]


GROUP_BUILDERS = {
    "overlap": overlap_specs,
    "momentum": momentum_specs,
    "cycles": cycle_specs,
    "statistic": statistic_specs,
    "volatility": volatility_specs,
    "volume": volume_specs,
    "price": price_transform_specs,
    "candles": candle_specs,
}


def build_group(name: str, df: pd.DataFrame, cfg: FeatureConfig,
                ctx: NormContext | None = None) -> pd.DataFrame:
    ctx = ctx if ctx is not None else make_context(df)
    out = run_specs(GROUP_BUILDERS[name](cfg), df, ctx)
    return prefix(out, name)
