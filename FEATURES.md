# Danh mục đặc trưng

**454** đặc trưng trong ma trận đầu vào, **85** cột bị loại ở bước tỉa. Sinh tự động từ `laplace/catalog.py` — đừng sửa tay.

## `base` — Biến đổi cơ bản từ OHLC  (71 cột)

| # | Cột | Nguồn | Công thức / chuẩn hoá | Ý nghĩa |
|---:|---|---|---|---|
| 1 | `base__ret1` | laplace | log(C / C[−1]) | Lợi nhuận log của một bar |
| 2 | `base__gap` | laplace | log(O / C[−1]) | Nhảy giá đầu bar: qua đêm hoặc qua nghỉ trưa |
| 3 | `base__oc` | laplace | log(C / O) | Thân nến có dấu |
| 4 | `base__hl` | laplace | log(H / L) | Biên độ bar — cũng là ước lượng biến động Parkinson |
| 5 | `base__ho` | laplace | log(H / O) | Khoảng cách từ mở cửa lên đỉnh bar |
| 6 | `base__lo` | laplace | log(L / O) | Khoảng cách từ mở cửa xuống đáy bar |
| 7 | `base__hc` | laplace | log(H / C) | Khoảng cách từ đóng cửa lên đỉnh bar |
| 8 | `base__lc` | laplace | log(L / C) | Khoảng cách từ đóng cửa xuống đáy bar |
| 9 | `base__clv` | laplace | ((C−L) − (H−C)) / (H−L) | Vị trí đóng cửa trong biên độ bar, −1…1 |
| 10 | `base__body_frac` | laplace | abs(C−O) / (H−L) | Tỷ lệ thân nến trên toàn biên độ |
| 11 | `base__upper_wick` | laplace | (H − max(O,C)) / (H−L) | Tỷ lệ bóng trên |
| 12 | `base__lower_wick` | laplace | (min(O,C) − L) / (H−L) | Tỷ lệ bóng dưới |
| 13 | `base__direction` | laplace | sign(C − O) | Chiều của nến |
| 14 | `base__is_flat` | laplace | 1 nếu H == L | Bar phẳng — thường là ATC hoặc lúc thanh khoản cạn |
| 15 | `base__ret2` | laplace | log(C / C[−2]) / √2 | Lợi nhuận 2 bar; chia √2 để mọi tầm nhìn có cùng độ lớn |
| 16 | `base__ret3` | laplace | log(C / C[−3]) / √3 | Lợi nhuận 3 bar; chia √3 để mọi tầm nhìn có cùng độ lớn |
| 17 | `base__ret6` | laplace | log(C / C[−6]) / √6 | Lợi nhuận 6 bar; chia √6 để mọi tầm nhìn có cùng độ lớn |
| 18 | `base__ret12` | laplace | log(C / C[−12]) / √12 | Lợi nhuận 12 bar; chia √12 để mọi tầm nhìn có cùng độ lớn |
| 19 | `base__ret24` | laplace | log(C / C[−24]) / √24 | Lợi nhuận 24 bar; chia √24 để mọi tầm nhìn có cùng độ lớn |
| 20 | `base__ret51` | laplace | log(C / C[−51]) / √51 | Lợi nhuận 51 bar; chia √51 để mọi tầm nhìn có cùng độ lớn |
| 21 | `base__rv12` | laplace | stdev(ret1, 12) | Biến động đã thực hiện trên 12 bar |
| 22 | `base__park12` | laplace | √(mean(hl², 12) / 4ln2) | Ước lượng Parkinson — dùng biên độ nên hiệu quả hơn rv12 với cùng số bar |
| 23 | `base__gk12` | laplace | Garman–Klass trên 12 bar | Ước lượng biến động dùng cả bốn giá OHLC |
| 24 | `base__rs12` | laplace | Rogers–Satchell trên 12 bar | Ước lượng biến động không thiên lệch khi có xu thế |
| 25 | `base__rv51` | laplace | stdev(ret1, 51) | Biến động đã thực hiện trên 51 bar |
| 26 | `base__park51` | laplace | √(mean(hl², 51) / 4ln2) | Ước lượng Parkinson — dùng biên độ nên hiệu quả hơn rv51 với cùng số bar |
| 27 | `base__gk51` | laplace | Garman–Klass trên 51 bar | Ước lượng biến động dùng cả bốn giá OHLC |
| 28 | `base__rs51` | laplace | Rogers–Satchell trên 51 bar | Ước lượng biến động không thiên lệch khi có xu thế |
| 29 | `base__rv255` | laplace | stdev(ret1, 255) | Biến động đã thực hiện trên 255 bar |
| 30 | `base__park255` | laplace | √(mean(hl², 255) / 4ln2) | Ước lượng Parkinson — dùng biên độ nên hiệu quả hơn rv255 với cùng số bar |
| 31 | `base__gk255` | laplace | Garman–Klass trên 255 bar | Ước lượng biến động dùng cả bốn giá OHLC |
| 32 | `base__ret1_z` | laplace | ret1 / stdev(ret1, 255) | Lợi nhuận 1 bar tính bằng số sigma — so sánh được giữa các chế độ biến động |
| 33 | `base__ret2_z` | laplace | ret2 / stdev(ret1, 255) | Lợi nhuận 2 bar tính bằng số sigma — so sánh được giữa các chế độ biến động |
| 34 | `base__ret3_z` | laplace | ret3 / stdev(ret1, 255) | Lợi nhuận 3 bar tính bằng số sigma — so sánh được giữa các chế độ biến động |
| 35 | `base__ret6_z` | laplace | ret6 / stdev(ret1, 255) | Lợi nhuận 6 bar tính bằng số sigma — so sánh được giữa các chế độ biến động |
| 36 | `base__ret12_z` | laplace | ret12 / stdev(ret1, 255) | Lợi nhuận 12 bar tính bằng số sigma — so sánh được giữa các chế độ biến động |
| 37 | `base__ret24_z` | laplace | ret24 / stdev(ret1, 255) | Lợi nhuận 24 bar tính bằng số sigma — so sánh được giữa các chế độ biến động |
| 38 | `base__ret51_z` | laplace | ret51 / stdev(ret1, 255) | Lợi nhuận 51 bar tính bằng số sigma — so sánh được giữa các chế độ biến động |
| 39 | `base__vol_ratio` | laplace | log(rv12 / rv255) | Tỷ lệ biến động ngắn trên dài — dương nghĩa là biến động vừa bùng |
| 40 | `base__pos6` | laplace | 2·(C − LLV(L,6)) / (HHV(H,6) − LLV(L,6)) − 1 | Vị trí giá trong biên độ 6 bar, −1…1 |
| 41 | `base__dhh6` | laplace | log(C / HHV(H,6)) | Khoảng cách tới đỉnh 6 bar (≤ 0) |
| 42 | `base__dll6` | laplace | log(C / LLV(L,6)) | Khoảng cách tới đáy 6 bar (≥ 0) |
| 43 | `base__er6` | laplace | abs(C − C[−6]) / Σabs(dC, 6) | Hệ số hiệu quả Kaufman trên 6 bar: gần 1 là xu thế sạch, gần 0 là đi ngang |
| 44 | `base__pos12` | laplace | 2·(C − LLV(L,12)) / (HHV(H,12) − LLV(L,12)) − 1 | Vị trí giá trong biên độ 12 bar, −1…1 |
| 45 | `base__dhh12` | laplace | log(C / HHV(H,12)) | Khoảng cách tới đỉnh 12 bar (≤ 0) |
| 46 | `base__dll12` | laplace | log(C / LLV(L,12)) | Khoảng cách tới đáy 12 bar (≥ 0) |
| 47 | `base__er12` | laplace | abs(C − C[−12]) / Σabs(dC, 12) | Hệ số hiệu quả Kaufman trên 12 bar: gần 1 là xu thế sạch, gần 0 là đi ngang |
| 48 | `base__pos24` | laplace | 2·(C − LLV(L,24)) / (HHV(H,24) − LLV(L,24)) − 1 | Vị trí giá trong biên độ 24 bar, −1…1 |
| 49 | `base__dhh24` | laplace | log(C / HHV(H,24)) | Khoảng cách tới đỉnh 24 bar (≤ 0) |
| 50 | `base__dll24` | laplace | log(C / LLV(L,24)) | Khoảng cách tới đáy 24 bar (≥ 0) |
| 51 | `base__er24` | laplace | abs(C − C[−24]) / Σabs(dC, 24) | Hệ số hiệu quả Kaufman trên 24 bar: gần 1 là xu thế sạch, gần 0 là đi ngang |
| 52 | `base__pos51` | laplace | 2·(C − LLV(L,51)) / (HHV(H,51) − LLV(L,51)) − 1 | Vị trí giá trong biên độ 51 bar, −1…1 |
| 53 | `base__dhh51` | laplace | log(C / HHV(H,51)) | Khoảng cách tới đỉnh 51 bar (≤ 0) |
| 54 | `base__dll51` | laplace | log(C / LLV(L,51)) | Khoảng cách tới đáy 51 bar (≥ 0) |
| 55 | `base__er51` | laplace | abs(C − C[−51]) / Σabs(dC, 51) | Hệ số hiệu quả Kaufman trên 51 bar: gần 1 là xu thế sạch, gần 0 là đi ngang |
| 56 | `base__pos102` | laplace | 2·(C − LLV(L,102)) / (HHV(H,102) − LLV(L,102)) − 1 | Vị trí giá trong biên độ 102 bar, −1…1 |
| 57 | `base__dhh102` | laplace | log(C / HHV(H,102)) | Khoảng cách tới đỉnh 102 bar (≤ 0) |
| 58 | `base__dll102` | laplace | log(C / LLV(L,102)) | Khoảng cách tới đáy 102 bar (≥ 0) |
| 59 | `base__er102` | laplace | abs(C − C[−102]) / Σabs(dC, 102) | Hệ số hiệu quả Kaufman trên 102 bar: gần 1 là xu thế sạch, gần 0 là đi ngang |
| 60 | `base__pos255` | laplace | 2·(C − LLV(L,255)) / (HHV(H,255) − LLV(L,255)) − 1 | Vị trí giá trong biên độ 255 bar, −1…1 |
| 61 | `base__dhh255` | laplace | log(C / HHV(H,255)) | Khoảng cách tới đỉnh 255 bar (≤ 0) |
| 62 | `base__dll255` | laplace | log(C / LLV(L,255)) | Khoảng cách tới đáy 255 bar (≥ 0) |
| 63 | `base__er255` | laplace | abs(C − C[−255]) / Σabs(dC, 255) | Hệ số hiệu quả Kaufman trên 255 bar: gần 1 là xu thế sạch, gần 0 là đi ngang |
| 64 | `base__vol_rel12` | laplace | log(1+V) − mean(log(1+V), 12) | Khối lượng so với trung bình 12 bar gần nhất |
| 65 | `base__vol_z12` | laplace | z-score của log(1+V) trên 12 bar | Khối lượng tính bằng số sigma |
| 66 | `base__vol_rel51` | laplace | log(1+V) − mean(log(1+V), 51) | Khối lượng so với trung bình 51 bar gần nhất |
| 67 | `base__vol_z51` | laplace | z-score của log(1+V) trên 51 bar | Khối lượng tính bằng số sigma |
| 68 | `base__vol_rel255` | laplace | log(1+V) − mean(log(1+V), 255) | Khối lượng so với trung bình 255 bar gần nhất |
| 69 | `base__vol_z255` | laplace | z-score của log(1+V) trên 255 bar | Khối lượng tính bằng số sigma |
| 70 | `base__vol_seasonal_adj` | laplace | log(1+V) − TB 60 phiên của cùng bar-of-day | Khối lượng đã khử mùa vụ trong phiên — bar 09:00 và 11:20 không còn so lệch nhau |
| 71 | `base__vol_ret_corr` | laplace | sign(dC) · vol_z12 | Khối lượng có dấu theo chiều giá: bùng khối lượng lúc tăng hay lúc giảm |

## `cycles` — Chu kỳ (Hilbert transform)  (7 cột)

| # | Cột | Nguồn | Công thức / chuẩn hoá | Ý nghĩa |
|---:|---|---|---|---|
| 1 | `cycles__HT_DCPERIOD` | HT_DCPERIOD() | (x − 27) / 20 | Chu kỳ trội đo bằng Hilbert transform, đơn vị bar |
| 2 | `cycles__HT_DCPHASE` | HT_DCPHASE() | x / 180 | Pha của chu kỳ trội, đơn vị độ |
| 3 | `cycles__HT_PHASOR_inphase` | HT_PHASOR() | x / close | Thành phần in-phase và quadrature của tín hiệu giải tích |
| 4 | `cycles__HT_PHASOR_quadrature` | HT_PHASOR() | x / close | Thành phần in-phase và quadrature của tín hiệu giải tích |
| 5 | `cycles__HT_SINE_sine` | HT_SINE() | giữ nguyên | Sine và leading sine — báo trước điểm đảo chiều chu kỳ |
| 6 | `cycles__HT_SINE_leadsine` | HT_SINE() | giữ nguyên | Sine và leading sine — báo trước điểm đảo chiều chu kỳ |
| 7 | `cycles__HT_TRENDMODE` | HT_TRENDMODE() | giữ nguyên | 1 = chế độ xu thế, 0 = chế độ dao động |

## `momentum` — Động lượng  (131 cột)

| # | Cột | Nguồn | Công thức / chuẩn hoá | Ý nghĩa |
|---:|---|---|---|---|
| 1 | `momentum__RSI6` | RSI(timeperiod=6) | x / 50 − 1 | Chỉ số sức mạnh tương đối (làm mượt Wilder) |
| 2 | `momentum__CCI6` | CCI(timeperiod=6) | x / 100 | Commodity Channel Index — độ lệch khỏi giá điển hình, không bị chặn |
| 3 | `momentum__MFI6` | MFI(timeperiod=6) | x / 50 − 1 | Money Flow Index — RSI có trọng số khối lượng |
| 4 | `momentum__ADX6` | ADX(timeperiod=6) | x / 50 − 1 | Cường độ xu thế, không phân biệt chiều |
| 5 | `momentum__ADXR6` | ADXR(timeperiod=6) | x / 50 − 1 | ADX đã làm mượt thêm một lớp |
| 6 | `momentum__DX6` | DX(timeperiod=6) | x / 50 − 1 | Chỉ số hướng — thành phần thô của ADX |
| 7 | `momentum__PLUS_DI6` | PLUS_DI(timeperiod=6) | x / 50 − 1 | Chỉ số hướng lên |
| 8 | `momentum__MINUS_DI6` | MINUS_DI(timeperiod=6) | x / 50 − 1 | Chỉ số hướng xuống |
| 9 | `momentum__PLUS_DM6` | PLUS_DM(timeperiod=6) | x / close | Động lượng hướng lên thô, đơn vị điểm giá |
| 10 | `momentum__MINUS_DM6` | MINUS_DM(timeperiod=6) | x / close | Động lượng hướng xuống thô, đơn vị điểm giá |
| 11 | `momentum__AROON6_down` | AROON(timeperiod=6) | x / 50 − 1 | Số bar kể từ đỉnh và từ đáy gần nhất |
| 12 | `momentum__AROON6_up` | AROON(timeperiod=6) | x / 50 − 1 | Số bar kể từ đỉnh và từ đáy gần nhất |
| 13 | `momentum__AROONOSC6` | AROONOSC(timeperiod=6) | x / 100 | Hiệu giữa Aroon up và Aroon down |
| 14 | `momentum__IMI6` | IMI(timeperiod=6) | x / 50 − 1 | Intraday Momentum Index — RSI tính trên thân nến thay vì giá đóng cửa |
| 15 | `momentum__STOCHRSI6_k` | STOCHRSI(timeperiod=6) | x / 50 − 1 | Stochastic áp lên RSI thay vì lên giá |
| 16 | `momentum__STOCHRSI6_d` | STOCHRSI(timeperiod=6) | x / 50 − 1 | Stochastic áp lên RSI thay vì lên giá |
| 17 | `momentum__RSI12` | RSI(timeperiod=12) | x / 50 − 1 | Chỉ số sức mạnh tương đối (làm mượt Wilder) |
| 18 | `momentum__CCI12` | CCI(timeperiod=12) | x / 100 | Commodity Channel Index — độ lệch khỏi giá điển hình, không bị chặn |
| 19 | `momentum__MFI12` | MFI(timeperiod=12) | x / 50 − 1 | Money Flow Index — RSI có trọng số khối lượng |
| 20 | `momentum__ADX12` | ADX(timeperiod=12) | x / 50 − 1 | Cường độ xu thế, không phân biệt chiều |
| 21 | `momentum__ADXR12` | ADXR(timeperiod=12) | x / 50 − 1 | ADX đã làm mượt thêm một lớp |
| 22 | `momentum__DX12` | DX(timeperiod=12) | x / 50 − 1 | Chỉ số hướng — thành phần thô của ADX |
| 23 | `momentum__PLUS_DI12` | PLUS_DI(timeperiod=12) | x / 50 − 1 | Chỉ số hướng lên |
| 24 | `momentum__MINUS_DI12` | MINUS_DI(timeperiod=12) | x / 50 − 1 | Chỉ số hướng xuống |
| 25 | `momentum__PLUS_DM12` | PLUS_DM(timeperiod=12) | x / close | Động lượng hướng lên thô, đơn vị điểm giá |
| 26 | `momentum__MINUS_DM12` | MINUS_DM(timeperiod=12) | x / close | Động lượng hướng xuống thô, đơn vị điểm giá |
| 27 | `momentum__AROON12_down` | AROON(timeperiod=12) | x / 50 − 1 | Số bar kể từ đỉnh và từ đáy gần nhất |
| 28 | `momentum__AROON12_up` | AROON(timeperiod=12) | x / 50 − 1 | Số bar kể từ đỉnh và từ đáy gần nhất |
| 29 | `momentum__AROONOSC12` | AROONOSC(timeperiod=12) | x / 100 | Hiệu giữa Aroon up và Aroon down |
| 30 | `momentum__IMI12` | IMI(timeperiod=12) | x / 50 − 1 | Intraday Momentum Index — RSI tính trên thân nến thay vì giá đóng cửa |
| 31 | `momentum__STOCHRSI12_k` | STOCHRSI(timeperiod=12) | x / 50 − 1 | Stochastic áp lên RSI thay vì lên giá |
| 32 | `momentum__STOCHRSI12_d` | STOCHRSI(timeperiod=12) | x / 50 − 1 | Stochastic áp lên RSI thay vì lên giá |
| 33 | `momentum__RSI24` | RSI(timeperiod=24) | x / 50 − 1 | Chỉ số sức mạnh tương đối (làm mượt Wilder) |
| 34 | `momentum__CCI24` | CCI(timeperiod=24) | x / 100 | Commodity Channel Index — độ lệch khỏi giá điển hình, không bị chặn |
| 35 | `momentum__MFI24` | MFI(timeperiod=24) | x / 50 − 1 | Money Flow Index — RSI có trọng số khối lượng |
| 36 | `momentum__ADX24` | ADX(timeperiod=24) | x / 50 − 1 | Cường độ xu thế, không phân biệt chiều |
| 37 | `momentum__ADXR24` | ADXR(timeperiod=24) | x / 50 − 1 | ADX đã làm mượt thêm một lớp |
| 38 | `momentum__DX24` | DX(timeperiod=24) | x / 50 − 1 | Chỉ số hướng — thành phần thô của ADX |
| 39 | `momentum__PLUS_DI24` | PLUS_DI(timeperiod=24) | x / 50 − 1 | Chỉ số hướng lên |
| 40 | `momentum__MINUS_DI24` | MINUS_DI(timeperiod=24) | x / 50 − 1 | Chỉ số hướng xuống |
| 41 | `momentum__PLUS_DM24` | PLUS_DM(timeperiod=24) | x / close | Động lượng hướng lên thô, đơn vị điểm giá |
| 42 | `momentum__MINUS_DM24` | MINUS_DM(timeperiod=24) | x / close | Động lượng hướng xuống thô, đơn vị điểm giá |
| 43 | `momentum__AROON24_down` | AROON(timeperiod=24) | x / 50 − 1 | Số bar kể từ đỉnh và từ đáy gần nhất |
| 44 | `momentum__AROON24_up` | AROON(timeperiod=24) | x / 50 − 1 | Số bar kể từ đỉnh và từ đáy gần nhất |
| 45 | `momentum__AROONOSC24` | AROONOSC(timeperiod=24) | x / 100 | Hiệu giữa Aroon up và Aroon down |
| 46 | `momentum__IMI24` | IMI(timeperiod=24) | x / 50 − 1 | Intraday Momentum Index — RSI tính trên thân nến thay vì giá đóng cửa |
| 47 | `momentum__STOCHRSI24_k` | STOCHRSI(timeperiod=24) | x / 50 − 1 | Stochastic áp lên RSI thay vì lên giá |
| 48 | `momentum__STOCHRSI24_d` | STOCHRSI(timeperiod=24) | x / 50 − 1 | Stochastic áp lên RSI thay vì lên giá |
| 49 | `momentum__RSI51` | RSI(timeperiod=51) | x / 50 − 1 | Chỉ số sức mạnh tương đối (làm mượt Wilder) |
| 50 | `momentum__CCI51` | CCI(timeperiod=51) | x / 100 | Commodity Channel Index — độ lệch khỏi giá điển hình, không bị chặn |
| 51 | `momentum__MFI51` | MFI(timeperiod=51) | x / 50 − 1 | Money Flow Index — RSI có trọng số khối lượng |
| 52 | `momentum__ADX51` | ADX(timeperiod=51) | x / 50 − 1 | Cường độ xu thế, không phân biệt chiều |
| 53 | `momentum__ADXR51` | ADXR(timeperiod=51) | x / 50 − 1 | ADX đã làm mượt thêm một lớp |
| 54 | `momentum__DX51` | DX(timeperiod=51) | x / 50 − 1 | Chỉ số hướng — thành phần thô của ADX |
| 55 | `momentum__PLUS_DI51` | PLUS_DI(timeperiod=51) | x / 50 − 1 | Chỉ số hướng lên |
| 56 | `momentum__MINUS_DI51` | MINUS_DI(timeperiod=51) | x / 50 − 1 | Chỉ số hướng xuống |
| 57 | `momentum__PLUS_DM51` | PLUS_DM(timeperiod=51) | x / close | Động lượng hướng lên thô, đơn vị điểm giá |
| 58 | `momentum__MINUS_DM51` | MINUS_DM(timeperiod=51) | x / close | Động lượng hướng xuống thô, đơn vị điểm giá |
| 59 | `momentum__AROON51_down` | AROON(timeperiod=51) | x / 50 − 1 | Số bar kể từ đỉnh và từ đáy gần nhất |
| 60 | `momentum__AROON51_up` | AROON(timeperiod=51) | x / 50 − 1 | Số bar kể từ đỉnh và từ đáy gần nhất |
| 61 | `momentum__AROONOSC51` | AROONOSC(timeperiod=51) | x / 100 | Hiệu giữa Aroon up và Aroon down |
| 62 | `momentum__IMI51` | IMI(timeperiod=51) | x / 50 − 1 | Intraday Momentum Index — RSI tính trên thân nến thay vì giá đóng cửa |
| 63 | `momentum__STOCHRSI51_k` | STOCHRSI(timeperiod=51) | x / 50 − 1 | Stochastic áp lên RSI thay vì lên giá |
| 64 | `momentum__STOCHRSI51_d` | STOCHRSI(timeperiod=51) | x / 50 − 1 | Stochastic áp lên RSI thay vì lên giá |
| 65 | `momentum__RSI102` | RSI(timeperiod=102) | x / 50 − 1 | Chỉ số sức mạnh tương đối (làm mượt Wilder) |
| 66 | `momentum__MOM102` | MOM(timeperiod=102) | x / close | Động lượng thô: C − C[−n] |
| 67 | `momentum__ROCP102` | ROCP(timeperiod=102) | giữ nguyên | Tỷ lệ thay đổi giá qua n bar |
| 68 | `momentum__CCI102` | CCI(timeperiod=102) | x / 100 | Commodity Channel Index — độ lệch khỏi giá điển hình, không bị chặn |
| 69 | `momentum__MFI102` | MFI(timeperiod=102) | x / 50 − 1 | Money Flow Index — RSI có trọng số khối lượng |
| 70 | `momentum__ADX102` | ADX(timeperiod=102) | x / 50 − 1 | Cường độ xu thế, không phân biệt chiều |
| 71 | `momentum__ADXR102` | ADXR(timeperiod=102) | x / 50 − 1 | ADX đã làm mượt thêm một lớp |
| 72 | `momentum__DX102` | DX(timeperiod=102) | x / 50 − 1 | Chỉ số hướng — thành phần thô của ADX |
| 73 | `momentum__PLUS_DI102` | PLUS_DI(timeperiod=102) | x / 50 − 1 | Chỉ số hướng lên |
| 74 | `momentum__MINUS_DI102` | MINUS_DI(timeperiod=102) | x / 50 − 1 | Chỉ số hướng xuống |
| 75 | `momentum__PLUS_DM102` | PLUS_DM(timeperiod=102) | x / close | Động lượng hướng lên thô, đơn vị điểm giá |
| 76 | `momentum__MINUS_DM102` | MINUS_DM(timeperiod=102) | x / close | Động lượng hướng xuống thô, đơn vị điểm giá |
| 77 | `momentum__AROON102_down` | AROON(timeperiod=102) | x / 50 − 1 | Số bar kể từ đỉnh và từ đáy gần nhất |
| 78 | `momentum__AROON102_up` | AROON(timeperiod=102) | x / 50 − 1 | Số bar kể từ đỉnh và từ đáy gần nhất |
| 79 | `momentum__AROONOSC102` | AROONOSC(timeperiod=102) | x / 100 | Hiệu giữa Aroon up và Aroon down |
| 80 | `momentum__IMI102` | IMI(timeperiod=102) | x / 50 − 1 | Intraday Momentum Index — RSI tính trên thân nến thay vì giá đóng cửa |
| 81 | `momentum__STOCHRSI102_k` | STOCHRSI(timeperiod=102) | x / 50 − 1 | Stochastic áp lên RSI thay vì lên giá |
| 82 | `momentum__STOCHRSI102_d` | STOCHRSI(timeperiod=102) | x / 50 − 1 | Stochastic áp lên RSI thay vì lên giá |
| 83 | `momentum__RSI255` | RSI(timeperiod=255) | x / 50 − 1 | Chỉ số sức mạnh tương đối (làm mượt Wilder) |
| 84 | `momentum__MOM255` | MOM(timeperiod=255) | x / close | Động lượng thô: C − C[−n] |
| 85 | `momentum__ROCP255` | ROCP(timeperiod=255) | giữ nguyên | Tỷ lệ thay đổi giá qua n bar |
| 86 | `momentum__CCI255` | CCI(timeperiod=255) | x / 100 | Commodity Channel Index — độ lệch khỏi giá điển hình, không bị chặn |
| 87 | `momentum__MFI255` | MFI(timeperiod=255) | x / 50 − 1 | Money Flow Index — RSI có trọng số khối lượng |
| 88 | `momentum__ADX255` | ADX(timeperiod=255) | x / 50 − 1 | Cường độ xu thế, không phân biệt chiều |
| 89 | `momentum__ADXR255` | ADXR(timeperiod=255) | x / 50 − 1 | ADX đã làm mượt thêm một lớp |
| 90 | `momentum__DX255` | DX(timeperiod=255) | x / 50 − 1 | Chỉ số hướng — thành phần thô của ADX |
| 91 | `momentum__PLUS_DI255` | PLUS_DI(timeperiod=255) | x / 50 − 1 | Chỉ số hướng lên |
| 92 | `momentum__MINUS_DI255` | MINUS_DI(timeperiod=255) | x / 50 − 1 | Chỉ số hướng xuống |
| 93 | `momentum__PLUS_DM255` | PLUS_DM(timeperiod=255) | x / close | Động lượng hướng lên thô, đơn vị điểm giá |
| 94 | `momentum__MINUS_DM255` | MINUS_DM(timeperiod=255) | x / close | Động lượng hướng xuống thô, đơn vị điểm giá |
| 95 | `momentum__AROON255_down` | AROON(timeperiod=255) | x / 50 − 1 | Số bar kể từ đỉnh và từ đáy gần nhất |
| 96 | `momentum__AROON255_up` | AROON(timeperiod=255) | x / 50 − 1 | Số bar kể từ đỉnh và từ đáy gần nhất |
| 97 | `momentum__AROONOSC255` | AROONOSC(timeperiod=255) | x / 100 | Hiệu giữa Aroon up và Aroon down |
| 98 | `momentum__IMI255` | IMI(timeperiod=255) | x / 50 − 1 | Intraday Momentum Index — RSI tính trên thân nến thay vì giá đóng cửa |
| 99 | `momentum__STOCHRSI255_k` | STOCHRSI(timeperiod=255) | x / 50 − 1 | Stochastic áp lên RSI thay vì lên giá |
| 100 | `momentum__STOCHRSI255_d` | STOCHRSI(timeperiod=255) | x / 50 − 1 | Stochastic áp lên RSI thay vì lên giá |
| 101 | `momentum__TRIX24` | TRIX(timeperiod=24) | x / 100 | Tỷ lệ thay đổi của EMA ba lớp |
| 102 | `momentum__TRIX51` | TRIX(timeperiod=51) | x / 100 | Tỷ lệ thay đổi của EMA ba lớp |
| 103 | `momentum__TRIX102` | TRIX(timeperiod=102) | x / 100 | Tỷ lệ thay đổi của EMA ba lớp |
| 104 | `momentum__TRIX255` | TRIX(timeperiod=255) | x / 100 | Tỷ lệ thay đổi của EMA ba lớp |
| 105 | `momentum__MACD_6_12_macd` | MACD(fastperiod=6, slowperiod=12, signalperiod=5) | x / close | Hiệu hai EMA, kèm đường tín hiệu và histogram |
| 106 | `momentum__MACD_6_12_signal` | MACD(fastperiod=6, slowperiod=12, signalperiod=5) | x / close | Hiệu hai EMA, kèm đường tín hiệu và histogram |
| 107 | `momentum__MACD_6_12_hist` | MACD(fastperiod=6, slowperiod=12, signalperiod=5) | x / close | Hiệu hai EMA, kèm đường tín hiệu và histogram |
| 108 | `momentum__APO_6_12` | APO(fastperiod=6, slowperiod=12) | x / close | Hiệu tuyệt đối hai trung bình động, đơn vị điểm giá |
| 109 | `momentum__MACD_12_26_macd` | MACD(fastperiod=12, slowperiod=26, signalperiod=9) | x / close | Hiệu hai EMA, kèm đường tín hiệu và histogram |
| 110 | `momentum__MACD_12_26_signal` | MACD(fastperiod=12, slowperiod=26, signalperiod=9) | x / close | Hiệu hai EMA, kèm đường tín hiệu và histogram |
| 111 | `momentum__MACD_12_26_hist` | MACD(fastperiod=12, slowperiod=26, signalperiod=9) | x / close | Hiệu hai EMA, kèm đường tín hiệu và histogram |
| 112 | `momentum__APO_12_26` | APO(fastperiod=12, slowperiod=26) | x / close | Hiệu tuyệt đối hai trung bình động, đơn vị điểm giá |
| 113 | `momentum__MACD_24_51_macd` | MACD(fastperiod=24, slowperiod=51, signalperiod=18) | x / close | Hiệu hai EMA, kèm đường tín hiệu và histogram |
| 114 | `momentum__MACD_24_51_signal` | MACD(fastperiod=24, slowperiod=51, signalperiod=18) | x / close | Hiệu hai EMA, kèm đường tín hiệu và histogram |
| 115 | `momentum__MACD_24_51_hist` | MACD(fastperiod=24, slowperiod=51, signalperiod=18) | x / close | Hiệu hai EMA, kèm đường tín hiệu và histogram |
| 116 | `momentum__APO_24_51` | APO(fastperiod=24, slowperiod=51) | x / close | Hiệu tuyệt đối hai trung bình động, đơn vị điểm giá |
| 117 | `momentum__MACD_51_102_macd` | MACD(fastperiod=51, slowperiod=102, signalperiod=36) | x / close | Hiệu hai EMA, kèm đường tín hiệu và histogram |
| 118 | `momentum__MACD_51_102_signal` | MACD(fastperiod=51, slowperiod=102, signalperiod=36) | x / close | Hiệu hai EMA, kèm đường tín hiệu và histogram |
| 119 | `momentum__MACD_51_102_hist` | MACD(fastperiod=51, slowperiod=102, signalperiod=36) | x / close | Hiệu hai EMA, kèm đường tín hiệu và histogram |
| 120 | `momentum__APO_51_102` | APO(fastperiod=51, slowperiod=102) | x / close | Hiệu tuyệt đối hai trung bình động, đơn vị điểm giá |
| 121 | `momentum__BOP` | BOP() | giữ nguyên | Balance of Power: (C−O)/(H−L) |
| 122 | `momentum__ULTOSC` | ULTOSC(timeperiod1=7, timeperiod2=14, timeperiod3=28) | x / 50 − 1 | Ultimate Oscillator — ghép ba khung thời gian |
| 123 | `momentum__ULTOSCslow` | ULTOSC(timeperiod1=12, timeperiod2=51, timeperiod3=102) | x / 50 − 1 | Ultimate Oscillator — ghép ba khung thời gian |
| 124 | `momentum__STOCH5_k` | STOCH(fastk_period=5, slowk_period=3, slowd_period=3) | x / 50 − 1 | Stochastic %K/%D đã làm mượt |
| 125 | `momentum__STOCH5_d` | STOCH(fastk_period=5, slowk_period=3, slowd_period=3) | x / 50 − 1 | Stochastic %K/%D đã làm mượt |
| 126 | `momentum__STOCHF5_k` | STOCHF(fastk_period=5, fastd_period=3) | x / 50 − 1 | Stochastic nhanh, không làm mượt %K |
| 127 | `momentum__STOCH14_k` | STOCH(fastk_period=14, slowk_period=3, slowd_period=3) | x / 50 − 1 | Stochastic %K/%D đã làm mượt |
| 128 | `momentum__STOCH14_d` | STOCH(fastk_period=14, slowk_period=3, slowd_period=3) | x / 50 − 1 | Stochastic %K/%D đã làm mượt |
| 129 | `momentum__STOCHF14_k` | STOCHF(fastk_period=14, fastd_period=3) | x / 50 − 1 | Stochastic nhanh, không làm mượt %K |
| 130 | `momentum__STOCH51_k` | STOCH(fastk_period=51, slowk_period=5, slowd_period=5) | x / 50 − 1 | Stochastic %K/%D đã làm mượt |
| 131 | `momentum__STOCH51_d` | STOCH(fastk_period=51, slowk_period=5, slowd_period=5) | x / 50 − 1 | Stochastic %K/%D đã làm mượt |

## `overlap` — Trung bình động và đường bao  (113 cột)

| # | Cột | Nguồn | Công thức / chuẩn hoá | Ý nghĩa |
|---:|---|---|---|---|
| 1 | `overlap__SMA6` | SMA(timeperiod=6) | log(x / close) | Trung bình động giản đơn |
| 2 | `overlap__EMA6` | EMA(timeperiod=6) | log(x / close) | Trung bình động luỹ thừa |
| 3 | `overlap__WMA6` | WMA(timeperiod=6) | log(x / close) | Trung bình động trọng số tuyến tính |
| 4 | `overlap__WMA6_slope` | WMA(timeperiod=6) | log(x / x[−1]) | Độ dốc của WMA — xu thế của chính đường trung bình, tách khỏi khoảng cách giá-đến-đường |
| 5 | `overlap__DEMA6` | DEMA(timeperiod=6) | log(x / close) | Trung bình động kép — bám giá sát hơn EMA cùng chu kỳ |
| 6 | `overlap__DEMA6_slope` | DEMA(timeperiod=6) | log(x / x[−1]) | Độ dốc của DEMA — xu thế của chính đường trung bình, tách khỏi khoảng cách giá-đến-đường |
| 7 | `overlap__TEMA6` | TEMA(timeperiod=6) | log(x / close) | Trung bình động ba lớp — độ trễ thấp nhất họ EMA |
| 8 | `overlap__TEMA6_slope` | TEMA(timeperiod=6) | log(x / x[−1]) | Độ dốc của TEMA — xu thế của chính đường trung bình, tách khỏi khoảng cách giá-đến-đường |
| 9 | `overlap__TRIMA6` | TRIMA(timeperiod=6) | log(x / close) | Trung bình động tam giác — trọng số nặng ở giữa cửa sổ |
| 10 | `overlap__TRIMA6_slope` | TRIMA(timeperiod=6) | log(x / x[−1]) | Độ dốc của TRIMA — xu thế của chính đường trung bình, tách khỏi khoảng cách giá-đến-đường |
| 11 | `overlap__KAMA6` | KAMA(timeperiod=6) | log(x / close) | Trung bình động thích nghi Kaufman — nhanh khi xu thế sạch, chậm khi đi ngang |
| 12 | `overlap__KAMA6_slope` | KAMA(timeperiod=6) | log(x / x[−1]) | Độ dốc của KAMA — xu thế của chính đường trung bình, tách khỏi khoảng cách giá-đến-đường |
| 13 | `overlap__T36` | T3(timeperiod=6) | log(x / close) | Trung bình động T3 Tillson — mượt hơn EMA với cùng độ trễ |
| 14 | `overlap__T36_slope` | T3(timeperiod=6) | log(x / x[−1]) | Độ dốc của T3 — xu thế của chính đường trung bình, tách khỏi khoảng cách giá-đến-đường |
| 15 | `overlap__MIDPOINT6` | MIDPOINT(timeperiod=6) | log(x / close) | Trung điểm giữa giá đóng cửa cao nhất và thấp nhất trong cửa sổ |
| 16 | `overlap__MIDPOINT6_slope` | MIDPOINT(timeperiod=6) | log(x / x[−1]) | Độ dốc của MIDPOINT — xu thế của chính đường trung bình, tách khỏi khoảng cách giá-đến-đường |
| 17 | `overlap__MIDPRICE6` | MIDPRICE(timeperiod=6) | log(x / close) | Trung điểm giữa đỉnh và đáy trong cửa sổ |
| 18 | `overlap__SMA12` | SMA(timeperiod=12) | log(x / close) | Trung bình động giản đơn |
| 19 | `overlap__EMA12` | EMA(timeperiod=12) | log(x / close) | Trung bình động luỹ thừa |
| 20 | `overlap__WMA12` | WMA(timeperiod=12) | log(x / close) | Trung bình động trọng số tuyến tính |
| 21 | `overlap__WMA12_slope` | WMA(timeperiod=12) | log(x / x[−1]) | Độ dốc của WMA — xu thế của chính đường trung bình, tách khỏi khoảng cách giá-đến-đường |
| 22 | `overlap__DEMA12` | DEMA(timeperiod=12) | log(x / close) | Trung bình động kép — bám giá sát hơn EMA cùng chu kỳ |
| 23 | `overlap__DEMA12_slope` | DEMA(timeperiod=12) | log(x / x[−1]) | Độ dốc của DEMA — xu thế của chính đường trung bình, tách khỏi khoảng cách giá-đến-đường |
| 24 | `overlap__TEMA12` | TEMA(timeperiod=12) | log(x / close) | Trung bình động ba lớp — độ trễ thấp nhất họ EMA |
| 25 | `overlap__TEMA12_slope` | TEMA(timeperiod=12) | log(x / x[−1]) | Độ dốc của TEMA — xu thế của chính đường trung bình, tách khỏi khoảng cách giá-đến-đường |
| 26 | `overlap__TRIMA12` | TRIMA(timeperiod=12) | log(x / close) | Trung bình động tam giác — trọng số nặng ở giữa cửa sổ |
| 27 | `overlap__TRIMA12_slope` | TRIMA(timeperiod=12) | log(x / x[−1]) | Độ dốc của TRIMA — xu thế của chính đường trung bình, tách khỏi khoảng cách giá-đến-đường |
| 28 | `overlap__KAMA12` | KAMA(timeperiod=12) | log(x / close) | Trung bình động thích nghi Kaufman — nhanh khi xu thế sạch, chậm khi đi ngang |
| 29 | `overlap__KAMA12_slope` | KAMA(timeperiod=12) | log(x / x[−1]) | Độ dốc của KAMA — xu thế của chính đường trung bình, tách khỏi khoảng cách giá-đến-đường |
| 30 | `overlap__T312` | T3(timeperiod=12) | log(x / close) | Trung bình động T3 Tillson — mượt hơn EMA với cùng độ trễ |
| 31 | `overlap__T312_slope` | T3(timeperiod=12) | log(x / x[−1]) | Độ dốc của T3 — xu thế của chính đường trung bình, tách khỏi khoảng cách giá-đến-đường |
| 32 | `overlap__MIDPOINT12` | MIDPOINT(timeperiod=12) | log(x / close) | Trung điểm giữa giá đóng cửa cao nhất và thấp nhất trong cửa sổ |
| 33 | `overlap__MIDPOINT12_slope` | MIDPOINT(timeperiod=12) | log(x / x[−1]) | Độ dốc của MIDPOINT — xu thế của chính đường trung bình, tách khỏi khoảng cách giá-đến-đường |
| 34 | `overlap__MIDPRICE12` | MIDPRICE(timeperiod=12) | log(x / close) | Trung điểm giữa đỉnh và đáy trong cửa sổ |
| 35 | `overlap__SMA24` | SMA(timeperiod=24) | log(x / close) | Trung bình động giản đơn |
| 36 | `overlap__EMA24` | EMA(timeperiod=24) | log(x / close) | Trung bình động luỹ thừa |
| 37 | `overlap__WMA24` | WMA(timeperiod=24) | log(x / close) | Trung bình động trọng số tuyến tính |
| 38 | `overlap__DEMA24` | DEMA(timeperiod=24) | log(x / close) | Trung bình động kép — bám giá sát hơn EMA cùng chu kỳ |
| 39 | `overlap__DEMA24_slope` | DEMA(timeperiod=24) | log(x / x[−1]) | Độ dốc của DEMA — xu thế của chính đường trung bình, tách khỏi khoảng cách giá-đến-đường |
| 40 | `overlap__TEMA24` | TEMA(timeperiod=24) | log(x / close) | Trung bình động ba lớp — độ trễ thấp nhất họ EMA |
| 41 | `overlap__TEMA24_slope` | TEMA(timeperiod=24) | log(x / x[−1]) | Độ dốc của TEMA — xu thế của chính đường trung bình, tách khỏi khoảng cách giá-đến-đường |
| 42 | `overlap__TRIMA24` | TRIMA(timeperiod=24) | log(x / close) | Trung bình động tam giác — trọng số nặng ở giữa cửa sổ |
| 43 | `overlap__TRIMA24_slope` | TRIMA(timeperiod=24) | log(x / x[−1]) | Độ dốc của TRIMA — xu thế của chính đường trung bình, tách khỏi khoảng cách giá-đến-đường |
| 44 | `overlap__KAMA24` | KAMA(timeperiod=24) | log(x / close) | Trung bình động thích nghi Kaufman — nhanh khi xu thế sạch, chậm khi đi ngang |
| 45 | `overlap__KAMA24_slope` | KAMA(timeperiod=24) | log(x / x[−1]) | Độ dốc của KAMA — xu thế của chính đường trung bình, tách khỏi khoảng cách giá-đến-đường |
| 46 | `overlap__T324` | T3(timeperiod=24) | log(x / close) | Trung bình động T3 Tillson — mượt hơn EMA với cùng độ trễ |
| 47 | `overlap__T324_slope` | T3(timeperiod=24) | log(x / x[−1]) | Độ dốc của T3 — xu thế của chính đường trung bình, tách khỏi khoảng cách giá-đến-đường |
| 48 | `overlap__MIDPOINT24` | MIDPOINT(timeperiod=24) | log(x / close) | Trung điểm giữa giá đóng cửa cao nhất và thấp nhất trong cửa sổ |
| 49 | `overlap__MIDPOINT24_slope` | MIDPOINT(timeperiod=24) | log(x / x[−1]) | Độ dốc của MIDPOINT — xu thế của chính đường trung bình, tách khỏi khoảng cách giá-đến-đường |
| 50 | `overlap__MIDPRICE24` | MIDPRICE(timeperiod=24) | log(x / close) | Trung điểm giữa đỉnh và đáy trong cửa sổ |
| 51 | `overlap__SMA51` | SMA(timeperiod=51) | log(x / close) | Trung bình động giản đơn |
| 52 | `overlap__EMA51` | EMA(timeperiod=51) | log(x / close) | Trung bình động luỹ thừa |
| 53 | `overlap__WMA51` | WMA(timeperiod=51) | log(x / close) | Trung bình động trọng số tuyến tính |
| 54 | `overlap__DEMA51` | DEMA(timeperiod=51) | log(x / close) | Trung bình động kép — bám giá sát hơn EMA cùng chu kỳ |
| 55 | `overlap__DEMA51_slope` | DEMA(timeperiod=51) | log(x / x[−1]) | Độ dốc của DEMA — xu thế của chính đường trung bình, tách khỏi khoảng cách giá-đến-đường |
| 56 | `overlap__TEMA51` | TEMA(timeperiod=51) | log(x / close) | Trung bình động ba lớp — độ trễ thấp nhất họ EMA |
| 57 | `overlap__TEMA51_slope` | TEMA(timeperiod=51) | log(x / x[−1]) | Độ dốc của TEMA — xu thế của chính đường trung bình, tách khỏi khoảng cách giá-đến-đường |
| 58 | `overlap__TRIMA51` | TRIMA(timeperiod=51) | log(x / close) | Trung bình động tam giác — trọng số nặng ở giữa cửa sổ |
| 59 | `overlap__TRIMA51_slope` | TRIMA(timeperiod=51) | log(x / x[−1]) | Độ dốc của TRIMA — xu thế của chính đường trung bình, tách khỏi khoảng cách giá-đến-đường |
| 60 | `overlap__KAMA51` | KAMA(timeperiod=51) | log(x / close) | Trung bình động thích nghi Kaufman — nhanh khi xu thế sạch, chậm khi đi ngang |
| 61 | `overlap__KAMA51_slope` | KAMA(timeperiod=51) | log(x / x[−1]) | Độ dốc của KAMA — xu thế của chính đường trung bình, tách khỏi khoảng cách giá-đến-đường |
| 62 | `overlap__T351` | T3(timeperiod=51) | log(x / close) | Trung bình động T3 Tillson — mượt hơn EMA với cùng độ trễ |
| 63 | `overlap__T351_slope` | T3(timeperiod=51) | log(x / x[−1]) | Độ dốc của T3 — xu thế của chính đường trung bình, tách khỏi khoảng cách giá-đến-đường |
| 64 | `overlap__MIDPOINT51` | MIDPOINT(timeperiod=51) | log(x / close) | Trung điểm giữa giá đóng cửa cao nhất và thấp nhất trong cửa sổ |
| 65 | `overlap__MIDPOINT51_slope` | MIDPOINT(timeperiod=51) | log(x / x[−1]) | Độ dốc của MIDPOINT — xu thế của chính đường trung bình, tách khỏi khoảng cách giá-đến-đường |
| 66 | `overlap__MIDPRICE51` | MIDPRICE(timeperiod=51) | log(x / close) | Trung điểm giữa đỉnh và đáy trong cửa sổ |
| 67 | `overlap__SMA102` | SMA(timeperiod=102) | log(x / close) | Trung bình động giản đơn |
| 68 | `overlap__EMA102` | EMA(timeperiod=102) | log(x / close) | Trung bình động luỹ thừa |
| 69 | `overlap__WMA102` | WMA(timeperiod=102) | log(x / close) | Trung bình động trọng số tuyến tính |
| 70 | `overlap__DEMA102` | DEMA(timeperiod=102) | log(x / close) | Trung bình động kép — bám giá sát hơn EMA cùng chu kỳ |
| 71 | `overlap__DEMA102_slope` | DEMA(timeperiod=102) | log(x / x[−1]) | Độ dốc của DEMA — xu thế của chính đường trung bình, tách khỏi khoảng cách giá-đến-đường |
| 72 | `overlap__TEMA102` | TEMA(timeperiod=102) | log(x / close) | Trung bình động ba lớp — độ trễ thấp nhất họ EMA |
| 73 | `overlap__TEMA102_slope` | TEMA(timeperiod=102) | log(x / x[−1]) | Độ dốc của TEMA — xu thế của chính đường trung bình, tách khỏi khoảng cách giá-đến-đường |
| 74 | `overlap__TRIMA102` | TRIMA(timeperiod=102) | log(x / close) | Trung bình động tam giác — trọng số nặng ở giữa cửa sổ |
| 75 | `overlap__KAMA102` | KAMA(timeperiod=102) | log(x / close) | Trung bình động thích nghi Kaufman — nhanh khi xu thế sạch, chậm khi đi ngang |
| 76 | `overlap__KAMA102_slope` | KAMA(timeperiod=102) | log(x / x[−1]) | Độ dốc của KAMA — xu thế của chính đường trung bình, tách khỏi khoảng cách giá-đến-đường |
| 77 | `overlap__T3102` | T3(timeperiod=102) | log(x / close) | Trung bình động T3 Tillson — mượt hơn EMA với cùng độ trễ |
| 78 | `overlap__T3102_slope` | T3(timeperiod=102) | log(x / x[−1]) | Độ dốc của T3 — xu thế của chính đường trung bình, tách khỏi khoảng cách giá-đến-đường |
| 79 | `overlap__MIDPOINT102` | MIDPOINT(timeperiod=102) | log(x / close) | Trung điểm giữa giá đóng cửa cao nhất và thấp nhất trong cửa sổ |
| 80 | `overlap__MIDPOINT102_slope` | MIDPOINT(timeperiod=102) | log(x / x[−1]) | Độ dốc của MIDPOINT — xu thế của chính đường trung bình, tách khỏi khoảng cách giá-đến-đường |
| 81 | `overlap__MIDPRICE102` | MIDPRICE(timeperiod=102) | log(x / close) | Trung điểm giữa đỉnh và đáy trong cửa sổ |
| 82 | `overlap__SMA255` | SMA(timeperiod=255) | log(x / close) | Trung bình động giản đơn |
| 83 | `overlap__EMA255` | EMA(timeperiod=255) | log(x / close) | Trung bình động luỹ thừa |
| 84 | `overlap__WMA255` | WMA(timeperiod=255) | log(x / close) | Trung bình động trọng số tuyến tính |
| 85 | `overlap__DEMA255` | DEMA(timeperiod=255) | log(x / close) | Trung bình động kép — bám giá sát hơn EMA cùng chu kỳ |
| 86 | `overlap__DEMA255_slope` | DEMA(timeperiod=255) | log(x / x[−1]) | Độ dốc của DEMA — xu thế của chính đường trung bình, tách khỏi khoảng cách giá-đến-đường |
| 87 | `overlap__TEMA255` | TEMA(timeperiod=255) | log(x / close) | Trung bình động ba lớp — độ trễ thấp nhất họ EMA |
| 88 | `overlap__TEMA255_slope` | TEMA(timeperiod=255) | log(x / x[−1]) | Độ dốc của TEMA — xu thế của chính đường trung bình, tách khỏi khoảng cách giá-đến-đường |
| 89 | `overlap__TRIMA255` | TRIMA(timeperiod=255) | log(x / close) | Trung bình động tam giác — trọng số nặng ở giữa cửa sổ |
| 90 | `overlap__TRIMA255_slope` | TRIMA(timeperiod=255) | log(x / x[−1]) | Độ dốc của TRIMA — xu thế của chính đường trung bình, tách khỏi khoảng cách giá-đến-đường |
| 91 | `overlap__KAMA255` | KAMA(timeperiod=255) | log(x / close) | Trung bình động thích nghi Kaufman — nhanh khi xu thế sạch, chậm khi đi ngang |
| 92 | `overlap__KAMA255_slope` | KAMA(timeperiod=255) | log(x / x[−1]) | Độ dốc của KAMA — xu thế của chính đường trung bình, tách khỏi khoảng cách giá-đến-đường |
| 93 | `overlap__T3255` | T3(timeperiod=255) | log(x / close) | Trung bình động T3 Tillson — mượt hơn EMA với cùng độ trễ |
| 94 | `overlap__T3255_slope` | T3(timeperiod=255) | log(x / x[−1]) | Độ dốc của T3 — xu thế của chính đường trung bình, tách khỏi khoảng cách giá-đến-đường |
| 95 | `overlap__MIDPOINT255` | MIDPOINT(timeperiod=255) | log(x / close) | Trung điểm giữa giá đóng cửa cao nhất và thấp nhất trong cửa sổ |
| 96 | `overlap__MIDPOINT255_slope` | MIDPOINT(timeperiod=255) | log(x / x[−1]) | Độ dốc của MIDPOINT — xu thế của chính đường trung bình, tách khỏi khoảng cách giá-đến-đường |
| 97 | `overlap__MIDPRICE255` | MIDPRICE(timeperiod=255) | log(x / close) | Trung điểm giữa đỉnh và đáy trong cửa sổ |
| 98 | `overlap__BBANDS24_upper` | BBANDS(timeperiod=24, nbdevup=2.0, nbdevdn=2.0) | log(x / close) | Dải Bollinger — trung bình cộng/trừ 2 độ lệch chuẩn |
| 99 | `overlap__BBANDS24_lower` | BBANDS(timeperiod=24, nbdevup=2.0, nbdevdn=2.0) | log(x / close) | Dải Bollinger — trung bình cộng/trừ 2 độ lệch chuẩn |
| 100 | `overlap__ACCBANDS24_upper` | ACCBANDS(timeperiod=24) | log(x / close) | Dải Acceleration — biên độ giãn theo (H−L)/(H+L) |
| 101 | `overlap__ACCBANDS24_lower` | ACCBANDS(timeperiod=24) | log(x / close) | Dải Acceleration — biên độ giãn theo (H−L)/(H+L) |
| 102 | `overlap__BBANDS51_upper` | BBANDS(timeperiod=51, nbdevup=2.0, nbdevdn=2.0) | log(x / close) | Dải Bollinger — trung bình cộng/trừ 2 độ lệch chuẩn |
| 103 | `overlap__BBANDS51_lower` | BBANDS(timeperiod=51, nbdevup=2.0, nbdevdn=2.0) | log(x / close) | Dải Bollinger — trung bình cộng/trừ 2 độ lệch chuẩn |
| 104 | `overlap__ACCBANDS51_upper` | ACCBANDS(timeperiod=51) | log(x / close) | Dải Acceleration — biên độ giãn theo (H−L)/(H+L) |
| 105 | `overlap__ACCBANDS51_lower` | ACCBANDS(timeperiod=51) | log(x / close) | Dải Acceleration — biên độ giãn theo (H−L)/(H+L) |
| 106 | `overlap__MAMA_mama` | MAMA() | log(x / close) | MESA Adaptive MA — chu kỳ tự thích nghi theo Hilbert transform |
| 107 | `overlap__MAMA_mama_slope` | MAMA() | log(x / x[−1]) | Độ dốc của MAMA — xu thế của chính đường trung bình, tách khỏi khoảng cách giá-đến-đường |
| 108 | `overlap__MAMA_fama` | MAMA() | log(x / close) | MESA Adaptive MA — chu kỳ tự thích nghi theo Hilbert transform |
| 109 | `overlap__MAMA_fama_slope` | MAMA() | log(x / x[−1]) | Độ dốc của MAMA — xu thế của chính đường trung bình, tách khỏi khoảng cách giá-đến-đường |
| 110 | `overlap__HT_TRENDLINE` | HT_TRENDLINE() | log(x / close) | Đường xu thế tách bằng Hilbert transform |
| 111 | `overlap__HT_TRENDLINE_slope` | HT_TRENDLINE() | log(x / x[−1]) | Độ dốc của HT_TRENDLINE — xu thế của chính đường trung bình, tách khỏi khoảng cách giá-đến-đường |
| 112 | `overlap__SAR` | SAR(acceleration=0.02, maximum=0.2) | log(x / close) | Parabolic SAR — mức dừng lỗ xoay chiều |
| 113 | `overlap__SAREXT_side` | SAREXT() | sign(x) | Parabolic SAR mở rộng; giá trị âm nghĩa là đang ở chiều bán |

## `price` — Giá phái sinh  (2 cột)

| # | Cột | Nguồn | Công thức / chuẩn hoá | Ý nghĩa |
|---:|---|---|---|---|
| 1 | `price__AVGPRICE` | AVGPRICE() | log(x / close) | (O+H+L+C)/4 |
| 2 | `price__MEDPRICE` | MEDPRICE() | log(x / close) | (H+L)/2 |

## `statistic` — Thống kê  (52 cột)

| # | Cột | Nguồn | Công thức / chuẩn hoá | Ý nghĩa |
|---:|---|---|---|---|
| 1 | `statistic__LINEARREG6` | LINEARREG(timeperiod=6) | log(x / close) | Giá trị cuối của đường hồi quy tuyến tính |
| 2 | `statistic__LINEARREG_ANGLE6` | LINEARREG_ANGLE(timeperiod=6) | x / 90 | Góc của đường hồi quy, đơn vị độ |
| 3 | `statistic__LINEARREG_SLOPE6` | LINEARREG_SLOPE(timeperiod=6) | x / close | Độ dốc của đường hồi quy, điểm giá mỗi bar |
| 4 | `statistic__LINEARREG_INTERCEPT6` | LINEARREG_INTERCEPT(timeperiod=6) | log(x / close) | Hệ số chặn của đường hồi quy |
| 5 | `statistic__TSF6` | TSF(timeperiod=6) | log(x / close) | Time Series Forecast — ngoại suy một bước của đường hồi quy |
| 6 | `statistic__STDDEV6` | STDDEV(timeperiod=6) | x / close | Độ lệch chuẩn của giá đóng cửa |
| 7 | `statistic__AVGDEV6` | AVGDEV(timeperiod=6) | x / close | Độ lệch tuyệt đối trung bình |
| 8 | `statistic__BETA6` | BETA(timeperiod=6) | giữ nguyên | Hệ số beta giữa đỉnh và đáy |
| 9 | `statistic__CORREL6` | CORREL(timeperiod=6) | giữ nguyên | Tương quan giữa đỉnh và đáy — độ chặt của biên độ bar |
| 10 | `statistic__LINEARREG12` | LINEARREG(timeperiod=12) | log(x / close) | Giá trị cuối của đường hồi quy tuyến tính |
| 11 | `statistic__LINEARREG_ANGLE12` | LINEARREG_ANGLE(timeperiod=12) | x / 90 | Góc của đường hồi quy, đơn vị độ |
| 12 | `statistic__LINEARREG_SLOPE12` | LINEARREG_SLOPE(timeperiod=12) | x / close | Độ dốc của đường hồi quy, điểm giá mỗi bar |
| 13 | `statistic__LINEARREG_INTERCEPT12` | LINEARREG_INTERCEPT(timeperiod=12) | log(x / close) | Hệ số chặn của đường hồi quy |
| 14 | `statistic__TSF12` | TSF(timeperiod=12) | log(x / close) | Time Series Forecast — ngoại suy một bước của đường hồi quy |
| 15 | `statistic__STDDEV12` | STDDEV(timeperiod=12) | x / close | Độ lệch chuẩn của giá đóng cửa |
| 16 | `statistic__AVGDEV12` | AVGDEV(timeperiod=12) | x / close | Độ lệch tuyệt đối trung bình |
| 17 | `statistic__BETA12` | BETA(timeperiod=12) | giữ nguyên | Hệ số beta giữa đỉnh và đáy |
| 18 | `statistic__CORREL12` | CORREL(timeperiod=12) | giữ nguyên | Tương quan giữa đỉnh và đáy — độ chặt của biên độ bar |
| 19 | `statistic__LINEARREG24` | LINEARREG(timeperiod=24) | log(x / close) | Giá trị cuối của đường hồi quy tuyến tính |
| 20 | `statistic__LINEARREG_ANGLE24` | LINEARREG_ANGLE(timeperiod=24) | x / 90 | Góc của đường hồi quy, đơn vị độ |
| 21 | `statistic__LINEARREG_SLOPE24` | LINEARREG_SLOPE(timeperiod=24) | x / close | Độ dốc của đường hồi quy, điểm giá mỗi bar |
| 22 | `statistic__LINEARREG_INTERCEPT24` | LINEARREG_INTERCEPT(timeperiod=24) | log(x / close) | Hệ số chặn của đường hồi quy |
| 23 | `statistic__TSF24` | TSF(timeperiod=24) | log(x / close) | Time Series Forecast — ngoại suy một bước của đường hồi quy |
| 24 | `statistic__STDDEV24` | STDDEV(timeperiod=24) | x / close | Độ lệch chuẩn của giá đóng cửa |
| 25 | `statistic__AVGDEV24` | AVGDEV(timeperiod=24) | x / close | Độ lệch tuyệt đối trung bình |
| 26 | `statistic__BETA24` | BETA(timeperiod=24) | giữ nguyên | Hệ số beta giữa đỉnh và đáy |
| 27 | `statistic__CORREL24` | CORREL(timeperiod=24) | giữ nguyên | Tương quan giữa đỉnh và đáy — độ chặt của biên độ bar |
| 28 | `statistic__LINEARREG51` | LINEARREG(timeperiod=51) | log(x / close) | Giá trị cuối của đường hồi quy tuyến tính |
| 29 | `statistic__LINEARREG_ANGLE51` | LINEARREG_ANGLE(timeperiod=51) | x / 90 | Góc của đường hồi quy, đơn vị độ |
| 30 | `statistic__LINEARREG_SLOPE51` | LINEARREG_SLOPE(timeperiod=51) | x / close | Độ dốc của đường hồi quy, điểm giá mỗi bar |
| 31 | `statistic__LINEARREG_INTERCEPT51` | LINEARREG_INTERCEPT(timeperiod=51) | log(x / close) | Hệ số chặn của đường hồi quy |
| 32 | `statistic__TSF51` | TSF(timeperiod=51) | log(x / close) | Time Series Forecast — ngoại suy một bước của đường hồi quy |
| 33 | `statistic__STDDEV51` | STDDEV(timeperiod=51) | x / close | Độ lệch chuẩn của giá đóng cửa |
| 34 | `statistic__AVGDEV51` | AVGDEV(timeperiod=51) | x / close | Độ lệch tuyệt đối trung bình |
| 35 | `statistic__BETA51` | BETA(timeperiod=51) | giữ nguyên | Hệ số beta giữa đỉnh và đáy |
| 36 | `statistic__CORREL51` | CORREL(timeperiod=51) | giữ nguyên | Tương quan giữa đỉnh và đáy — độ chặt của biên độ bar |
| 37 | `statistic__LINEARREG102` | LINEARREG(timeperiod=102) | log(x / close) | Giá trị cuối của đường hồi quy tuyến tính |
| 38 | `statistic__LINEARREG_ANGLE102` | LINEARREG_ANGLE(timeperiod=102) | x / 90 | Góc của đường hồi quy, đơn vị độ |
| 39 | `statistic__LINEARREG_SLOPE102` | LINEARREG_SLOPE(timeperiod=102) | x / close | Độ dốc của đường hồi quy, điểm giá mỗi bar |
| 40 | `statistic__LINEARREG_INTERCEPT102` | LINEARREG_INTERCEPT(timeperiod=102) | log(x / close) | Hệ số chặn của đường hồi quy |
| 41 | `statistic__STDDEV102` | STDDEV(timeperiod=102) | x / close | Độ lệch chuẩn của giá đóng cửa |
| 42 | `statistic__AVGDEV102` | AVGDEV(timeperiod=102) | x / close | Độ lệch tuyệt đối trung bình |
| 43 | `statistic__BETA102` | BETA(timeperiod=102) | giữ nguyên | Hệ số beta giữa đỉnh và đáy |
| 44 | `statistic__CORREL102` | CORREL(timeperiod=102) | giữ nguyên | Tương quan giữa đỉnh và đáy — độ chặt của biên độ bar |
| 45 | `statistic__LINEARREG255` | LINEARREG(timeperiod=255) | log(x / close) | Giá trị cuối của đường hồi quy tuyến tính |
| 46 | `statistic__LINEARREG_ANGLE255` | LINEARREG_ANGLE(timeperiod=255) | x / 90 | Góc của đường hồi quy, đơn vị độ |
| 47 | `statistic__LINEARREG_SLOPE255` | LINEARREG_SLOPE(timeperiod=255) | x / close | Độ dốc của đường hồi quy, điểm giá mỗi bar |
| 48 | `statistic__LINEARREG_INTERCEPT255` | LINEARREG_INTERCEPT(timeperiod=255) | log(x / close) | Hệ số chặn của đường hồi quy |
| 49 | `statistic__STDDEV255` | STDDEV(timeperiod=255) | x / close | Độ lệch chuẩn của giá đóng cửa |
| 50 | `statistic__AVGDEV255` | AVGDEV(timeperiod=255) | x / close | Độ lệch tuyệt đối trung bình |
| 51 | `statistic__BETA255` | BETA(timeperiod=255) | giữ nguyên | Hệ số beta giữa đỉnh và đáy |
| 52 | `statistic__CORREL255` | CORREL(timeperiod=255) | giữ nguyên | Tương quan giữa đỉnh và đáy — độ chặt của biên độ bar |

## `volatility` — Biến động  (7 cột)

| # | Cột | Nguồn | Công thức / chuẩn hoá | Ý nghĩa |
|---:|---|---|---|---|
| 1 | `volatility__TRANGE` | TRANGE() | x / close | Biên độ thật của một bar |
| 2 | `volatility__ATR6` | ATR(timeperiod=6) | x / close | Biên độ thật trung bình (làm mượt Wilder) |
| 3 | `volatility__ATR12` | ATR(timeperiod=12) | x / close | Biên độ thật trung bình (làm mượt Wilder) |
| 4 | `volatility__ATR24` | ATR(timeperiod=24) | x / close | Biên độ thật trung bình (làm mượt Wilder) |
| 5 | `volatility__ATR51` | ATR(timeperiod=51) | x / close | Biên độ thật trung bình (làm mượt Wilder) |
| 6 | `volatility__ATR102` | ATR(timeperiod=102) | x / close | Biên độ thật trung bình (làm mượt Wilder) |
| 7 | `volatility__ATR255` | ATR(timeperiod=255) | x / close | Biên độ thật trung bình (làm mượt Wilder) |

## `volume` — Khối lượng  (5 cột)

| # | Cột | Nguồn | Công thức / chuẩn hoá | Ý nghĩa |
|---:|---|---|---|---|
| 1 | `volume__AD` | AD() | diff(x) / khối lượng TB | Đường tích luỹ/phân phối Chaikin |
| 2 | `volume__OBV` | OBV() | diff(x) / khối lượng TB | On Balance Volume |
| 3 | `volume__ADOSC_3_10` | ADOSC(fastperiod=3, slowperiod=10) | x / khối lượng TB | Chaikin Oscillator — hiệu hai EMA của đường A/D |
| 4 | `volume__ADOSC_12_51` | ADOSC(fastperiod=12, slowperiod=51) | x / khối lượng TB | Chaikin Oscillator — hiệu hai EMA của đường A/D |
| 5 | `volume__ADOSC_51_102` | ADOSC(fastperiod=51, slowperiod=102) | x / khối lượng TB | Chaikin Oscillator — hiệu hai EMA của đường A/D |

## `flow` — Dòng lệnh mua/bán  (22 cột)

| # | Cột | Nguồn | Công thức / chuẩn hoá | Ý nghĩa |
|---:|---|---|---|---|
| 1 | `flow__ofi` | laplace | (BUY_VOL − SELL_VOL) / (BUY_VOL + SELL_VOL) | Mất cân bằng dòng lệnh trong bar, −1…1 |
| 2 | `flow__participation` | laplace | (BUY_VOL + SELL_VOL) / VOL | Tỷ lệ lệnh chủ động trên tổng khớp — độ quyết liệt của bar |
| 3 | `flow__buy_px_edge` | laplace | log((BUY_VAL / BUY_VOL) / C) | Giá trung bình bên mua so với giá đóng cửa |
| 4 | `flow__sell_px_edge` | laplace | log((SELL_VAL / SELL_VOL) / C) | Giá trung bình bên bán so với giá đóng cửa |
| 5 | `flow__px_spread` | laplace | buy_px_edge − sell_px_edge | Chênh lệch giá thực hiện giữa hai bên — proxy cho spread |
| 6 | `flow__cum_delta_day` | laplace | Σ(BUY−SELL) / Σ(BUY+SELL), reset mỗi phiên | Delta luỹ kế trong phiên, chuẩn hoá theo hoạt động đã khớp |
| 7 | `flow__ofi_ma6` | laplace | mean(ofi, 6) | Mất cân bằng dòng lệnh làm mượt 6 bar |
| 8 | `flow__ofi_net6` | laplace | Σ(BUY−SELL, 6) / Σ(BUY+SELL, 6) | Delta ròng 6 bar, chuẩn hoá theo tổng hoạt động cùng cửa sổ |
| 9 | `flow__ofi_ma12` | laplace | mean(ofi, 12) | Mất cân bằng dòng lệnh làm mượt 12 bar |
| 10 | `flow__ofi_net12` | laplace | Σ(BUY−SELL, 12) / Σ(BUY+SELL, 12) | Delta ròng 12 bar, chuẩn hoá theo tổng hoạt động cùng cửa sổ |
| 11 | `flow__ofi_ma24` | laplace | mean(ofi, 24) | Mất cân bằng dòng lệnh làm mượt 24 bar |
| 12 | `flow__ofi_net24` | laplace | Σ(BUY−SELL, 24) / Σ(BUY+SELL, 24) | Delta ròng 24 bar, chuẩn hoá theo tổng hoạt động cùng cửa sổ |
| 13 | `flow__ofi_ma51` | laplace | mean(ofi, 51) | Mất cân bằng dòng lệnh làm mượt 51 bar |
| 14 | `flow__ofi_net51` | laplace | Σ(BUY−SELL, 51) / Σ(BUY+SELL, 51) | Delta ròng 51 bar, chuẩn hoá theo tổng hoạt động cùng cửa sổ |
| 15 | `flow__ofi_ma102` | laplace | mean(ofi, 102) | Mất cân bằng dòng lệnh làm mượt 102 bar |
| 16 | `flow__ofi_net102` | laplace | Σ(BUY−SELL, 102) / Σ(BUY+SELL, 102) | Delta ròng 102 bar, chuẩn hoá theo tổng hoạt động cùng cửa sổ |
| 17 | `flow__ofi_ma255` | laplace | mean(ofi, 255) | Mất cân bằng dòng lệnh làm mượt 255 bar |
| 18 | `flow__ofi_net255` | laplace | Σ(BUY−SELL, 255) / Σ(BUY+SELL, 255) | Delta ròng 255 bar, chuẩn hoá theo tổng hoạt động cùng cửa sổ |
| 19 | `flow__active_rel12` | laplace | log(1+BUY+SELL) − trung bình trượt 12 | Cường độ lệnh chủ động so với 12 bar gần nhất |
| 20 | `flow__active_rel51` | laplace | log(1+BUY+SELL) − trung bình trượt 51 | Cường độ lệnh chủ động so với 51 bar gần nhất |
| 21 | `flow__active_rel255` | laplace | log(1+BUY+SELL) − trung bình trượt 255 | Cường độ lệnh chủ động so với 255 bar gần nhất |
| 22 | `flow__flow_price_div` | laplace | sign(ret1) · (−ofi_ma12) | Phân kỳ dòng tiền–giá: giá tăng nhưng dòng tiền bán ròng, hoặc ngược lại |

## `session` — Lịch và vị trí trong phiên  (19 cột)

| # | Cột | Nguồn | Công thức / chuẩn hoá | Ý nghĩa |
|---:|---|---|---|---|
| 1 | `session__day_progress` | laplace | 2·bar_of_day / (số bar phiên trước − 1) − 1 | Tiến độ phiên, −1 đầu phiên đến +1 cuối phiên |
| 2 | `session__is_first_bar` | laplace | 1 tại bar đầu phiên | Cờ đánh dấu mở cửa |
| 3 | `session__is_last_bar` | laplace | 1 khi giờ ≥ 14:45 | Cờ đánh dấu bar ATC, lấy từ lịch giao dịch chứ không từ việc đếm bar |
| 4 | `session__bars_to_close` | laplace | log(1 + số bar còn lại đến 14:45) | Còn bao lâu nữa đến khi đóng phiên |
| 5 | `session__tod_sin` | laplace | sin(2π · phút / 1440) | Giờ trong ngày, thành phần sin |
| 6 | `session__tod_cos` | laplace | cos(2π · phút / 1440) | Giờ trong ngày, thành phần cos |
| 7 | `session__bar_gap` | laplace | log(1 + số phút kể từ bar trước) | Khoảng cách thực tế tới bar trước: 5 bình thường, 90 sau nghỉ trưa, ~1095 qua đêm |
| 8 | `session__after_lunch` | laplace | 1 tại bar đầu tiên sau nghỉ trưa | Cờ đánh dấu mở cửa phiên chiều |
| 9 | `session__dow_sin` | laplace | sin(2π · thứ / 7) | Thứ trong tuần, thành phần sin |
| 10 | `session__dow_cos` | laplace | cos(2π · thứ / 7) | Thứ trong tuần, thành phần cos |
| 11 | `session__is_monday` | laplace | 1 nếu là thứ Hai | Hiệu ứng đầu tuần |
| 12 | `session__is_friday` | laplace | 1 nếu là thứ Sáu | Hiệu ứng cuối tuần |
| 13 | `session__month_sin` | laplace | sin(2π · (tháng−1) / 12) | Tháng trong năm, thành phần sin |
| 14 | `session__month_cos` | laplace | cos(2π · (tháng−1) / 12) | Tháng trong năm, thành phần cos |
| 15 | `session__dom_norm` | laplace | (ngày − 15,5) / 15,5 | Vị trí trong tháng, −1…1 |
| 16 | `session__dte` | laplace | số ngày đến đáo hạn / 30 | VN30F1M xoay vòng theo tháng: gần đáo hạn thì basis và thanh khoản đổi hành vi |
| 17 | `session__dte_inv` | laplace | 1 / (1 + số ngày đến đáo hạn) | Nhấn mạnh những ngày sát đáo hạn |
| 18 | `session__is_expiry_week` | laplace | 1 khi còn ≤ 5 ngày đến đáo hạn | Tuần đáo hạn |
| 19 | `session__is_expiry_day` | laplace | 1 đúng ngày đáo hạn | Ngày đáo hạn — thanh khoản và biến động bất thường |

## `bot` — Đầu vào của hai bot AFL  (25 cột)

| # | Cột | Nguồn | Công thức / chuẩn hoá | Ý nghĩa |
|---:|---|---|---|---|
| 1 | `bot__kespt_st_up` | laplace | log(Up / C) | Băng trên của SuperTrend(3, ATR 28) |
| 2 | `bot__kespt_st_dn` | laplace | log(Dn / C) | Băng dưới của SuperTrend(3, ATR 28) |
| 3 | `bot__kespt_st_line` | laplace | log(đường ST đang hoạt động / C) | Đường SuperTrend hiện hành — chính là mức dừng lỗ của bot |
| 4 | `bot__kespt_st_trend` | laplace | +1 / −1 | Trạng thái xu thế SuperTrend |
| 5 | `bot__kespt_st_dist_atr` | laplace | (C − đường ST) / ATR(28) | Còn bao nhiêu ATR trước khi SuperTrend đảo chiều — đại lượng bot thực sự dựa vào |
| 6 | `bot__kespt_stochk` | laplace | StochK(22, 43) / 50 − 1 | Stochastic %K theo đúng tham số của bot |
| 7 | `bot__kespt_lrsi` | laplace | LinearReg(RSI(22), 54) / 50 − 1 | RSI đã làm phẳng bằng hồi quy tuyến tính |
| 8 | `bot__kespt_lsto` | laplace | LinearReg(StochK(22,43), 54) / 50 − 1 | Stochastic đã làm phẳng bằng hồi quy tuyến tính |
| 9 | `bot__kespt_storsi` | laplace | (3,7·LRSI + LSTO) / 4,7 rồi đổi về −1…1 | Dao động lõi của bot KESPT |
| 10 | `bot__kespt_storsi_ma` | laplace | WMA(STORSI, 34) rồi đổi về −1…1 | Đường tín hiệu của STORSI |
| 11 | `bot__kespt_hiskf` | laplace | (STORSI − STORSIma) / 4,7 / 50 | Histogram KF — giao cắt của nó sinh tín hiệu vào lệnh |
| 12 | `bot__kespt_ema300` | laplace | log(EMA(C, 300) / C) | Bộ lọc xu thế của bot KESPT |
| 13 | `bot__kespt_above_ema` | laplace | sign(C − EMA300) | Giá trên hay dưới bộ lọc xu thế |
| 14 | `bot__kespt_kf_state` | laplace | +1 / −1 | Trạng thái giao cắt KF (Buy1 / Short1) |
| 15 | `bot__kespt_sig_state` | laplace | +1 / 0 / −1 | KF và SuperTrend đã cùng chiều chưa — điều kiện trước khi áp bộ lọc EMA |
| 16 | `bot__roof_hp` | laplace | HighPass(C, 120) / C | Giá đã lọc thông cao — bỏ thành phần xu thế chậm |
| 17 | `bot__roof_filt` | laplace | SuperSmoother(HP, 22) / C | Roofing Filter của Ehlers — dao động lõi của bot Roofing |
| 18 | `bot__roof_signal` | laplace | WMA(Filt, 10) / C | Đường tín hiệu của Roofing Filter |
| 19 | `bot__roof_hist` | laplace | (Filt − Signal) / C | Histogram Roofing — giao cắt sinh tín hiệu vào lệnh |
| 20 | `bot__roof_mom` | laplace | (Filt − Filt[−45]) / C | Động lượng của Roofing Filter |
| 21 | `bot__roof_momz` | laplace | Mom / stdev(Mom, 160) | Momentum thrust dạng z-score — công tắc chính của bot, ngưỡng ±0,72 |
| 22 | `bot__roof_above_ema` | laplace | sign(C − Ref(EMA(C,240), −1)) | Giá trên hay dưới bộ lọc xu thế của Roofing |
| 23 | `bot__roof_open_state` | laplace | +1 / −1 | Trạng thái giao cắt Roofing (openBuy / openShort) |
| 24 | `bot__roof_mom_gate` | laplace | +1 / 0 / −1 | Cổng momentum đã mở chưa và mở về chiều nào |
| 25 | `bot__agree_trend` | laplace | kespt_st_trend · roof_open_state | Hai bot đồng thuận (+1) hay mâu thuẫn (−1) về chiều |

## Cột bị loại ở bước tỉa  (85 cột)

Loại trên tập train: hằng số, gần như luôn bằng 0, hoặc trùng lặp với một cột khác ở mức |corr| ≥ 0,999.

| # | Cột | Lý do |
|---:|---|---|
| 1 | `base__rs255` | trung lap voi base__gk255 |
| 2 | `base__dollar_vol` | trung lap voi base__vol_rel255 |
| 3 | `momentum__CMO6` | trung lap voi momentum__RSI6 |
| 4 | `momentum__MOM6` | trung lap voi base__ret6 |
| 5 | `momentum__ROCP6` | trung lap voi base__ret6 |
| 6 | `momentum__ROCR1006` | trung lap voi base__ret6 |
| 7 | `momentum__WILLR6` | trung lap voi base__pos6 |
| 8 | `momentum__CMO12` | trung lap voi momentum__RSI12 |
| 9 | `momentum__MOM12` | trung lap voi base__ret12 |
| 10 | `momentum__ROCP12` | trung lap voi base__ret12 |
| 11 | `momentum__ROCR10012` | trung lap voi base__ret12 |
| 12 | `momentum__WILLR12` | trung lap voi base__pos12 |
| 13 | `momentum__CMO24` | trung lap voi momentum__RSI24 |
| 14 | `momentum__MOM24` | trung lap voi base__ret24 |
| 15 | `momentum__ROCP24` | trung lap voi base__ret24 |
| 16 | `momentum__ROCR10024` | trung lap voi base__ret24 |
| 17 | `momentum__WILLR24` | trung lap voi base__pos24 |
| 18 | `momentum__CMO51` | trung lap voi momentum__RSI51 |
| 19 | `momentum__MOM51` | trung lap voi base__ret51 |
| 20 | `momentum__ROCP51` | trung lap voi base__ret51 |
| 21 | `momentum__ROCR10051` | trung lap voi base__ret51 |
| 22 | `momentum__WILLR51` | trung lap voi base__pos51 |
| 23 | `momentum__CMO102` | trung lap voi momentum__RSI102 |
| 24 | `momentum__ROCR100102` | trung lap voi momentum__ROCP102 |
| 25 | `momentum__WILLR102` | trung lap voi base__pos102 |
| 26 | `momentum__CMO255` | trung lap voi momentum__RSI255 |
| 27 | `momentum__ROCR100255` | trung lap voi momentum__ROCP255 |
| 28 | `momentum__WILLR255` | trung lap voi base__pos255 |
| 29 | `momentum__PPO_6_12` | trung lap voi momentum__APO_6_12 |
| 30 | `momentum__PPO_12_26` | trung lap voi momentum__APO_12_26 |
| 31 | `momentum__PPO_24_51` | trung lap voi momentum__APO_24_51 |
| 32 | `momentum__PPO_51_102` | trung lap voi momentum__APO_51_102 |
| 33 | `momentum__MACDFIX_macd` | trung lap voi momentum__MACD_12_26_macd |
| 34 | `momentum__MACDFIX_signal` | trung lap voi momentum__MACD_12_26_signal |
| 35 | `momentum__MACDFIX_hist` | trung lap voi momentum__MACD_12_26_hist |
| 36 | `momentum__STOCHF5_d` | trung lap voi momentum__STOCH5_k |
| 37 | `momentum__STOCHF14_d` | trung lap voi momentum__STOCH14_k |
| 38 | `momentum__STOCHF51_k` | trung lap voi base__pos51 |
| 39 | `momentum__STOCHF51_d` | trung lap voi momentum__STOCH51_k |
| 40 | `overlap__SMA6_slope` | trung lap voi base__ret6 |
| 41 | `overlap__EMA6_slope` | trung lap voi overlap__EMA6 |
| 42 | `overlap__SMA12_slope` | trung lap voi base__ret12 |
| 43 | `overlap__EMA12_slope` | trung lap voi overlap__EMA12 |
| 44 | `overlap__SMA24_slope` | trung lap voi base__ret24 |
| 45 | `overlap__EMA24_slope` | trung lap voi overlap__EMA24 |
| 46 | `overlap__WMA24_slope` | trung lap voi overlap__SMA24 |
| 47 | `overlap__SMA51_slope` | trung lap voi base__ret51 |
| 48 | `overlap__EMA51_slope` | trung lap voi overlap__EMA51 |
| 49 | `overlap__WMA51_slope` | trung lap voi overlap__SMA51 |
| 50 | `overlap__SMA102_slope` | trung lap voi momentum__ROCP102 |
| 51 | `overlap__EMA102_slope` | trung lap voi overlap__EMA102 |
| 52 | `overlap__WMA102_slope` | trung lap voi overlap__SMA102 |
| 53 | `overlap__TRIMA102_slope` | trung lap voi momentum__APO_51_102 |
| 54 | `overlap__SMA255_slope` | trung lap voi momentum__ROCP255 |
| 55 | `overlap__EMA255_slope` | trung lap voi overlap__EMA255 |
| 56 | `overlap__WMA255_slope` | trung lap voi overlap__SMA255 |
| 57 | `overlap__BBANDS24_middle` | trung lap voi overlap__SMA24 |
| 58 | `overlap__ACCBANDS24_middle` | trung lap voi overlap__SMA24 |
| 59 | `overlap__BBANDS51_middle` | trung lap voi overlap__SMA51 |
| 60 | `overlap__ACCBANDS51_middle` | trung lap voi overlap__SMA51 |
| 61 | `overlap__SAREXT` | trung lap voi overlap__SAR |
| 62 | `statistic__VAR6` | trung lap voi statistic__STDDEV6 |
| 63 | `statistic__VAR12` | trung lap voi statistic__STDDEV12 |
| 64 | `statistic__VAR24` | trung lap voi statistic__STDDEV24 |
| 65 | `statistic__VAR51` | trung lap voi statistic__STDDEV51 |
| 66 | `statistic__TSF102` | trung lap voi statistic__LINEARREG102 |
| 67 | `statistic__VAR102` | trung lap voi statistic__STDDEV102 |
| 68 | `statistic__TSF255` | trung lap voi statistic__LINEARREG255 |
| 69 | `statistic__VAR255` | trung lap voi statistic__STDDEV255 |
| 70 | `volatility__NATR6` | trung lap voi volatility__ATR6 |
| 71 | `volatility__NATR12` | trung lap voi volatility__ATR12 |
| 72 | `volatility__NATR24` | trung lap voi volatility__ATR24 |
| 73 | `volatility__NATR51` | trung lap voi volatility__ATR51 |
| 74 | `volatility__NATR102` | trung lap voi volatility__ATR102 |
| 75 | `volatility__NATR255` | trung lap voi volatility__ATR255 |
| 76 | `price__TYPPRICE` | trung lap voi price__MEDPRICE |
| 77 | `price__WCLPRICE` | trung lap voi price__MEDPRICE |
| 78 | `flow__ofi_val` | trung lap voi flow__ofi |
| 79 | `session__minute_norm` | trung lap voi session__tod_sin |
| 80 | `bot__kespt_atr28` | trung lap voi volatility__ATR24 |
| 81 | `bot__kespt_rsi22` | trung lap voi momentum__RSI24 |
| 82 | `bot__kespt_ema300_slope` | trung lap voi bot__kespt_ema300 |
| 83 | `bot__roof_ema240` | trung lap voi overlap__EMA255 |
| 84 | `bot__roof_emafilter` | trung lap voi overlap__EMA255 |
| 85 | `bot__roof_ema240_slope` | trung lap voi overlap__EMA255 |
