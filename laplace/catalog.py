"""Sinh danh muc dac trung tu chinh cac Spec trong code.

Viet tay danh sach 506 dac trung ra file markdown thi hom sau no se lech: them mot
chu ky vao FeatureConfig la sinh them vai chuc cot ma khong ai nho cap nhat tai lieu.
Module nay doc nguoc lai tu indicators.py va tu bang mo ta o duoi, nen danh muc luon
khop voi thu pipeline thuc su tao ra.

Khac voi phan con lai cua package, cac chuoi mo ta o day co dau tieng Viet: chung la
noi dung tai lieu doc cho nguoi, khong phai comment trong code.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace

import pandas as pd

from .config import FeatureConfig
from .indicators import GROUP_BUILDERS, _column_names
from .stationarity import classify

# --------------------------------------------------------------------------- #
# Y nghia cua tung ham TA-Lib
# --------------------------------------------------------------------------- #
FUNC_GLOSS = {
    # Overlap studies
    "SMA": "Trung bình động giản đơn",
    "EMA": "Trung bình động luỹ thừa",
    "WMA": "Trung bình động trọng số tuyến tính",
    "DEMA": "Trung bình động kép — bám giá sát hơn EMA cùng chu kỳ",
    "TEMA": "Trung bình động ba lớp — độ trễ thấp nhất họ EMA",
    "TRIMA": "Trung bình động tam giác — trọng số nặng ở giữa cửa sổ",
    "KAMA": "Trung bình động thích nghi Kaufman — nhanh khi xu thế sạch, chậm khi đi ngang",
    "T3": "Trung bình động T3 Tillson — mượt hơn EMA với cùng độ trễ",
    "MIDPOINT": "Trung điểm giữa giá đóng cửa cao nhất và thấp nhất trong cửa sổ",
    "MIDPRICE": "Trung điểm giữa đỉnh và đáy trong cửa sổ",
    "BBANDS": "Dải Bollinger — trung bình cộng/trừ 2 độ lệch chuẩn",
    "ACCBANDS": "Dải Acceleration — biên độ giãn theo (H−L)/(H+L)",
    "MAMA": "MESA Adaptive MA — chu kỳ tự thích nghi theo Hilbert transform",
    "HT_TRENDLINE": "Đường xu thế tách bằng Hilbert transform",
    "SAR": "Parabolic SAR — mức dừng lỗ xoay chiều",
    "SAREXT": "Parabolic SAR mở rộng; giá trị âm nghĩa là đang ở chiều bán",
    "AVGPRICE": "(O+H+L+C)/4",
    "MEDPRICE": "(H+L)/2",
    "TYPPRICE": "(H+L+C)/3 — giá điển hình",
    "WCLPRICE": "(H+L+2C)/4 — giá đóng cửa có trọng số",
    # Momentum
    "RSI": "Chỉ số sức mạnh tương đối (làm mượt Wilder)",
    "CMO": "Chande Momentum Oscillator — RSI dạng có dấu, −100…100",
    "MOM": "Động lượng thô: C − C[−n]",
    "ROCP": "Tỷ lệ thay đổi giá qua n bar",
    "ROCR100": "Tỷ số giá hiện tại trên giá n bar trước, tính theo phần trăm",
    "CCI": "Commodity Channel Index — độ lệch khỏi giá điển hình, không bị chặn",
    "WILLR": "Williams %R — vị trí đóng cửa trong biên độ, thang −100…0",
    "MFI": "Money Flow Index — RSI có trọng số khối lượng",
    "ADX": "Cường độ xu thế, không phân biệt chiều",
    "ADXR": "ADX đã làm mượt thêm một lớp",
    "DX": "Chỉ số hướng — thành phần thô của ADX",
    "PLUS_DI": "Chỉ số hướng lên",
    "MINUS_DI": "Chỉ số hướng xuống",
    "PLUS_DM": "Động lượng hướng lên thô, đơn vị điểm giá",
    "MINUS_DM": "Động lượng hướng xuống thô, đơn vị điểm giá",
    "AROON": "Số bar kể từ đỉnh và từ đáy gần nhất",
    "AROONOSC": "Hiệu giữa Aroon up và Aroon down",
    "IMI": "Intraday Momentum Index — RSI tính trên thân nến thay vì giá đóng cửa",
    "STOCHRSI": "Stochastic áp lên RSI thay vì lên giá",
    "TRIX": "Tỷ lệ thay đổi của EMA ba lớp",
    "MACD": "Hiệu hai EMA, kèm đường tín hiệu và histogram",
    "MACDFIX": "MACD với cặp chu kỳ cố định 12/26",
    "APO": "Hiệu tuyệt đối hai trung bình động, đơn vị điểm giá",
    "PPO": "Hiệu hai trung bình động tính theo phần trăm",
    "BOP": "Balance of Power: (C−O)/(H−L)",
    "ULTOSC": "Ultimate Oscillator — ghép ba khung thời gian",
    "STOCH": "Stochastic %K/%D đã làm mượt",
    "STOCHF": "Stochastic nhanh, không làm mượt %K",
    # Cycles
    "HT_DCPERIOD": "Chu kỳ trội đo bằng Hilbert transform, đơn vị bar",
    "HT_DCPHASE": "Pha của chu kỳ trội, đơn vị độ",
    "HT_PHASOR": "Thành phần in-phase và quadrature của tín hiệu giải tích",
    "HT_SINE": "Sine và leading sine — báo trước điểm đảo chiều chu kỳ",
    "HT_TRENDMODE": "1 = chế độ xu thế, 0 = chế độ dao động",
    # Statistic
    "LINEARREG": "Giá trị cuối của đường hồi quy tuyến tính",
    "LINEARREG_ANGLE": "Góc của đường hồi quy, đơn vị độ",
    "LINEARREG_SLOPE": "Độ dốc của đường hồi quy, điểm giá mỗi bar",
    "LINEARREG_INTERCEPT": "Hệ số chặn của đường hồi quy",
    "TSF": "Time Series Forecast — ngoại suy một bước của đường hồi quy",
    "STDDEV": "Độ lệch chuẩn của giá đóng cửa",
    "VAR": "Phương sai của giá đóng cửa",
    "AVGDEV": "Độ lệch tuyệt đối trung bình",
    "BETA": "Hệ số beta giữa đỉnh và đáy",
    "CORREL": "Tương quan giữa đỉnh và đáy — độ chặt của biên độ bar",
    # Volatility
    "ATR": "Biên độ thật trung bình (làm mượt Wilder)",
    "NATR": "ATR chuẩn hoá theo phần trăm giá",
    "TRANGE": "Biên độ thật của một bar",
    # Volume
    "AD": "Đường tích luỹ/phân phối Chaikin",
    "OBV": "On Balance Volume",
    "ADOSC": "Chaikin Oscillator — hiệu hai EMA của đường A/D",
}

# 61 mau nen TA-Lib. Dau ra +100 / -100 cho biet mau nghieng ve tang hay giam.
CDL_GLOSS = {
    "CDL2CROWS": "Hai con quạ — đảo chiều giảm",
    "CDL3BLACKCROWS": "Ba con quạ đen — đảo chiều giảm mạnh",
    "CDL3INSIDE": "Ba nến trong — đảo chiều",
    "CDL3LINESTRIKE": "Ba đường tấn công",
    "CDL3OUTSIDE": "Ba nến ngoài — đảo chiều",
    "CDL3STARSINSOUTH": "Ba ngôi sao phương Nam — đảo chiều tăng",
    "CDL3WHITESOLDIERS": "Ba chiến binh trắng — đảo chiều tăng mạnh",
    "CDLABANDONEDBABY": "Em bé bị bỏ rơi — đảo chiều mạnh, có gap hai bên",
    "CDLADVANCEBLOCK": "Khối cản tiến — xu thế tăng đang đuối sức",
    "CDLBELTHOLD": "Nến giữ đai — mở cửa ngay tại cực biên độ",
    "CDLBREAKAWAY": "Nến bứt phá khỏi vùng tích luỹ",
    "CDLCLOSINGMARUBOZU": "Marubozu đóng cửa — không bóng ở phía đóng cửa",
    "CDLCONCEALBABYSWALL": "Em bé ẩn nấp — đảo chiều tăng, rất hiếm gặp",
    "CDLCOUNTERATTACK": "Phản công — hai nến ngược chiều cùng giá đóng cửa",
    "CDLDARKCLOUDCOVER": "Mây đen che phủ — đảo chiều giảm",
    "CDLDOJI": "Doji — mở và đóng cửa gần bằng nhau, thị trường do dự",
    "CDLDOJISTAR": "Sao doji — doji cách nến trước bằng một gap",
    "CDLDRAGONFLYDOJI": "Doji chuồn chuồn — bóng dưới dài, có hỗ trợ",
    "CDLENGULFING": "Nến nhấn chìm — thân nến phủ trọn nến trước",
    "CDLEVENINGDOJISTAR": "Sao doji buổi tối — đảo chiều giảm",
    "CDLEVENINGSTAR": "Sao buổi tối — đảo chiều giảm",
    "CDLGAPSIDESIDEWHITE": "Hai nến cùng chiều cạnh nhau sau một gap",
    "CDLGRAVESTONEDOJI": "Doji bia mộ — bóng trên dài, có kháng cự",
    "CDLHAMMER": "Nến búa — đảo chiều tăng sau nhịp giảm",
    "CDLHANGINGMAN": "Người treo cổ — đảo chiều giảm sau nhịp tăng",
    "CDLHARAMI": "Harami — nến con nằm gọn trong thân nến mẹ",
    "CDLHARAMICROSS": "Harami chữ thập — nến con là một doji",
    "CDLHIGHWAVE": "Nến sóng cao — hai bóng rất dài, thị trường mất phương hướng",
    "CDLHIKKAKE": "Hikkake — bẫy phá vỡ giá giả",
    "CDLHIKKAKEMOD": "Hikkake biến thể",
    "CDLHOMINGPIGEON": "Bồ câu về tổ — đảo chiều tăng",
    "CDLIDENTICAL3CROWS": "Ba con quạ giống hệt — đảo chiều giảm",
    "CDLINNECK": "Nến trong cổ — tiếp diễn giảm",
    "CDLINVERTEDHAMMER": "Búa ngược — đảo chiều tăng",
    "CDLKICKING": "Nến đá — hai marubozu ngược chiều cách nhau bằng gap",
    "CDLKICKINGBYLENGTH": "Nến đá, chiều xác định bởi marubozu dài hơn",
    "CDLLADDERBOTTOM": "Đáy thang — đảo chiều tăng",
    "CDLLONGLEGGEDDOJI": "Doji chân dài — biên độ rộng, không quyết định",
    "CDLLONGLINE": "Nến thân dài — mức đồng thuận mạnh",
    "CDLMARUBOZU": "Marubozu — không bóng ở cả hai đầu",
    "CDLMATCHINGLOW": "Hai đáy bằng nhau — vùng hỗ trợ",
    "CDLMATHOLD": "Mat hold — tiếp diễn tăng",
    "CDLMORNINGDOJISTAR": "Sao doji buổi sáng — đảo chiều tăng",
    "CDLMORNINGSTAR": "Sao buổi sáng — đảo chiều tăng",
    "CDLONNECK": "Nến trên cổ — tiếp diễn giảm",
    "CDLPIERCING": "Nến xuyên thấu — đảo chiều tăng",
    "CDLRICKSHAWMAN": "Người kéo xe — doji chân dài với thân nằm giữa",
    "CDLRISEFALL3METHODS": "Ba phương pháp tăng/giảm — tiếp diễn xu thế",
    "CDLSEPARATINGLINES": "Đường tách rời — tiếp diễn xu thế",
    "CDLSHOOTINGSTAR": "Sao băng — đảo chiều giảm",
    "CDLSHORTLINE": "Nến thân ngắn — mức đồng thuận thấp",
    "CDLSPINNINGTOP": "Con quay — thân nhỏ, hai bóng dài",
    "CDLSTALLEDPATTERN": "Mẫu đình trệ — đà tăng mất dần",
    "CDLSTICKSANDWICH": "Bánh mì kẹp — đảo chiều tăng",
    "CDLTAKURI": "Takuri — doji chuồn chuồn với bóng dưới rất dài",
    "CDLTASUKIGAP": "Tasuki gap — tiếp diễn xu thế qua gap",
    "CDLTHRUSTING": "Nến đâm xuyên — tiếp diễn giảm",
    "CDLTRISTAR": "Ba ngôi sao — ba doji liên tiếp, đảo chiều",
    "CDLUNIQUE3RIVER": "Ba dòng sông độc nhất — đảo chiều tăng",
    "CDLUPSIDEGAP2CROWS": "Hai con quạ gap lên — đảo chiều giảm",
    "CDLXSIDEGAP3METHODS": "Ba phương pháp có gap — tiếp diễn xu thế",
}

NORM_GLOSS = {
    "price": "log(x / close)",
    "absprice": "log(|x| / close)",
    "sign": "sign(x)",
    "pdiff": "x / close",
    "pvar": "√x / close",
    "pct100": "x / 50 − 1",
    "pct100n": "x / 50 + 1",
    "signed100": "x / 100",
    "pct": "x / 100",
    "deg90": "x / 90",
    "deg180": "x / 180",
    "div100": "x / 100",
    "dcperiod": "(x − 27) / 20",
    "flow": "x / khối lượng TB",
    "flow_diff": "diff(x) / khối lượng TB",
    "pass": "giữ nguyên",
}

# --------------------------------------------------------------------------- #
# Mo ta cho cac nhom viet tay. Khop theo regex vi ten cot co tham so nhung ben
# trong: ret12, pos255, ofi_ma51... {0} duoc thay bang nhom bat duoc.
# --------------------------------------------------------------------------- #
MANUAL: list[tuple[str, str, str]] = [
    # base — hình học một cây nến
    (r"^ret1$", "log(C / C[−1])", "Lợi nhuận log của một bar"),
    (r"^gap$", "log(O / C[−1])", "Nhảy giá đầu bar: qua đêm hoặc qua nghỉ trưa"),
    (r"^oc$", "log(C / O)", "Thân nến có dấu"),
    (r"^hl$", "log(H / L)", "Biên độ bar — cũng là ước lượng biến động Parkinson"),
    (r"^ho$", "log(H / O)", "Khoảng cách từ mở cửa lên đỉnh bar"),
    (r"^lo$", "log(L / O)", "Khoảng cách từ mở cửa xuống đáy bar"),
    (r"^hc$", "log(H / C)", "Khoảng cách từ đóng cửa lên đỉnh bar"),
    (r"^lc$", "log(L / C)", "Khoảng cách từ đóng cửa xuống đáy bar"),
    (r"^clv$", "((C−L) − (H−C)) / (H−L)", "Vị trí đóng cửa trong biên độ bar, −1…1"),
    (r"^body_frac$", "abs(C−O) / (H−L)", "Tỷ lệ thân nến trên toàn biên độ"),
    (r"^upper_wick$", "(H − max(O,C)) / (H−L)", "Tỷ lệ bóng trên"),
    (r"^lower_wick$", "(min(O,C) − L) / (H−L)", "Tỷ lệ bóng dưới"),
    (r"^direction$", "sign(C − O)", "Chiều của nến"),
    (r"^is_flat$", "1 nếu H == L", "Bar phẳng — thường là ATC hoặc lúc thanh khoản cạn"),
    # base — lợi nhuận và biến động
    (r"^ret(\d+)$", "log(C / C[−{0}]) / √{0}",
     "Lợi nhuận {0} bar; chia √{0} để mọi tầm nhìn có cùng độ lớn"),
    (r"^ret(\d+)_z$", "ret{0} / stdev(ret1, 255)",
     "Lợi nhuận {0} bar tính bằng số sigma — so sánh được giữa các chế độ biến động"),
    (r"^rv(\d+)$", "stdev(ret1, {0})", "Biến động đã thực hiện trên {0} bar"),
    (r"^park(\d+)$", "√(mean(hl², {0}) / 4ln2)",
     "Ước lượng Parkinson — dùng biên độ nên hiệu quả hơn rv{0} với cùng số bar"),
    (r"^gk(\d+)$", "Garman–Klass trên {0} bar",
     "Ước lượng biến động dùng cả bốn giá OHLC"),
    (r"^rs(\d+)$", "Rogers–Satchell trên {0} bar",
     "Ước lượng biến động không thiên lệch khi có xu thế"),
    (r"^vol_ratio$", "log(rv12 / rv255)",
     "Tỷ lệ biến động ngắn trên dài — dương nghĩa là biến động vừa bùng"),
    # base — vị trí và chất lượng xu thế
    (r"^pos(\d+)$", "2·(C − LLV(L,{0})) / (HHV(H,{0}) − LLV(L,{0})) − 1",
     "Vị trí giá trong biên độ {0} bar, −1…1"),
    (r"^dhh(\d+)$", "log(C / HHV(H,{0}))", "Khoảng cách tới đỉnh {0} bar (≤ 0)"),
    (r"^dll(\d+)$", "log(C / LLV(L,{0}))", "Khoảng cách tới đáy {0} bar (≥ 0)"),
    (r"^er(\d+)$", "abs(C − C[−{0}]) / Σabs(dC, {0})",
     "Hệ số hiệu quả Kaufman trên {0} bar: gần 1 là xu thế sạch, gần 0 là đi ngang"),
    # base — khối lượng
    (r"^vol_rel(\d+)$", "log(1+V) − mean(log(1+V), {0})",
     "Khối lượng so với trung bình {0} bar gần nhất"),
    (r"^vol_z(\d+)$", "z-score của log(1+V) trên {0} bar",
     "Khối lượng tính bằng số sigma"),
    (r"^vol_seasonal_adj$", "log(1+V) − TB 60 phiên của cùng bar-of-day",
     "Khối lượng đã khử mùa vụ trong phiên — bar 09:00 và 11:20 không còn so lệch nhau"),
    (r"^dollar_vol$", "log(1+V·C) − trung bình trượt 255 bar",
     "Giá trị giao dịch so với mức nền — khối lượng có trọng số giá"),
    (r"^vol_ret_corr$", "sign(dC) · vol_z12",
     "Khối lượng có dấu theo chiều giá: bùng khối lượng lúc tăng hay lúc giảm"),
    # flow
    (r"^ofi$", "(BUY_VOL − SELL_VOL) / (BUY_VOL + SELL_VOL)",
     "Mất cân bằng dòng lệnh trong bar, −1…1"),
    (r"^ofi_val$", "(BUY_VAL − SELL_VAL) / (BUY_VAL + SELL_VAL)",
     "Mất cân bằng dòng lệnh tính theo giá trị thay vì khối lượng"),
    (r"^cum_delta_day$", "Σ(BUY−SELL) / Σ(BUY+SELL), reset mỗi phiên",
     "Delta luỹ kế trong phiên, chuẩn hoá theo hoạt động đã khớp"),
    (r"^ofi_ma(\d+)$", "mean(ofi, {0})",
     "Mất cân bằng dòng lệnh làm mượt {0} bar"),
    (r"^ofi_net(\d+)$", "Σ(BUY−SELL, {0}) / Σ(BUY+SELL, {0})",
     "Delta ròng {0} bar, chuẩn hoá theo tổng hoạt động cùng cửa sổ"),
    (r"^active_rel(\d+)$", "log(1+BUY+SELL) − trung bình trượt {0}",
     "Cường độ lệnh chủ động so với {0} bar gần nhất"),
    (r"^flow_price_div$", "sign(ret1) · (−ofi_ma12)",
     "Phân kỳ dòng tiền–giá: giá tăng nhưng dòng tiền bán ròng, hoặc ngược lại"),
    # session
    (r"^day_progress$", "2·bar_of_day / (số bar phiên trước − 1) − 1",
     "Tiến độ phiên, −1 đầu phiên đến +1 cuối phiên"),
    (r"^is_first_bar$", "1 tại bar đầu phiên", "Cờ đánh dấu mở cửa"),
    (r"^is_last_bar$", "1 khi giờ ≥ 14:45",
     "Cờ đánh dấu bar ATC, lấy từ lịch giao dịch chứ không từ việc đếm bar"),
    (r"^bars_to_close$", "log(1 + số bar còn lại đến 14:45)",
     "Còn bao lâu nữa đến khi đóng phiên"),
    (r"^tod_sin$", "sin(2π · phút / 1440)", "Giờ trong ngày, thành phần sin"),
    (r"^tod_cos$", "cos(2π · phút / 1440)", "Giờ trong ngày, thành phần cos"),
    (r"^minute_norm$", "(phút trong ngày − 540) / 345",
     "Vị trí tuyến tính trong phiên, 0 lúc 09:00 và 1 lúc 14:45"),
    (r"^bar_gap$", "log(1 + số phút kể từ bar trước)",
     "Khoảng cách thực tế tới bar trước: 5 bình thường, 90 sau nghỉ trưa, ~1095 qua đêm"),
    (r"^after_lunch$", "1 tại bar đầu tiên sau nghỉ trưa",
     "Cờ đánh dấu mở cửa phiên chiều"),
    (r"^dow_sin$", "sin(2π · thứ / 7)", "Thứ trong tuần, thành phần sin"),
    (r"^dow_cos$", "cos(2π · thứ / 7)", "Thứ trong tuần, thành phần cos"),
    (r"^is_monday$", "1 nếu là thứ Hai", "Hiệu ứng đầu tuần"),
    (r"^is_friday$", "1 nếu là thứ Sáu", "Hiệu ứng cuối tuần"),
    (r"^month_sin$", "sin(2π · (tháng−1) / 12)", "Tháng trong năm, thành phần sin"),
    (r"^month_cos$", "cos(2π · (tháng−1) / 12)", "Tháng trong năm, thành phần cos"),
    (r"^dom_norm$", "(ngày − 15,5) / 15,5", "Vị trí trong tháng, −1…1"),
    (r"^dte$", "số ngày đến đáo hạn / 30",
     "VN30F1M xoay vòng theo tháng: gần đáo hạn thì basis và thanh khoản đổi hành vi"),
    (r"^dte_inv$", "1 / (1 + số ngày đến đáo hạn)",
     "Nhấn mạnh những ngày sát đáo hạn"),
    (r"^is_expiry_week$", "1 khi còn ≤ 5 ngày đến đáo hạn", "Tuần đáo hạn"),
    (r"^is_expiry_day$", "1 đúng ngày đáo hạn",
     "Ngày đáo hạn — thanh khoản và biến động bất thường"),
    # bot — KESPT
    (r"^kespt_st_up$", "log(Up / C)", "Băng trên của SuperTrend(3, ATR 28)"),
    (r"^kespt_st_dn$", "log(Dn / C)", "Băng dưới của SuperTrend(3, ATR 28)"),
    (r"^kespt_st_line$", "log(đường ST đang hoạt động / C)",
     "Đường SuperTrend hiện hành — chính là mức dừng lỗ của bot"),
    (r"^kespt_st_trend$", "+1 / −1", "Trạng thái xu thế SuperTrend"),
    (r"^kespt_st_dist_atr$", "(C − đường ST) / ATR(28)",
     "Còn bao nhiêu ATR trước khi SuperTrend đảo chiều — đại lượng bot thực sự dựa vào"),
    (r"^kespt_atr28$", "ATR(28) / C", "Biên độ thật trung bình theo tham số của bot"),
    (r"^kespt_rsi22$", "RSI(22) / 50 − 1", "RSI theo đúng tham số của bot"),
    (r"^kespt_ema300_slope$", "log(EMA300 / EMA300[−1])",
     "Độ dốc của bộ lọc xu thế EMA300"),
    (r"^kespt_stochk$", "StochK(22, 43) / 50 − 1",
     "Stochastic %K theo đúng tham số của bot"),
    (r"^kespt_lrsi$", "LinearReg(RSI(22), 54) / 50 − 1",
     "RSI đã làm phẳng bằng hồi quy tuyến tính"),
    (r"^kespt_lsto$", "LinearReg(StochK(22,43), 54) / 50 − 1",
     "Stochastic đã làm phẳng bằng hồi quy tuyến tính"),
    (r"^kespt_storsi$", "(3,7·LRSI + LSTO) / 4,7 rồi đổi về −1…1",
     "Dao động lõi của bot KESPT"),
    (r"^kespt_storsi_ma$", "WMA(STORSI, 34) rồi đổi về −1…1",
     "Đường tín hiệu của STORSI"),
    (r"^kespt_hiskf$", "(STORSI − STORSIma) / 4,7 / 50",
     "Histogram KF — giao cắt của nó sinh tín hiệu vào lệnh"),
    (r"^kespt_ema300$", "log(EMA(C, 300) / C)", "Bộ lọc xu thế của bot KESPT"),
    (r"^kespt_above_ema$", "sign(C − EMA300)", "Giá trên hay dưới bộ lọc xu thế"),
    (r"^kespt_kf_state$", "+1 / −1", "Trạng thái giao cắt KF (Buy1 / Short1)"),
    (r"^kespt_sig_state$", "+1 / 0 / −1",
     "KF và SuperTrend đã cùng chiều chưa — điều kiện trước khi áp bộ lọc EMA"),
    # bot — Roofing
    (r"^roof_hp$", "HighPass(C, 120) / C",
     "Giá đã lọc thông cao — bỏ thành phần xu thế chậm"),
    (r"^roof_filt$", "SuperSmoother(HP, 22) / C",
     "Roofing Filter của Ehlers — dao động lõi của bot Roofing"),
    (r"^roof_signal$", "WMA(Filt, 10) / C", "Đường tín hiệu của Roofing Filter"),
    (r"^roof_hist$", "(Filt − Signal) / C",
     "Histogram Roofing — giao cắt sinh tín hiệu vào lệnh"),
    (r"^roof_mom$", "(Filt − Filt[−45]) / C", "Động lượng của Roofing Filter"),
    (r"^roof_momz$", "Mom / stdev(Mom, 160)",
     "Momentum thrust dạng z-score — công tắc chính của bot, ngưỡng ±0,72"),
    (r"^roof_ema240$", "log(EMA(C, 240) / C)", "Bộ lọc xu thế của bot Roofing"),
    (r"^roof_emafilter$", "log(Ref(EMA(C,240), −1) / C)",
     "Bộ lọc xu thế trễ một bar — đúng dạng bot dùng để so với giá"),
    (r"^roof_ema240_slope$", "log(EMA240 / EMA240[−1])",
     "Độ dốc của bộ lọc xu thế EMA240"),
    (r"^roof_above_ema$", "sign(C − Ref(EMA(C,240), −1))",
     "Giá trên hay dưới bộ lọc xu thế của Roofing"),
    (r"^roof_open_state$", "+1 / −1",
     "Trạng thái giao cắt Roofing (openBuy / openShort)"),
    (r"^roof_mom_gate$", "+1 / 0 / −1", "Cổng momentum đã mở chưa và mở về chiều nào"),
    (r"^agree_trend$", "kespt_st_trend · roof_open_state",
     "Hai bot đồng thuận (+1) hay mâu thuẫn (−1) về chiều"),
]

_COMPILED = [(re.compile(p), f, d) for p, f, d in MANUAL]

GROUP_TITLES = {
    "base": "Biến đổi cơ bản từ OHLC",
    "candles": "Mẫu hình nến",
    "cycles": "Chu kỳ (Hilbert transform)",
    "momentum": "Động lượng",
    "overlap": "Trung bình động và đường bao",
    "price": "Giá phái sinh",
    "statistic": "Thống kê",
    "volatility": "Biến động",
    "volume": "Khối lượng",
    "flow": "Dòng lệnh mua/bán",
    "session": "Lịch và vị trí trong phiên",
    "bot": "Đầu vào của hai bot AFL",
}

# Ba ho nguon goc - dung de to mau va loc trong danh muc.
FAMILY = {
    "base": "laplace", "flow": "laplace", "session": "laplace",
    "candles": "talib", "cycles": "talib", "momentum": "talib", "overlap": "talib",
    "price": "talib", "statistic": "talib", "volatility": "talib", "volume": "talib",
    "bot": "bot",
}


@dataclass
class Feature:
    column: str
    group: str
    family: str
    source: str
    formula: str
    description: str
    status: str = "kept"
    note: str = ""


def _talib_features(cfg: FeatureConfig) -> dict[str, Feature]:
    """Doc nguoc tu cac Spec: moi Spec biet ham, tham so va kieu chuan hoa cua no."""
    out: dict[str, Feature] = {}
    for group, builder in GROUP_BUILDERS.items():
        for spec in builder(cfg):
            params = ", ".join(f"{k}={v}" for k, v in spec.params.items())
            source = f"{spec.func}({params})" if params else f"{spec.func}()"
            gloss = FUNC_GLOSS.get(spec.func) or CDL_GLOSS.get(spec.func, spec.func)
            for name, kind in zip(_column_names(spec), spec.norms, strict=True):
                out[f"{group}__{name}"] = Feature(
                    f"{group}__{name}", group, FAMILY[group], source,
                    NORM_GLOSS.get(kind, kind), gloss,
                )
                if spec.slope:
                    out[f"{group}__{name}_slope"] = Feature(
                        f"{group}__{name}_slope", group, FAMILY[group], source,
                        "log(x / x[−1])",
                        f"Độ dốc của {spec.func} — xu thế của chính đường trung bình, "
                        f"tách khỏi khoảng cách giá-đến-đường",
                    )
    return out


def _manual_feature(column: str, group: str) -> Feature:
    short = column.split("__", 1)[1]
    for pattern, formula, desc in _COMPILED:
        m = pattern.match(short)
        if m:
            args = m.groups()
            return Feature(column, group, FAMILY.get(group, "laplace"), "laplace",
                           formula.format(*args), desc.format(*args))
    return Feature(column, group, FAMILY.get(group, "laplace"), "laplace", "", "")


def build_catalog(columns: list[str], cfg: FeatureConfig | None = None,
                  dropped: dict[str, str] | None = None) -> pd.DataFrame:
    """Bang tra cuu cho danh sach cot da cho, giu nguyen thu tu.

    `dropped` la anh xa cot -> ly do tu prune_columns(); neu co, cac cot bi loai duoc
    them vao cuoi voi status = "dropped" de danh muc phan anh ca nhung gi da bi bo.
    """
    cfg = cfg or FeatureConfig()
    talib_map = _talib_features(cfg)

    def base_lookup(col: str) -> Feature:
        group = col.split("__", 1)[0]
        f = talib_map.get(col)
        # Ban sao: lookup() sua cong thuc tai cho, khong duoc lam hong ban dung chung.
        return replace(f) if f else _manual_feature(col, group)

    def lookup(col: str) -> Feature:
        # Buoc lop tinh dung (spec 006) boc them mot phep bien doi quanh cong thuc goc.
        if not cfg.stationarize:
            return base_lookup(col)
        w = cfg.rolling_window
        if col.endswith("_z") and classify(col[:-2], cfg) == "variance":
            f = base_lookup(col[:-2])
            f.column = col
            f.formula = f"PIT_t{cfg.pit_dof:g}(z_{w}(log |{f.formula}|))"
            f.description = (f"{f.description} — so với {w} bar trước (z-score cuộn, "
                             f"nén đuôi Student-t)")
            return f
        f = base_lookup(col)
        kind = classify(col, cfg)
        if kind == "adaptive":
            f.formula = f"PIT_t{cfg.pit_dof:g}(z_{w}({f.formula}))"
            f.description = (f"{f.description} — so với {w} bar trước; mức tuyệt đối bị "
                             f"bỏ vì gãy cấu trúc năm 2023")
        elif kind == "variance":
            f.formula = f"log |{f.formula}|"
        return f

    rows = [vars(lookup(c)) for c in columns]
    for col, reason in (dropped or {}).items():
        feat = lookup(col)
        feat.status, feat.note = "dropped", reason
        rows.append(vars(feat))
    return pd.DataFrame(rows)


def _cell(text: str) -> str:
    """Escape ky tu | de khong lam vo bang markdown."""
    return str(text).replace("|", "\\|")


def to_markdown(catalog: pd.DataFrame) -> str:
    """Danh muc day du dang markdown, nhom theo group."""
    kept = catalog[catalog["status"] == "kept"]
    dropped = catalog[catalog["status"] == "dropped"]

    lines = [
        "# Danh mục đặc trưng",
        "",
        f"**{len(kept)}** đặc trưng trong ma trận đầu vào, **{len(dropped)}** cột bị "
        "loại ở bước tỉa. Sinh tự động từ `laplace/catalog.py` — đừng sửa tay.",
        "",
    ]
    for group, title in GROUP_TITLES.items():
        sub = kept[kept["group"] == group]
        if sub.empty:
            continue
        lines += [f"## `{group}` — {title}  ({len(sub)} cột)", "",
                  "| # | Cột | Nguồn | Công thức / chuẩn hoá | Ý nghĩa |",
                  "|---:|---|---|---|---|"]
        for i, r in enumerate(sub.itertuples(), 1):
            lines.append(f"| {i} | `{r.column}` | {_cell(r.source)} "
                         f"| {_cell(r.formula)} | {_cell(r.description)} |")
        lines.append("")

    if not dropped.empty:
        lines += [f"## Cột bị loại ở bước tỉa  ({len(dropped)} cột)", "",
                  "Loại trên tập train: hằng số, gần như luôn bằng 0, hoặc trùng lặp "
                  "với một cột khác ở mức |corr| ≥ 0,999.", "",
                  "| # | Cột | Lý do |", "|---:|---|---|"]
        for i, r in enumerate(dropped.itertuples(), 1):
            lines.append(f"| {i} | `{r.column}` | {_cell(r.note)} |")
        lines.append("")
    return "\n".join(lines)
