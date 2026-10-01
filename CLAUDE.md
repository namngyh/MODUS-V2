# CLAUDE.md

Quy tắc làm việc trên repo này. Đọc **cùng với [PROCESS.md](PROCESS.md)** trước khi làm
bất cứ việc gì. Chi tiết kỹ thuật không nằm ở đây:

| Muốn biết | Xem |
|---|---|
| Kiến trúc MODUS 2: các tầng, luồng dữ liệu, quyết định đã chốt | [KIENTRUC.md](KIENTRUC.md) |
| Các nhóm đặc trưng, nguyên tắc chuẩn hoá | [README.md](README.md) |
| Từng cột đặc trưng (sinh tự động, không sửa tay) | [FEATURES.md](FEATURES.md) |
| Quyết định thiết kế và kết quả từng bước | [specs/](specs/) |
| Số lần đã nhìn tập test | [specs/SO-LAN-NHIN-TAP-TEST.md](specs/SO-LAN-NHIN-TAP-TEST.md) |

---

# PHẦN 1 — CÁCH LÀM VIỆC

Phần này ít thay đổi. Phần 2 (cấu trúc dự án) sẽ thay đổi nhiều.

## 1. Người dùng duyệt thì mới thi công

```
thảo luận  →  giải thích dễ hiểu  →  người dùng CHỐT  →  mới được code
```

- **Gửi đề xuất xong thì dừng.** Không code, không sửa file, cho tới khi người dùng trả
  lời, kể cả khi tôi tin chắc phương án nào đúng.
- **Một cuộc thảo luận chưa xong không phải là đồng ý.** Chỉ câu chốt rõ ràng ("làm A",
  "ok sửa đi") mới là duyệt.
- **Việc lớn bàn từng cái một, việc nhỏ gộp lại.** Việc lớn: nhãn, reward, cách chia tập,
  kiến trúc mạng, quy tắc vào/ra lệnh. Việc nhỏ: ngưỡng, chu kỳ, tên cột. Việc nhỏ gộp
  thành một danh sách để duyệt một lượt.
- **Duyệt xong thì khoá phạm vi.** Cần sửa ngoài phạm vi đã duyệt thì dừng lại, báo, và
  chờ duyệt tiếp.

### Sửa lỗi thì không cần hỏi

> **Chỉ có một cách sửa đúng → đó là lỗi, cứ sửa rồi báo lại.**
> **Nhiều cách sửa đều hợp lệ → đó là thiết kế, phải hỏi.**

| Tự sửa, rồi báo | Báo trước, chờ duyệt |
|---|---|
| Sai cú pháp, sai kiểu, lệch chỉ số, chia cho 0 | Lỗi logic mà tôi không chắc 100% |
| Công thức khác với chính tài liệu hoặc docstring của nó | Thứ trông sai nhưng có thể là cố ý |
| Lỗi vô tình thấy khi đang làm việc khác | Cách sửa đụng tới đơn vị, ngưỡng, quy tắc chuẩn hoá |

Sửa gì cũng phải nói rõ, không sửa lặng lẽ.

### Không cần thảo luận trước

Sửa chính tả, sửa tài liệu, refactor không đổi hành vi, vẽ biểu đồ, và **thăm dò rẻ**
trong scratchpad. Nhưng ngay khi kết quả thăm dò được dùng để ra quyết định, nó trở lại
thành quyết định thiết kế và phải thảo luận.

## 2. Giải thích: dễ hiểu trước, kỹ thuật sau

**Viết cho người không cần biết PPO hay TA-Lib là gì.** Dùng hình ảnh và ví dụ thật, hạn
chế tên hàm và thuật ngữ chuyên ngành.

Mọi giải thích viết theo thứ tự này:

1. **Hình dung** — không thuật ngữ. *"Mô hình đang bị mù ở đoạn này"*, *"nhiệt kế tự
   chỉnh về 0 nên quên rằng đang cháy"*. Người đọc phải hiểu **vì sao nó quan trọng**.
2. **Ví dụ bằng số thật của dự án** — *"năm 2022 biến động gấp 7 lần năm 2024"*, không
   phải *"phương sai không đồng nhất"*.
3. **Chi tiết kỹ thuật** — chỉ khi cần cho việc thi công, viết ngắn, đặt sau cùng.

Quy tắc đi kèm:

- **Định nghĩa trước khi dùng.** Ký hiệu hay khái niệm mới phải được giải thích ngay chỗ
  nó xuất hiện lần đầu, kèm **đơn vị** (điểm, bội số ATR, số bar 5 phút…).
- **Ngắn và cụ thể.** Không liệt kê ưu nhược cho đủ mục; chỉ viết kỹ chỗ thật sự quyết
  định.
- **Khi người dùng nói "chưa hiểu"** thì viết lại đơn giản hơn, không viết dài hơn.

## 3. Không bịa — mọi khẳng định phải có bằng chứng

- **Không nói điều gì không có cơ sở.** Mỗi con số, mỗi kết luận phải truy được về một
  phép đo, một bài test, hoặc một dòng code đã đọc.
- **Không chắc thì nói là không chắc, rồi đi kiểm tra.** Chạy thử, đo, đọc code — đừng
  đoán. Chưa kiểm được thì ghi rõ *"chưa có cơ sở"*.
- **Phân biệt ba loại:** đã đo / đã kiểm chứng · giả định · chưa biết. Không biến giả định
  thành sự thật.
- **Không nói "test pass" khi chưa chạy.** Báo đúng mức: đã code · đã test · đã kiểm chứng
  trên dữ liệu thật.
- **Báo cả kết quả xấu.** Thất bại, giả thuyết bị bác, lỗi của chính tôi — ghi lại như
  kết quả tốt.
- **Không đặt ngưỡng từ phép đo hẹp hơn thứ sắp đo.** Đã sai ba lần ở tiêu chí tốc độ
  (spec 004, 005).

## 4. Mỗi đề xuất thiết kế phải có

1. **Vấn đề** — đang quyết định cái gì
2. **Ít nhất hai phương án thật** — phương án thứ hai phải cân nhắc được, không phải bù
   nhìn dựng lên để loại
3. **Khuyến nghị kèm một lý do quyết định**
4. **Điều gì làm tôi đổi ý** — một quan sát cụ thể, đặt trước khi chạy
5. **Rủi ro tôi chưa lượng hoá được** — nêu tên nó
6. **Cái mất khi bỏ phương án kia**

Nhược điểm nói bằng con số khi có thể. Các trục thường phân biệt được phương án:

| Trục | Câu hỏi |
|---|---|
| Quá khớp | Thêm bao nhiêu tham số tự do? |
| Rò rỉ tương lai | Có đường nào từ tương lai về hiện tại? Tham số ước lượng trên tập nào? |
| Đổi chế độ thị trường | Còn đúng ở 2018 / 2020 / 2022 / 2025 không? |
| Tập test | Có tiêu một lần nhìn tập test không? |
| Khi hỏng | Live lệch backtest thì có biết *vì sao* không? |
| Đảo ngược | Bỏ đi tốn gì? |
| Tốc độ | Suy luận có kịp trước khi bar sau đóng không? |

Không cần viết đủ bảy dòng. Hai phương án tốt như nhau thì nói thẳng là hoà.

## 5. Spec trước, code sau

**Bắt buộc có spec** khi đụng tới: đặc trưng (thêm mới hoặc đổi nghĩa/đơn vị), nhãn,
môi trường RL, reward, quy tắc vào/ra lệnh, ranh giới train/valid/test, dữ liệu đầu vào,
hoặc một bất biến. Đây là những chỗ lỗi **không làm chương trình dừng** mà chỉ làm kết
quả đẹp lên một cách sai.

Spec một trang, mẫu ở [specs/TEMPLATE.md](specs/TEMPLATE.md), sáu mục: câu hỏi · vào → ra
kèm đơn vị · vì sao không nhìn tương lai · bất biến · **bài test làm spec thất bại** ·
**tiêu chí chấp nhận đặt trước khi chạy**.

```
thảo luận → người dùng chốt → viết spec → viết test thất bại trước → code tới khi xanh
   → chạy toàn bộ test → cập nhật tài liệu → ghi kết quả vào spec (kể cả khi thất bại)
```

## 6. Chạy thật do người dùng chạy

Huấn luyện đầy đủ, dò siêu tham số, backtest đầy đủ: tôi viết file `.bat`, người dùng
chạy (PROCESS.md mục 14). Tôi chỉ tự chạy test và thử nghiệm ngắn. Việc chạy dài phải có
checkpoint và chạy tiếp được sau khi bị ngắt.

## 7. Không được làm

- Code trước khi người dùng chốt
- Nhìn tập test để chọn mô hình, hay nhìn thêm mà không ghi vào sổ
- Nới ngưỡng hay đổi định nghĩa để một bài test xanh
- Kết luận từ **một** lần chạy
- Báo `reward` như một con số thành tích (xem mục 9)
- Ghi mật khẩu, DSN, token vào code, log hay file commit — chỉ ghi tên biến (`PG_DSN`)
- Commit `data/` và `ohlc_export.csv`
- Nhắc lại chuyện phí và thuế (xem mục 8)

---

# PHẦN 2 — DỰ ÁN

Phần này sẽ thay đổi theo tiến độ. Chi tiết nằm ở README và specs.

## 8. Sản phẩm và quy tắc giao dịch

| | |
|---|---|
| Sản phẩm | **VN30F1M**, nến 5 phút |
| Vị thế | **Một vị thế tại một thời điểm**: long **hoặc** short, không bao giờ mở cả hai cùng lúc |
| Trạng thái | **FLAT** (không có lệnh) · **Đang giữ lệnh** (long hoặc short) |
| Khi FLAT | head **entry** chọn: **LONG · SHORT · SKIP** |
| Khi giữ lệnh | head **exit** chọn: **HOLD · EXIT** |
| Đảo chiều | **Không có.** Muốn đổi chiều thì EXIT ở bar này, về FLAT, rồi entry ở bar sau |
| Phí, thuế | **Làm sau cùng. Không nhắc tới** cho tới khi người dùng mở lại chủ đề này |

Mỗi bar dùng **đúng một** head ra quyết định. Ngoài ra còn head **value** (chấm điểm tình
huống): chỉ dùng lúc học để biết một lệnh lãi là nhờ quyết định đúng hay nhờ thị trường,
không dùng khi giao dịch.

Giá của việc bỏ đảo chiều, đo trên bot KESPT (train + valid): 337 lần đảo trong 1.347 lệnh,
chờ thêm 1 bar mất −72 điểm trong 7,5 năm. Bar bị lỡ đúng chiều 50 % số lần.

**Chưa làm trong code:** code hiện tại (spec 002) vẫn cho đảo chiều trong một bar. Đổi
quy tắc này cần một spec riêng.

## 9. `profit` và `reward` là hai thứ khác nhau

Định nghĩa của người dùng (2026-10-01):

| Từ | Là gì | Gồm | Dùng để |
|---|---|---|---|
| **`profit`** | **Lợi nhuận thật** của mô hình | Lãi/lỗ của từng lệnh, không thêm bớt gì | **Đánh giá.** Phải **chuẩn tuyệt đối**, vì mọi kết luận dựa vào nó |
| **`reward`** | **Điểm của mô hình** — thứ mô hình cố làm cho lớn khi học | **điểm thưởng/phạt + profit + các thành phần thiết kế thêm** | **Huấn luyện** |

**Tất cả tính bằng điểm, không bao giờ quy ra tiền.** Mỗi thành phần của reward được ghi
riêng để biết mô hình được thưởng vì đâu.

**Giá khớp của profit (chốt 2026-10-01):** quyết định ra ở cuối nến *t* thì khớp ở **giá mở
cửa nến *t+1***. Không khớp ở giá đóng cửa nến *t*: giá đó đã qua khi mô hình nhìn thấy
nó. Đo trên train: chênh lệch trong phiên trung bình 0,19 điểm, nhưng qua trưa/qua đêm
trung bình **3,90 điểm**. **Code chưa đổi** (môi trường spec 004 vẫn khớp ở giá đóng cửa)
— cần một spec riêng.

**Thành phần profit trong reward (chốt 2026-10-01): `w_R · R + w_C · C`**, trọng số khai
trong config, **bắt đầu w_R = w_C = ½**.

- **R** = điểm lãi/lỗ ÷ ATR 51 nến **lúc vào lệnh** — so với độ nhảy của phiên gần nhất
- **C** = điểm lãi/lỗ ÷ ATR trung vị **khoảng 1 năm trước** — so với mặt bằng cả năm

Đo trên 860 lệnh KESPT 2018–2022: R cân bằng các năm nhất (năm nặng ÷ nhẹ = 1,38) nhưng
tổng theo năm khớp profit kém (0,225); C khớp tốt hơn (0,746) nhưng chậm một năm (2020
bị thổi lên 1,58); ½R + ½C ở giữa (1,64 · 0,605). Cách nào cho mô hình kiếm nhiều điểm
hơn **chưa biết** — phải thí nghiệm ở phase PPO. Code hiện chỉ có R (spec 004).

`profit` dùng để đánh giá thì luôn là điểm chỉ số.

Hai thứ này **không tỷ lệ với nhau**. Đo trên 1.539 lệnh của bot KESPT: năm 2025 tốt
nhất theo profit nhưng không lọt top 4 theo reward. Nên:

- Báo cáo hiệu quả **luôn bằng profit (điểm)**
- Tiêu chí đánh giá **phải khác** hàm reward, nếu không sẽ không phát hiện được mô hình
  đang lợi dụng kẽ hở của reward
- Đặt tên biến: `_points` = điểm, `_atr` hoặc `_R` = bội số ATR, `reward` = tín hiệu học.
  **Không dùng `pnl` trần** vì nó không cho biết đơn vị

## 10. Ngưỡng nhiễu

Một mô hình **chưa học gì** cũng có thể lãi vài trăm điểm trên tập valid nhờ may mắn. Đo
ở spec 005: 10 mô hình ngẫu nhiên cho trung bình +99 điểm, độ lệch chuẩn 164, cao nhất
+443.

**Con số này đã hết hiệu lực** sau spec 006 (ma trận đặc trưng đổi) và phải đo lại trước
khi so sánh bất cứ thứ gì. Quy tắc vẫn giữ: **nhiều hạt giống mới kết luận được** (ở
spec 005: 5 hạt giống chỉ phát hiện được chênh lệch > 147 điểm).

## 11. Bất biến — mỗi quy tắc có một bài test canh

Không được phá khi chưa thảo luận. Thêm bất biến thì thêm cả dòng ở đây lẫn bài test,
trong cùng một thay đổi.

| # | Quy tắc | Test canh |
|---|---|---|
| 1 | Không đặc trưng nào bám theo mức giá (tương quan với giá < 0,5) | `test_no_feature_tracks_the_raw_price_level` |
| 2 | Giá trị tại bar *t* chỉ dùng dữ liệu tới *t* | `test_features_identical_when_future_removed` |
| 3 | Tham số ước lượng từ dữ liệu chỉ khớp trên train | `test_scaler_ignores_valid_and_test` |
| 4 | Train → valid → test theo thời gian, có vùng đệm giữa | `test_split_is_ordered_and_embargoed` |
| 5 | Cửa sổ của train không chạm bar valid/test | `test_windows_stay_inside_their_split` |
| 6 | Tín hiệu **và đặc trưng** bot không bao giờ là đầu vào của LSTM — chỉ dành cho Meta (spec 007) | `test_signals_stay_out_of_the_feature_matrix`, `test_bot_columns_never_in_feature_matrix` |
| 7 | Không tạo mảng 3 chiều; ba tập dùng chung một ma trận | `test_datasets_share_one_two_dimensional_matrix` |
| 8 | Mọi cột đều có mô tả | `test_every_column_is_documented` |
| 9 | Tắt một nhóm thì không còn cột nào của nhóm đó | `test_disabled_group_leaves_no_columns` |
| 10 | Tín hiệu bot tái lập đúng AFL gốc, không nhìn tương lai | `test_signals_do_not_use_future_bars` |
| 11 | Bar đúng kích thước khai báo | `test_loaded_bars_have_the_configured_size` |
| 12 | Chu kỳ đúng tầm nhìn đã định (30 phút … 1 tuần) | `test_periods_match_their_intended_horizons` |
| 13 | Gộp bar 1 phút ra đúng bar 5 phút của nhà cung cấp | `test_resample_reproduces_vendor_five_minute_bars` |
| 14 | Trạng thái vị thế không nằm trong ma trận đặc trưng | `test_position_state_not_in_feature_matrix` |
| 15 | Nạp dữ liệu huấn luyện không bao giờ cần mạng | `test_loader_never_opens_a_network_connection` |
| 16 | Lực mua cùng chiều với giá trong bar (bắt việc đảo nhãn mua/bán) | `test_order_flow_imbalance_moves_with_price`, `test_db_buy_side_pays_more_than_sell_side` |
| 17 | Tổng reward của một lệnh = đúng lãi/lỗ của lệnh đó, tính bằng R | `test_reward_telescopes_to_realised_pnl` |
| 18 | Khi cắt đoạn huấn luyện, phần tương lai được ước lượng chứ không gán bằng 0 | `test_boundary_bootstraps_instead_of_zeroing_future`, `test_collect_bootstraps_from_the_pre_reset_state` |
| 19 | Cột không khai `regime` không trôi ≥ 1σ giữa các năm của train | `test_non_regime_features_do_not_drift_across_years` |

## 12. Lệnh

Trên máy này `python` trỏ vào Python 3.12 **không có thư viện**. Dùng `py -3.13`.

```bash
py -3.13 build_features.py --out data/features   # dựng lại đặc trưng, sinh FEATURES.md
py -3.13 build_features.py --dry-run             # chỉ xem báo cáo
py -3.13 -m pytest tests/ -q                     # toàn bộ test (~7 phút)
py -3.13 -m pytest tests/test_invariants.py -q   # chỉ bất biến
```

Chạy từ thư mục gốc; lỗi import thì đặt `PYTHONPATH=.`.

## 13. GPU

RTX 4060 (8,6 GB), `torch 2.13.0+cu130`. Huấn luyện và suy luận **ưu tiên GPU**:

- Chọn thiết bị ở **một chỗ duy nhất**: `laplace/rl/device.py`
- Không vòng lặp Python qua từng môi trường song song — một lời gọi cho cả lô
- Tránh chuyển dữ liệu GPU ↔ CPU trong vòng lặp nóng
- Đo tốc độ phải đồng bộ GPU trước và sau, báo bằng **bước/giây kèm số môi trường**

**Cài lại torch có thể làm hỏng nó** (đường dẫn Windows quá 260 ký tự, pip dừng giữa
chừng). Long paths đã được bật. Sau khi cài phải kiểm tra
`site-packages/torch/_C.cp313-win_amd64.pyd` còn tồn tại.

## 14. Quy ước code

- Comment và docstring: **tiếng Việt không dấu** (console Windows cp1252 sẽ lỗi).
  Tài liệu cho người đọc (README, specs, `catalog.py`, FEATURES.md) thì **có dấu**.
- Tên cột: `<nhóm>__<tên>`.
- **Không sửa tay** `FEATURES.md` và `data/features/catalog.json`.
- File lớn: dùng công cụ Write, không dùng heredoc trong Bash (bị cắt ở ~10 KB).

## 15. Xong là khi nào

- Toàn bộ test xanh, không chỉ test mới
- Bất biến mới (nếu có) đã vào bảng mục 11 kèm test
- `build_features.py` chạy được, tài liệu sinh tự động đã cập nhật
- Con số trong README khớp với thứ pipeline thực sự tạo ra
- Spec đã ghi kết quả thật, kể cả khi thất bại
- Đã commit và push lên `https://github.com/namngyh/MODUS-V2`
