"""Cau hinh cho pipeline sinh dac trung."""

from __future__ import annotations

from dataclasses import dataclass

# Mot phien VN30F: 09:00-11:30 (150 phut) + 13:00-14:45 (105 phut).
SESSION_MINUTES = 255


@dataclass
class FeatureConfig:
    """Tham so dieu khien toan bo pipeline.

    Moi nhom dac trung deu bat/tat duoc de chay ablation study: huan luyen lai
    mo hinh voi `use_candles=False` cho biet nhom nen co dong gop that hay khong.
    """

    # --- nguon du lieu ---
    csv_path: str = "ohlc_export.csv"
    symbol: str | None = None            # None = lay toan bo (file hien tai chi co VN30F1M)
    session_end: str = "14:45:00"        # bar ATC; bar sau gio nay bi coi la nhieu
    # Kich thuoc bar dich. Loader gop du lieu nguon ve day neu nguon min hon (xem
    # spec 001): file hien tai la bar 1 phut, giao dich thuc te tren nen 5 phut.
    bar_minutes: int = 5

    # --- bat/tat tung nhom ---
    use_base: bool = True                # bien doi co ban tu OHLC
    # Mau nen tat theo yeu cau. Bat lai bang FeatureConfig(use_candles=True) hoac
    # co --candles neu muon do dong gop cua nhom nay.
    use_candles: bool = False            # 61 mau nen TA-Lib
    use_cycles: bool = True              # Hilbert transform
    use_momentum: bool = True
    use_overlap: bool = True
    use_statistic: bool = True
    use_volatility: bool = True
    use_volume: bool = True
    use_orderflow: bool = True           # tu BUY_VOL/SELL_VOL (ngoai TA-Lib)
    use_session: bool = True             # thoi gian trong phien, ngay den dao han
    use_bots: bool = True                # dau vao cua hai bot AFL trong bot/

    # Tin hieu bot khong phai dac trung (xem bots.py) nhung van tinh cung mot luot
    # vi dung chung phan lon phep tinh trung gian.
    emit_bot_signals: bool = True

    # --- tam nhin da khung thoi gian, tinh bang PHUT ---
    # Khai bang phut chu khong bang so bar la co y: doi do phan giai du lieu thi so
    # bar phai doi theo, con y nghia "mot phien" thi khong. Truoc day khai thang
    # bang so bar, va khi file du lieu doi tu 5 phut sang 1 phut thi moi hang so
    # lech 5 lan ma khong test nao do duoc.
    fast_horizons: tuple[int, ...] = (30, 60)                             # 30 phut, 1 gio
    mid_horizons: tuple[int, ...] = (120, SESSION_MINUTES)                # 2 gio, 1 phien
    slow_horizons: tuple[int, ...] = (2 * SESSION_MINUTES, 5 * SESSION_MINUTES)

    # --- lop tinh dung (spec 006) ---
    stationarize: bool = True            # tat de tai lap X truoc spec 006
    rolling_horizon: int = 5 * SESSION_MINUTES   # cua so z-score cuon: 1 tuan, tinh bang phut
    pit_dof: float = 5.0                 # bac tu do Student-t khi ep duoi
    log_floor: float = 1e-5              # san truoc khi log muc bien dong

    # --- chuan hoa ---
    clip_sigma: float = 8.0              # cat duoi ngoai lai sau khi scale (don vi sigma)
    scaler: str = "robust"               # "robust" | "standard" | "none"

    # --- chia tap theo thoi gian (khong shuffle) ---
    train_end: str = "2024-06-30"
    valid_end: str = "2025-06-30"

    # --- dong goi cho model ---
    window: int = 64                     # do dai chuoi dua vao LSTM/TCN/Transformer
    stride: int = 1
    # Cua so 64 bar dai hon mot phien (51 bar) nen mac dinh phai cho bac qua dem;
    # cac dac trung session (bar_gap, day_progress) noi cho mo hinh biet cho nao la
    # ranh gioi. Dat False neu muon cua so nam gon trong phien - khi do window <= 42.
    cross_day: bool = True

    # ------------------------------------------------------------------ #
    # Chu ky suy ra tu tam nhin. Khong khai truc tiep de khong the lech.
    # ------------------------------------------------------------------ #
    def _bars(self, horizons: tuple[int, ...]) -> tuple[int, ...]:
        return tuple(h // self.bar_minutes for h in horizons)

    @property
    def fast_periods(self) -> tuple[int, ...]:
        return self._bars(self.fast_horizons)

    @property
    def mid_periods(self) -> tuple[int, ...]:
        return self._bars(self.mid_horizons)

    @property
    def slow_periods(self) -> tuple[int, ...]:
        return self._bars(self.slow_horizons)

    @property
    def all_periods(self) -> tuple[int, ...]:
        return tuple(sorted(set(self.fast_periods + self.mid_periods + self.slow_periods)))

    @property
    def session_bars(self) -> int:
        return SESSION_MINUTES // self.bar_minutes

    @property
    def rolling_window(self) -> int:
        return self.rolling_horizon // self.bar_minutes

    @property
    def embargo_bars(self) -> int:
        """Vung dem giua cac tap: hai phien, du de cua so va indicator dai het chong lan."""
        return 2 * self.session_bars

    @property
    def return_horizons(self) -> tuple[int, ...]:
        """Vai bar dau tien (dong luc tuc thoi) cong bon tam nhin ngan nhat."""
        return (1, 2, 3) + self.all_periods[:4]

    @property
    def vol_windows(self) -> tuple[int, ...]:
        """Cua so uoc luong bien dong: 1 gio, 1 phien, 1 tuan."""
        return (self.fast_periods[-1], self.session_bars, self.slow_periods[-1])

    def describe_periods(self) -> str:
        """Chu ky kem y nghia wall-clock - in ra de nhin thay ngay khi bi lech."""
        names = {30: "30 phut", 60: "1 gio", 120: "2 gio", SESSION_MINUTES: "1 phien",
                 2 * SESSION_MINUTES: "2 phien", 5 * SESSION_MINUTES: "1 tuan"}
        parts = [f"{p} bar = {names.get(p * self.bar_minutes, f'{p * self.bar_minutes} phut')}"
                 for p in self.all_periods]
        return f"bar {self.bar_minutes} phut | " + ", ".join(parts)
