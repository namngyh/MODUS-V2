# CLAUDE.md

Hướng dẫn làm việc trên repo này. Đọc trước khi sửa bất cứ thứ gì.

## Dự án

Pipeline đặc trưng cho mô hình auto-trading VN30F1M. Đầu ra hiện tại là **X** (ma trận
đặc trưng đã chuẩn hoá, chia tập theo thời gian) cộng **tín hiệu tham chiếu** của hai bot
AFL. Chưa có nhãn, chưa có môi trường RL. Khung dự kiến: LSTM encoder + PPO hai head
(entry / exit); các component phụ trợ (GARCH, Bayesian) gắn vào state/reward, không phải
vào X.

Kiến trúc và ý nghĩa từng nhóm đặc trưng: [README.md](README.md). Danh mục từng cột:
[FEATURES.md](FEATURES.md) (sinh tự động).

## Lệnh

```bash
python build_features.py --out data/features   # dựng lại toàn bộ, ghi kèm FEATURES.md
python build_features.py --dry-run             # chỉ xem báo cáo, không ghi
python -m pytest tests/ -q                     # toàn bộ test
python -m pytest tests/test_invariants.py -q   # chỉ các bất biến (nhanh hơn)
```

Chạy test từ thư mục gốc; nếu import lỗi thì `PYTHONPATH=.`.

## Bất biến

Đây là các quy tắc **không được phá** mà không thảo luận trước. Mỗi quy tắc có một bài
test làm nó thất bại — một bất biến không có test canh thì chỉ là lời chúc, vì không ai
phát hiện được khi nó bị phá.

| # | Quy tắc | Test canh |
|---|---|---|
| 1 | Không đặc trưng nào mang mức giá thô (`\|corr\|` với close < 0,5) | `test_no_feature_tracks_the_raw_price_level` |
| 2 | Mọi phép biến đổi đặc trưng là nhân quả: giá trị tại *t* chỉ dùng dữ liệu ≤ *t* | `test_features_identical_when_future_removed` |
| 3 | Tham số ước lượng từ dữ liệu (trung vị, IQR, danh sách cột loại) chỉ khớp trên train | `test_scaler_ignores_valid_and_test` |
| 4 | Ba tập theo thứ tự thời gian, có embargo giữa chúng | `test_split_is_ordered_and_embargoed` |
| 5 | Cửa sổ của tập train không chạm bar của valid/test | `test_windows_stay_inside_their_split` |
| 6 | Tín hiệu bot không bao giờ nằm trong X | `test_signals_stay_out_of_the_feature_matrix` |
| 7 | Không vật chất hoá tensor 3 chiều; ba tập dùng chung một ma trận `(T, F)` | `test_datasets_share_one_two_dimensional_matrix` |
| 8 | Mọi cột trong X đều có mô tả trong catalog | `test_every_column_is_documented` |
| 9 | Tắt một nhóm trong config thì không còn cột nào của nhóm đó | `test_disabled_group_leaves_no_columns` |
| 10 | Tín hiệu bot tái lập đúng AFL gốc và cũng nhân quả | `test_signals_do_not_use_future_bars` |
| 11 | Bar sau khi nạp đúng kích thước khai trong `bar_minutes` | `test_loaded_bars_have_the_configured_size` |
| 12 | Chu kỳ (số bar) vẫn đúng tầm nhìn đã định (30 phút … 1 tuần) | `test_periods_match_their_intended_horizons` |
| 13 | Phép gộp bar tái lập đúng bar 5 phút của nhà cung cấp | `test_resample_reproduces_vendor_five_minute_bars` |
| 14 | Trạng thái vị thế không bao giờ nằm trong `features.npy` — nó phụ thuộc hành động của agent, không phải thị trường | `test_position_state_not_in_feature_matrix` |
| 15 | `loader.py` không bao giờ mở kết nối mạng — đường huấn luyện phải tái lập được và chạy được khi mất mạng | `test_loader_never_opens_a_network_connection` |
| 16 | Mất cân bằng mua-bán cùng dấu với return trong bar (và trên dữ liệu DB: giá TB bên mua > bên bán) — kiểm chứng kinh tế bắt việc đổi nhãn BUY/SELL | `test_order_flow_imbalance_moves_with_price`, `test_db_buy_side_pays_more_than_sell_side` |
| 17 | Tổng thưởng từng bar của một lệnh = đúng lãi lỗ thực hiện của lệnh đó (tính bằng bội số ATR) | `test_reward_telescopes_to_realised_pnl` |
| 18 | Mọi ranh giới episode/rollout đều bootstrap `V` của trạng thái **tiếp diễn thật**, không bao giờ gán tương lai = 0 và không bao giờ lấy trạng thái sau khi reset | `test_boundary_bootstraps_instead_of_zeroing_future`, `test_collect_bootstraps_from_the_pre_reset_state` |

Thêm bất biến mới thì thêm cả dòng trong bảng này lẫn bài test, trong cùng một thay đổi.

## Từ vựng: `profit` và `reward` là hai thứ khác nhau

Đây là quy ước **bắt buộc**, không phải sở thích cách gọi. Lẫn hai từ này là cách nhanh
nhất để báo cáo một con số không có nghĩa gì.

| Từ | Là gì | Đơn vị | Dùng để |
|---|---|---|---|
| **`profit`** | Lãi/lỗ thật của vị thế | **điểm chỉ số** (không phải VNĐ) | **Đánh giá** — đây là thước đo hiệu quả |
| **`reward`** | Tín hiệu huấn luyện của RL | **bội số ATR (R)** | **Tối ưu** — đây là thứ agent tối đa hoá |

**Reward không phải profit, và không tỷ lệ với profit.** Reward chia cho ATR lúc vào lệnh
để mọi chế độ biến động đóng góp ngang nhau khi học (spec 004); profit thì không chia gì
cả. Đo trên 1.539 lệnh của KESPT:

```
tỷ lệ R trên mỗi điểm:   0,26 (2017)  →  1,34 (2019)      chênh 5,2 lần
tương quan profit năm với reward năm:   chỉ 0,748

xếp hạng năm theo profit:  2025, 2020, 2021, 2018
xếp hạng năm theo reward:  2018, 2020, 2019, 2021
```

2025 là năm tốt nhất tính theo profit nhưng **không lọt top-4** tính theo reward. Hai
bảng xếp hạng khác nhau, nên câu *"reward tăng 20%"* không nói được gì về tiền.

### Quy tắc

- **Báo cáo hiệu quả luôn bằng `profit` (điểm).** Không bao giờ trình bày `reward` như
  một con số thành tích.
- **Huấn luyện tối ưu `reward`.** Đó là việc của nó.
- Tiêu chí đánh giá **phải khác** hàm reward — nếu chấm bài bằng chính thứ agent tối ưu
  thì không bao giờ phát hiện được nó đang khai thác kẽ hở của hàm reward.

### Đặt tên trong code

| Hậu tố | Đơn vị | Ví dụ |
|---|---|---|
| `_points` | điểm chỉ số | `profit_points`, `drawdown_points` |
| `_atr` hoặc `_R` | bội số ATR | `pos_pnl_atr`, `mfe_atr` |
| `reward` (trần) | tín hiệu huấn luyện | `reward`, `reward_mean` |

**Không dùng `pnl` trần** — nó không nói đơn vị nào và chính là chỗ tôi từng viết lẫn.

## Ngưỡng nhiễu khi đánh giá

Đo trên tập valid với **10 policy khởi tạo ngẫu nhiên, chưa huấn luyện** (spec 005):

```
trung bình +99,2 điểm | độ lệch chuẩn 164,3 | trải từ −136 đến +443
```

Một policy hoàn toàn ngẫu nhiên có thể kiếm **+442 điểm** trên valid chỉ nhờ may mắn.
Nên **không bao giờ kết luận từ một lần chạy duy nhất.**

| Số hạt giống | Phát hiện được chênh lệch |
|---:|---:|
| 1 | > 328 điểm |
| 3 | > 190 điểm |
| 5 | > 147 điểm |
| 10 | > 104 điểm |

Dùng bảng này theo cả hai chiều: nó cho biết cần bao nhiêu hạt giống để chứng minh một
cải thiện, **và** cho biết khi nào nên thôi đuổi theo một khác biệt quá nhỏ để đo được.

## Thảo luận thiết kế trước khi code

**Không viết code trước khi thống nhất thiết kế.** Đây là quy tắc cứng, đứng trước cả
SDD: thảo luận chọn *hướng*, spec chốt *chi tiết và cách chứng minh sai*, rồi mới code.

Lý do không phải là hình thức. Trong quant, phần lớn quyết định thiết kế **không thể
hoàn tác một cách âm thầm**: mỗi tham số thêm vào là một bậc tự do để quá khớp, mỗi lần
nhìn tập test là một lần tiêu ngân sách thống kê không hoàn lại, và mỗi giả định sai về
chi phí giao dịch chỉ lộ ra khi đã chạy tiền thật. Code sai thì sửa được; thiết kế sai
thì backtest vẫn đẹp.

### Ba quy tắc đã thống nhất

**Sau khi gửi đề xuất thiết kế, tôi dừng.** Không viết code, không sửa file, cho tới khi
bạn trả lời — kể cả khi tôi tin chắc phương án nào đúng.

**Việc lớn bàn từng cái một, việc nhỏ gộp lại.** Nhãn, reward, cách chia tập, kiến trúc
mạng: mỗi thứ một lần, chốt xong mới sang cái kế. Ngưỡng, chu kỳ, tên cột, bố cục module:
gộp thành một danh sách để bạn duyệt một lượt.

**Viết ngắn và cụ thể, tránh trừu tượng.** Số liệu thật và ví dụ thật, không phải thuật
ngữ. Tám trục ở dưới là danh sách kiểm cho tôi, **không phải dàn ý bắt buộc viết đủ**:
viết sâu ở chỗ thật sự quyết định, các trục còn lại gói một đoạn ngắn kèm lý do tại sao
không đáng lo.

### Sửa lỗi thì không cần hỏi

Quy tắc dừng ở trên áp dụng cho *quyết định thiết kế*, không áp dụng cho *lỗi*. Phân biệt
gọn nhất:

> **Nhiều cách sửa đều hợp lệ → đó là thiết kế, phải hỏi.**
> **Chỉ có một cách đúng → đó là lỗi, cứ sửa.**

Tự sửa rồi báo lại:

- Lỗi chắc chắn sai 100%: sai cú pháp, sai kiểu, lệch chỉ số, chia cho 0
- Công thức tính khác với công thức đã ghi trong tài liệu hoặc trong chính docstring của nó
- Lỗi vô tình phát hiện khi đang làm việc khác

Báo trước, không tự sửa:

- Lỗi logic mà tôi **không chắc 100%** — mô tả, đề xuất cách sửa, rồi chờ
- Thứ trông sai nhưng có thể là cố ý
- Lỗi mà cách sửa chạm tới ngữ nghĩa mô hình: đơn vị, ngưỡng, quy tắc chuẩn hoá

Sửa gì cũng nói rõ, không sửa lặng lẽ.

### Mỗi đề xuất phải có

1. **Vấn đề** — đang quyết định cái gì, một đoạn
2. **Ít nhất hai phương án thật** — mỗi phương án: cách làm, ưu điểm, **nhược điểm chi
   tiết** theo các trục dưới đây
3. **Khuyến nghị kèm một lý do quyết định** — điều gì làm cán cân nghiêng, không phải
   danh sách lý do chung chung
4. **Điều gì làm tôi đổi ý** — quan sát cụ thể sẽ lật khuyến nghị
5. **Rủi ro tôi không lượng hoá được** — nêu tên nó. Không có mục này nghĩa là chưa nghĩ đủ
6. **Cái mất khi bỏ phương án kia** — chi phí cơ hội, không chỉ chi phí thực hiện

### Trục nhược điểm bắt buộc xét

"Nhược điểm: phức tạp hơn" là câu vô nghĩa. Với dự án này, nhược điểm phải nói theo các
trục sau, và nói bằng con số khi có thể:

| Trục | Câu hỏi phải trả lời |
|---|---|
| **Bậc tự do** | Thêm bao nhiêu tham số tự do? Mỗi cái là một cơ hội quá khớp, và chúng nhân lên chứ không cộng |
| **Rò rỉ thông tin** | Có đường nào từ tương lai về hiện tại? Tham số ước lượng trên tập nào? |
| **Chi phí thực thi** | Sống sót qua phí + trượt giá ~0,3–0,5 điểm mỗi lượt không? Thanh khoản VN30F ở khung 5 phút đủ không? |
| **Ổn định theo chế độ** | Dựa vào chế độ thị trường nào? Còn đúng nếu chế độ đó biến mất? Đã kiểm qua 2018 / 2020 / 2022 / 2025 chưa? |
| **Ngân sách tập test** | Có tiêu một lần nhìn tập test không? Nếu có thì đổi lại được gì? |
| **Chẩn đoán khi hỏng** | Khi live lệch backtest, thiết kế này có cho biết *vì sao* không, hay chỉ biết là lệch? |
| **Tính đảo ngược** | Bỏ đi tốn gì? Có khoá định dạng dữ liệu, API, hay một lần chạy dài không? |
| **Chi phí tính toán** | Build lâu thêm bao nhiêu? Suy luận có kịp trước khi bar sau đóng không? |

Không phải lúc nào cũng viết đủ tám dòng. Thường chỉ hai ba trục thật sự phân biệt được
các phương án — viết kỹ chỗ đó, còn lại một câu gọn là đủ.

### Giải thích thì luôn hai tầng

Mọi giải thích viết ở hai tầng, theo thứ tự này:

**Tầng trực giác** — hình ảnh, không thuật ngữ. "Mô hình đang bị *mù* ở đoạn này",
"head exit *chết đói*", "encoder phải *học lại từ đầu* cho mỗi tình huống". Người đọc
phải hiểu được **tại sao nó quan trọng** mà không cần biết PPO là gì.

**Tầng cấu trúc** — cái đang thực sự xảy ra, dùng đúng thuật ngữ và kèm số: gradient nào
bằng 0, tensor hình dạng gì, tham số nào không được cập nhật, phân phối nào bị lệch,
bao nhiêu bậc tự do.

Tầng một để **quyết định** đúng, tầng hai để **triển khai** đúng. Thiếu tầng một thì bạn
đang duyệt một thứ mình không thực sự hiểu; thiếu tầng hai thì tôi có thể code sai mà
nghe vẫn hợp lý.

### Định nghĩa ký hiệu và khái niệm TRƯỚC khi dùng

Mỗi khi trình bày một thuật toán, công thức, hay khái niệm mới: **nói ký hiệu đó là gì và
khái niệm đó nghĩa là gì trước**, rồi mới dùng nó.

- Không viết `Â_t` rồi mới giải thích ở đoạn sau — định nghĩa ngay tại chỗ nó xuất hiện
  lần đầu, hoặc gom thành một bảng ký hiệu ngắn ở đầu phần
- Không dùng "advantage", "on-policy", "action masking", "behavior cloning" như thể người
  đọc đã biết. Một câu định nghĩa bằng tiếng Việt thường, kèm ví dụ cụ thể của dự án này
- Mỗi ký hiệu phải nói rõ **hình dạng và đơn vị**: `h_t` là vector 128 số, không đơn vị;
  `unrealized_pnl` là điểm chỉ số; `bars_held` là số bar 5 phút

Quy tắc kiểm tra: nếu một đoạn có ký hiệu mà người đọc phải cuộn lên hoặc tra Google mới
hiểu, đoạn đó viết sai thứ tự.

### Chi phí giao dịch: đã hoãn, đừng nhắc lại

Giai đoạn phát triển mô hình chạy với **chi phí giao dịch = 0**. Phí và thuế thêm vào sau
cùng. Đây là quyết định đã chốt — **không nêu lại trong mỗi đề xuất**.

Hệ quả đã ghi đầy đủ ở [specs/002](specs/002-cau-truc-policy.md) mục 3, không cần nhắc
lại: policy học ở chi phí 0 sẽ giao dịch dày, SKIP gần như không được dùng, và cơ chế
chống head exit chết đói chưa được kiểm chứng. Hàm reward vẫn khai tham số
`cost_per_turn` đặt `0.0`, để sau này thêm phí chỉ là đổi một con số.

Chỉ nêu lại đúng hai trường hợp: khi bắt đầu giai đoạn đánh giá thực chiến, hoặc khi một
quyết định thiết kế sẽ **khoá** việc thêm phí về sau.

### Chống nghi thức hoá

Hai danh sách ưu/nhược không làm đổi quyết định thì chỉ tốn thời gian. Nên:

- Phương án thứ hai phải là phương án **thật sự cân nhắc được**, không phải bù nhìn dựng
  lên để loại
- Nếu cả hai phương án đều tốt như nhau thì nói thẳng là hoà, đừng bịa ra lý do nghiêng
- Nếu tôi không tìm được nhược điểm nào cho phương án mình đề xuất, đó là dấu hiệu tôi
  chưa hiểu vấn đề, không phải dấu hiệu phương án tốt

### Khi nào bỏ qua bước này

Sửa lỗi chính tả, tài liệu, refactor không đổi hành vi, biểu đồ, và **thăm dò rẻ**: chạy
thử một ý tưởng trong scratchpad để xem số liệu ra sao. Nhưng ngay khi kết quả thăm dò
được dùng để ra quyết định, nó quay lại thành quyết định thiết kế và cần thảo luận —
không được lấy kết quả đã nhìn rồi mới dựng lý lẽ quanh nó.

## Quy trình: Spec-Driven Development

### Khi nào viết spec trước

Bắt buộc, vì đây là những chỗ mà lỗi **không làm chương trình dừng** mà chỉ làm kết quả
đẹp lên một cách sai:

- Nhóm đặc trưng mới, hoặc đổi ngữ nghĩa/đơn vị của đặc trưng đã có
- Nhãn, môi trường RL, hàm reward, quy tắc vào/ra lệnh
- Bất cứ thứ gì chạm ranh giới train / valid / test
- Đổi dữ liệu đầu vào: nguồn, mã, **kích thước bar**, khoảng thời gian
- Đổi một trong các bất biến ở trên

### Khi nào không viết spec

Refactor không đổi hành vi, đổi tên, tài liệu, biểu đồ, sửa lỗi hiển thị, và mọi thứ
thăm dò trong scratchpad. Viết spec cho "thêm RSI chu kỳ 22" thì tốn hơn là làm luôn.

### Một spec gồm sáu mục

Ngắn — một trang là đủ. Mẫu ở [specs/TEMPLATE.md](specs/TEMPLATE.md), đánh số
`specs/NNN-ten-ngan.md`.

1. **Câu hỏi** — một hai câu, cái gì và tại sao bây giờ
2. **Đầu vào → đầu ra**, kèm **đơn vị** của từng thứ
3. **Lập luận nhân quả** — tại sao giá trị tại *t* không chạm dữ liệu sau *t*
4. **Bất biến** mới hoặc bị ảnh hưởng
5. **Bài test làm spec này thất bại** — tên hàm cụ thể. Bắt buộc. Một spec không nêu
   được cách chứng minh mình sai thì không phải spec.
6. **Tiêu chí chấp nhận** — con số quyết định **trước** khi chạy, không phải sau

### Vòng đời

```
thảo luận thiết kế (chọn hướng, ≥2 phương án, ưu/nhược theo 8 trục)
   →  thống nhất  →  viết spec (chốt chi tiết + cách chứng minh sai)
   →  viết test thất bại trước  →  code cho tới khi test xanh
   →  chạy toàn bộ suite  →  cập nhật tài liệu sinh tự động
   →  ghi kết quả vào spec, kể cả khi giả thuyết bị bác
```

Bước đầu quyết định *làm hướng nào*; spec quyết định *làm chính xác ra sao và làm sao
biết mình sai*. Gộp hai bước lại thì spec sẽ chỉ hợp lý hoá phương án đầu tiên nghĩ ra.

Ghi kết quả **kể cả khi thất bại**, ngay trong file spec. Trong công việc định lượng,
một nghĩa địa giả thuyết đã bị bác là tài sản: nó ngăn việc chạy lại cùng một ý tưởng và
làm phồng vấn đề đa kiểm định.

### Mục 6 quan trọng nhất

Đây là điểm mà quant khác phần mềm thông thường. Code có thể đúng hoàn toàn mà chiến lược
vẫn thua, vì rủi ro thật là quá khớp và đổi chế độ thị trường, không phải lỗi lập trình.
Nên tiêu chí chấp nhận phải nêu trước: dùng tập nào, ngưỡng nào là thành công, và đã nhìn
vào tập test bao nhiêu lần. Mỗi lần nhìn tập test là một lần tiêu bớt giá trị của nó.

## Ưu tiên GPU

Máy này có **RTX 4060 (8,6 GB, 24 SM)** và `torch 2.13.0+cu130`. Từ giờ mọi thứ liên
quan tới huấn luyện và suy luận phải **tối ưu cho GPU trước**, CPU chỉ là đường lùi.

- **Chọn thiết bị ở một chỗ duy nhất** (`laplace/rl/device.py`), không rải
  `.cuda()` khắp nơi. Mặc định `cuda` nếu có, tự lùi về `cpu` nếu không.
- **Không vòng lặp Python trên chiều lô.** Mô phỏng môi trường phải vector hoá qua toàn
  bộ môi trường song song — một lời gọi cho 512 môi trường, không phải 512 lời gọi.
- **Giữ tensor trên GPU.** Tránh `.cpu()`, `.numpy()`, `.item()` trong vòng lặp nóng;
  mỗi lần chuyển là một lần đồng bộ chặn.
- **Đo bằng `torch.cuda.synchronize()`** trước và sau. Không đồng bộ thì chỉ đo được
  thời gian *xếp hàng lệnh*, không phải thời gian tính.
- **Báo cáo tốc độ bằng bước/giây**, kèm số môi trường song song. Con số tuyệt đối vô
  nghĩa nếu không nói cỡ lô.

Số nền để so sánh (mạng 77k tham số, episode 255 bar, đo 2026-09-06):

| | 32 môi trường | 512 môi trường |
|---|---:|---:|
| Cách A (đọc lại cửa sổ 64 bar) | 11.648 bước/s | 16.058 bước/s |
| GPU nhanh hơn CPU | ~7× | — |

Cảnh báo đã biết: các số trên **chỉ đo mạng neural**, chưa đo mô phỏng môi trường. Nếu
môi trường viết bằng vòng lặp Python thì nó sẽ thành nút thắt và toàn bộ lợi thế GPU
biến mất.

## Sửa ở đâu

| Muốn làm gì | Sửa file nào |
|---|---|
| Thêm/bớt indicator TA-Lib | `laplace/indicators.py` — thêm một dòng `Spec`, bắt buộc khai kiểu chuẩn hoá |
| Thêm kiểu chuẩn hoá mới | `laplace/norms.py` — thêm hàm và một dòng trong `NORMS` |
| Đặc trưng viết tay | `base.py` (OHLC), `orderflow.py` (dòng lệnh), `session.py` (lịch) |
| Bot AFL | `bots.py`; primitive AmiBroker ở `afl.py` |
| Chu kỳ, mốc chia tập, bật/tắt nhóm | `laplace/config.py` |
| Chia tập, tỉa cột, scaler | `laplace/scaling.py` |
| Cửa sổ trượt, lưu/đọc | `laplace/dataset.py` |
| Mô tả đặc trưng cho tài liệu | `laplace/catalog.py` |

Cấu trúc `Spec` trong `indicators.py` chính là SDD đang chạy sẵn: khai báo hàm, tham số
và **kiểu chuẩn hoá cho từng output**, nên không thể thêm indicator mà quên bước đổi đơn
vị. Giữ nguyên cơ chế này khi mở rộng.

## Quy ước

- **Không code trước khi thống nhất thiết kế** — xem mục đầu tài liệu này.
- **Comment và docstring trong code: tiếng Việt không dấu.** Console Windows ở đây là
  cp1252 và sẽ nổ khi in ký tự ngoài bảng mã. **Chuỗi dữ liệu tài liệu** (`catalog.py`,
  README, FEATURES.md, specs) thì **có dấu** — chúng là nội dung cho người đọc.
- Tên cột: `<nhóm>__<tên>`. Nhóm là khoá trong `blocks` của `pipeline.py`.
- **Không sửa tay** `FEATURES.md`, `data/features/catalog.json` — sinh từ `catalog.py`.
- Không commit `data/` và `ohlc_export.csv`.
- File lớn: dùng công cụ Write, không dùng heredoc trong Bash (bị cắt ngang ~10 KB và
  gây lỗi cú pháp khó hiểu).

## Bẫy đã gặp

Ghi lại vì mỗi cái đều mất thời gian để tìm ra, và không cái nào làm chương trình dừng.

1. **Kích thước bar từng là giả định ngầm.** Các chu kỳ `(6, 12, 24, 51, 102, 255)` được
   chọn cho bar 5 phút với nghĩa 30 phút / 1 giờ / 2 giờ / 1 phiên / 2 phiên / 1 tuần.
   Khi dữ liệu đổi sang bar 1 phút, mọi con số đó sai 5 lần mà **không test nào đỏ** —
   chúng vẫn là chu kỳ hợp lệ, chỉ không còn là chu kỳ mình định. Nay đã sửa tận gốc:
   `config.py` khai **tầm nhìn bằng phút** và suy ra số bar, nên không thể lệch nữa
   (spec 001, bất biến #11–#13). Nguồn dữ liệu mịn hơn được gộp về `bar_minutes` ngay
   tại loader.
2. **`bars_in_day` từng đếm cả bar tương lai của phiên đang chạy.** Ở bar 09:30 chưa thể
   biết hôm nay có bao nhiêu bar. Nay dùng độ dài phiên liền trước, và `is_last_bar` lấy
   từ lịch giao dịch chứ không từ việc đếm.
3. **SAREXT trả giá trị âm** khi ở chiều bán; `log` thẳng biến 48% số bar thành NaN.
   Tách thành mức (`log|x|/C`) và chiều (`sign`).
4. **OBV và AD là tổng luỹ kế** từ bar đầu tiên; mức của chúng chỉ phản ánh điểm bắt đầu
   tính. Phải lấy sai phân trước khi chuẩn hoá.
5. **Khối lượng có mùa vụ trong phiên.** Bar mở cửa và bar giữa trưa khác hẳn nhau; so
   trực tiếp là vô nghĩa. Dùng trung bình trượt của *chính bar-of-day đó*, đã shift 1.
6. **Cài lại `torch` trên máy này có thể làm hỏng chính nó.** Python bản Microsoft
   Store có tiền tố site-packages dài ~140 ký tự, cộng với cây giấy phép rất sâu bên
   trong wheel của torch (`dist-info/licenses/third_party/flash-attention/third_party/
   aiter/3rdparty/composable_kernel/...`) là vượt giới hạn 260 ký tự của Windows →
   `WinError 206`, pip dừng giữa chừng. **Nguy hiểm ở chỗ nó dừng ở chỗ khác nhau mỗi
   lần**: có lần chỉ hỏng metadata (torch vẫn chạy), có lần mất luôn `_C.pyd` (torch
   chết hẳn). Trạng thái máy hiện tại: `LongPathsEnabled = 0`. Trước khi cài lại torch
   phải bật long paths bằng PowerShell quyền Administrator rồi khởi động lại:
   `New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force`
   Kiểm tra sau khi cài: `pip list | grep torch` không được ra `None`, và
   `site-packages/torch/_C.cp313-win_amd64.pyd` phải tồn tại.
7. **Vòng lặp đệ quy phải giữ đúng thứ tự cập nhật.** SuperTrend sửa băng tại chỗ rồi bar
   sau đọc lại giá trị đã sửa; đảo hai dòng là ra một chỉ báo khác trông vẫn hợp lý.

## Xong là khi nào

- Toàn bộ `pytest tests/ -q` xanh, không chỉ test mới
- Bất biến mới (nếu có) đã vào bảng ở trên kèm test
- `build_features.py` chạy được và tài liệu sinh tự động đã cập nhật
- Con số trong README khớp với thứ pipeline thực sự tạo ra
- Spec đã ghi kết quả thật, kể cả khi giả thuyết bị bác
