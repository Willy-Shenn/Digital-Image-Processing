# 期末專案：Flask 影像處理與結果比較系統（Color Image Processing Web App）

> 角色定位：本 README 以「數位影像處理」課程期末專案之**開發流程與技術文件**為目標，完整覆蓋題目要求：  
> - 自行找到一套影像處理軟體處理喜歡的彩色影像（本專案即為自製影像處理軟體）  
> - 至少三種影像處理技術  
> - 需寫出方程式、參數、原理  
> - 需展示原圖、處理結果與圖表（histogram、enhancement curve 等）  
> - 以 Python 實作，包含 Flask 前端與後端，並提供三種比較方式（滑桿式 / 疊圖式 / 相減式）  
> - I/O 檔案規範：`./input`、`./result`、輸出以 `yymmddhhmmss` 命名  
> - 每個演算法需搭配合適的處理後影像評估指標（含數學定義）

---

## 0. 系統設定聲明（務必置於文件開頭）

1. **使用專案虛擬環境**（命名為 `venv`），**勿使用系統環境**。  
2. **套件安裝、程式執行皆需於虛擬環境中**。  
3. **只要套件有更新，`requirements.txt` 即需更新**。  
4. **程式每進行一次更動，皆需以中文撰寫 git commit，包含標題與詳細內容並提交**。

---

## 1. 專案目標與功能總覽

### 1.1 專案目標
建立一套可在瀏覽器操作的影像處理系統，讓使用者：
- 上傳一張彩色影像（color image）
- 同時選擇 ≥ 3 種影像處理技術（本專案提供三個）
- 逐一產生處理結果、差異圖（original - processed）、品質評估指標與圖表
- 以三種視覺互動方式比較「原圖 vs 處理後」

### 1.2 影像處理技術（本專案選用）
本專案以「**影像調整結果最佳**」為導向，選擇最常見且對觀感提升顯著的三類：
1. **Interpolation（插值縮放）**：以 Bilinear / Bicubic 將影像放大（提升解析度觀感、檢視細節）。  
2. **Histogram Equalization（直方圖均衡化）**：針對亮度通道做對比度增強（提升暗部/亮部細節）。  
3. **Wavelet Denoising（小波去雜訊/增強）**：DWT 分解後對高頻子帶做 soft-threshold 去雜訊，再重建。  

> 註：模板比對（template matching）偏向「搜尋/定位」任務，屬於影像分析而非影像調整；若你的課程要求也可用它替換插值，但本專案以「影像品質改善」為主軸。

---

## 2. 專案資料夾與檔案規範

### 2.1 必要資料夾
- `./input/`：保存**上傳的原始圖片**
- `./result/`：保存**輸出成果**（處理後影像、差異圖、圖表）

### 2.2 檔名規範（必做）
- 輸出以 **時間戳記 `yymmddhhmmss`** 命名，例如：`260107001530.png`
- 建議同一個處理流程同時間戳共享前綴：
  - `{ts}_orig.png`（可選，備份）
  - `{ts}_interp_bicubic.png`
  - `{ts}_histeq_clahe.png`
  - `{ts}_wavelet_denoise.png`
  - `{ts}_diff_interp.png`、`{ts}_diff_histeq.png`、`{ts}_diff_wavelet.png`
  - `{ts}_hist_before.png`、`{ts}_hist_after.png`
  - `{ts}_curve_histeq.png`
  - `{ts}_wavelet_coeff_hist.png`、`{ts}_wavelet_threshold_curve.png`

> 注意：題目要求「輸入圖片儲存於 `./input`」，「輸出圖片儲存於 `./result`」，且命名需以時間戳。

---

## 3. 環境建置（venv）與套件管理

### 3.1 建立與啟用虛擬環境
```bash
# 於專案根目錄
python -m venv venv

# Windows (CMD)
venv\Scripts\activate

# Windows (PowerShell)
venv\Scripts\Activate.ps1

# macOS/Linux
source venv/bin/activate
```

### 3.2 安裝套件
```bash
pip install -r requirements.txt
```

### 3.3 requirements.txt 更新規範（必做）
只要你新增/升級/移除套件，立刻更新：
```bash
pip freeze > requirements.txt
```

---

## 4. Git 提交規範（必做）

每次修改必須 commit，且 **commit 訊息用中文**，包含「標題 + 詳細內容」。

範例：
```text
新增：小波去雜訊處理流程與品質指標

- 加入 DWT 分解與 soft-threshold 去雜訊
- 新增 MAD 噪聲估計與閾值計算
- 後端輸出差異圖與子帶係數分布圖
- 前端 pane 增加指標顯示區塊
```

---

## 5. 系統架構與流程（前端 + 後端）

### 5.1 頁面設計（題目規格）
前端（Flask + Jinja2 / 或純 HTML）至少包含以下畫面：

#### 畫面 1：上傳圖片與選擇技術頁面
- 上傳彩色影像（jpg/png）
- 勾選要處理的技術（可複選 ≥ 3）
- 送出後進入結果頁

#### 畫面 2：結果比較頁（依選擇數量橫向分割）
- 若選 3 個技術 → 畫面切成 3 個**橫向窗格（columns）**
- 每個窗格對應一種技術，且每個窗格內提供三種比較模式：

1) **a. 滑桿式比較（x 軸左右橫移）**  
- 圖片在滑桿上方  
- 滑桿下方左右兩側標注：左側 **Original**（英文）、右側 **處理後**（中文）  
- 使用者拖動滑桿改變左右顯示比例（常見 before/after slider）

2) **b. 疊圖式比較（透明度 0%~100%）**  
- 原始圖片作為底層（base layer）  
- 處理後圖片作為上層（overlay layer）  
- 右側提供垂直滑桿（上/下拖動）控制 overlay 的 alpha：0%（全透明）到 100%（全不透明）

3) **c. 相減式比較（顯示差異圖）**  
- 顯示 `original - processed` 的結果（建議用絕對值顯示可視化差異）  
- **只需顯示差異圖結果**（題目要求）

### 5.2 後端處理流程（概念流程）
1. 接收上傳檔案 → 存到 `./input/`
2. 產生時間戳 `ts = yymmddhhmmss`
3. 針對每個選擇的技術：
   - 執行影像處理
   - 保存處理後影像到 `./result/`
   - 計算品質指標（依演算法不同）
   - 生成對應圖表（histogram、enhancement curve、小波係數分布等）
   - 生成差異圖（相減式比較）
4. 回傳結果頁所需的檔案路徑與指標數值（可用 JSON 或渲染模板）

---

## 6. 影像處理技術：原理、公式、參數（必寫）

> 本節是報告的核心：**每個演算法都要有：原理 + 方程式 + 參數**。  
> 另外，本專案以彩色影像為主，實務上常在 **亮度通道**做增強，以避免色偏（例如在 LAB 的 L 或 HSV 的 V 通道）。

---

### 6.1 技術一：Interpolation（插值縮放）

#### (1) 原理
插值縮放是將離散像素樣本重建為連續訊號，再在新座標取樣。對於放大（upscale），每個新像素位置 \((x',y')\) 對應到原圖連續座標 \((x,y)\)，其像素值由周圍像素的加權和決定。

#### (2) 公式
設原影像為 \(I(x,y)\)。放大倍率為 \(s\)。新座標 \((x',y')\) 對應原座標：
\[
x = \frac{x'}{s},\quad y = \frac{y'}{s}
\]

**Bilinear（雙線性）**：由四個鄰點加權：
\[
I'(x',y') = \sum_{i=0}^{1}\sum_{j=0}^{1} w_{ij}\, I(\lfloor x\rfloor+i,\ \lfloor y\rfloor+j)
\]
其中權重 \(w_{ij}\) 由 \(x\) 與 \(y\) 的小數部分決定。

**Bicubic（雙三次）**：使用 4×4 鄰域（16 點）與三次卷積核，通常能得到更平滑與較佳細節。

#### (3) 參數
- 放大倍率 \(s\)（例如 1.5、2、4）
- 插值方法：nearest / bilinear / bicubic（本專案建議 bilinear、bicubic）

#### (4) 適合的品質評估指標（本演算法）
插值放大通常缺乏「真實高解析度」作為 ground truth，因此本專案採用**自我一致性（self-consistency）評估**：
1) 將原圖 \(I\) 先降採樣成 \(I_{\downarrow}\)（例如縮小到 0.5 倍）  
2) 再用插值放大回同尺寸 \(I_{\uparrow}\)  
3) 用 \(I\) 當作 pseudo-ground-truth 計算 PSNR / SSIM

**MSE**
\[
MSE = \frac{1}{MN}\sum_{x=1}^{M}\sum_{y=1}^{N} (I(x,y) - I_{\uparrow}(x,y))^2
\]

**PSNR**
\[
PSNR = 10\log_{10}\left(\frac{MAX^2}{MSE}\right)
\]
其中 \(MAX=255\)（8-bit）。

**SSIM（結構相似性）**：以亮度、對比、結構綜合衡量，值域 \([0,1]\)，越大越相似。

> 這種評估方式可在無 ground truth 的前提下，合理比較 bilinear vs bicubic 的重建品質。

---

### 6.2 技術二：Histogram Equalization（直方圖均衡化 / CLAHE）

#### (1) 原理
透過灰階映射函數 \(T(r)\) 將像素強度重新分配，使輸出直方圖更均勻，提升整體對比度與可辨識細節。  
對彩色影像，通常在 LAB 的 \(L\)（亮度）通道做均衡化，再轉回 RGB，以避免色彩失真。

#### (2) 公式（CDF 映射）
令灰階值 \(r_k\) 的機率為 \(p(r_k)\)，其累積分布函數：
\[
CDF(r_k) = \sum_{j=0}^{k} p(r_j)
\]
均衡化映射：
\[
s_k = T(r_k) = (L-1)\cdot CDF(r_k)
\]
其中 \(L\) 為灰階級數（8-bit 時 \(L=256\)）。

#### (3) CLAHE（建議用於彩色照片）
為避免全域均衡化造成過度增強與雜訊放大，可使用 **CLAHE**：在區塊內做局部均衡，並限制對比度（clip limit）。

#### (4) 參數
- 全域 HE：無額外超參數
- CLAHE：
  - `clipLimit`（對比度限制）
  - `tileGridSize`（區塊大小）

#### (5) 必須展示的圖表（本演算法最重要）
- **Histogram（直方圖）**：before / after  
- **Enhancement curve（增強曲線）**：\(T(r)\) 或 CDF 曲線（用於說明灰階映射如何改變亮度分布）

#### (6) 適合的品質評估指標（本演算法）
直方圖均衡化的目標是提升對比與資訊量，因此建議搭配：

1) **影像熵（Entropy）**：資訊量指標（越大通常代表灰階分布更豐富）
\[
H = -\sum_{k=0}^{L-1} p(r_k)\log_2 p(r_k)
\]

2) **RMS Contrast（對比度）**：以標準差衡量整體對比
\[
C_{RMS} = \sqrt{\frac{1}{MN}\sum_{x,y}(I(x,y)-\mu)^2}
\]
可報告 **對比改善比**：
\[
CII = \frac{C_{RMS}^{after}}{C_{RMS}^{before}}
\]

> 實務上：Entropy↑、CII↑ 通常意味著對比與可辨識性提升。

---

### 6.3 技術三：Wavelet Denoising（DWT + Soft-threshold）

#### (1) 原理
離散小波轉換（DWT）把影像分解為多個子帶：
- \(LL\)：低頻（整體結構/亮度）
- \(LH, HL, HH\)：高頻細節（邊緣、紋理、雜訊）

去雜訊常在高頻子帶做 thresholding：壓小疑似雜訊的係數，再用 IDWT 重建，達到保留邊緣又降低雜訊的效果。

#### (2) DWT 分解概念
一次分解可表示：
\[
I \xrightarrow{DWT} \{LL, LH, HL, HH\}
\]
重建：
\[
\{LL, LH, HL, HH\} \xrightarrow{IDWT} I'
\]

#### (3) Soft-threshold（軟閾值）
對小波係數 \(w\)，軟閾值：
\[
\hat{w} = \mathrm{sign}(w)\cdot\max(|w|-T, 0)
\]

常用 universal threshold：
\[
T = \sigma\sqrt{2\ln N}
\]
其中 \(N\) 為係數數量，\(\sigma\) 為噪聲標準差。

噪聲估計（MAD，常用在 \(HH\) 子帶）：
\[
\sigma \approx \frac{\mathrm{median}(|HH|)}{0.6745}
\]

#### (4) 參數
- 母小波：如 `haar`, `db2`, `db4`（建議 `db2` 或 `db4`）
- 分解層數 `level`（建議 1~3）
- threshold 類型：soft / hard（本專案用 soft）

#### (5) 必須展示的圖表（建議）
- 高頻係數分布直方圖（threshold 前後）
- threshold 曲線示意（soft-threshold 的折線形狀）
- 或者展示四子帶拼圖（LL/LH/HL/HH）作為「原理圖」

#### (6) 適合的品質評估指標（本演算法）
去雜訊常同時追求「噪聲降低」與「邊緣保留」，因此建議同時報告：

1) **PSNR / SSIM（若有參考圖）**  
- 可採用「合成雜訊評估」：將原圖加上高斯雜訊得到 \(I_{noisy}\)，去雜訊得到 \(I_{denoise}\)，用原圖 \(I\) 當 ground truth 來算 PSNR / SSIM。

2) **Edge Preservation Index（邊緣保留指標）**  
以梯度能量比衡量邊緣保留程度（示例定義）：
\[
EPI = \frac{\sum |\nabla I_{denoise}|}{\sum |\nabla I_{noisy}|}
\]
\(EPI\) 越接近 1 表示邊緣能量保留較好（過低代表過度平滑）。

> 報告建議：同時呈現 PSNR/SSIM（品質）與 EPI（邊緣保留），能更符合去雜訊任務需求。

---

## 7. 差異圖（相減式比較）的定義（必做）

題目要求「以原始圖片減去處理後的圖片顯示」，建議採用：
\[
D(x,y) = |I_{orig}(x,y) - I_{proc}(x,y)|
\]
並將差異圖 normalize 到 \([0,255]\) 以利顯示。  
差異圖能直觀呈現影像處理改動的位置與幅度（例如均衡化對亮度分布改動、小波去噪對高頻雜訊的削弱等）。

---

## 8. Flask 路由設計（建議規格）

> README 不放程式碼範例，但需清楚說明路由與資料流。

- `GET /`：上傳與選擇技術頁
- `POST /process`：接收檔案 + 技術選擇 → 執行處理 → 存檔 → 回傳結果頁
- `GET /result/<ts>`：顯示該次處理的多窗格比較頁（依技術數量橫向分割）
- `GET /files/<path>`：提供 `./input`、`./result` 檔案讀取（或改用 `send_from_directory`）

---

## 9. 前端互動設計細節（題目三種比較方式必備）

### 9.1 滑桿式比較（x 軸左右）
- 兩張同尺寸圖疊在同一容器內
- 透過 `<input type="range">` 控制上層顯示寬度（clip / width）
- 圖在上方；滑桿在下；滑桿下方左右標「Original」「處理後」

### 9.2 疊圖式比較（右側垂直滑桿控制透明度）
- 原圖 base layer（opacity=1）
- 處理後 overlay layer（opacity 隨滑桿改變）
- 右側垂直 range（CSS 旋轉或使用 `writing-mode`）
- 顯示 0%~100%（透明度）

### 9.3 相減式比較
- 直接顯示差異圖 D(x,y)
- 僅顯示結果（不需再放原/處理後）

### 9.4 多窗格橫向分割（依選擇數量）
- 使用 CSS flex：`display:flex;`
- 每個 pane：`flex: 1 1 0;`，自動等寬
- 每個 pane 內再放三種比較 tab（或 radio buttons）

---

## 10. 圖表輸出規格（題目要求：histogram、enhancement curve 等）

每個演算法至少輸出：
- 原圖（顯示於前端，不一定要另存）
- 處理後影像（存檔）
- 差異圖（存檔）
- 1~2 張「解釋性圖表」（存檔 + 顯示）：
  - HE/CLAHE：histogram before/after、CDF/映射曲線 \(T(r)\)
  - Wavelet：係數直方圖、threshold curve、四子帶示意
  - Interpolation：放大倍率與方法說明、可選擇展示 kernel 曲線（bilinear/bicubic 的 1D 核）或局部放大對照 patch

> 產圖建議用 matplotlib 存成 PNG，與影像輸出一樣以 `{ts}_*.png` 命名存於 `./result/`。

---

## 11. 執行方式（開發 / 展示）

### 11.1 開發模式啟動（建議）
```bash
# 確認在 venv 中
flask --app app.py run --debug
```

### 11.2 進階建議（非必要，但加分）
- 限制上傳檔案大小（避免過大圖片拖垮伺服器）
- 僅允許 jpg/png
- 上傳後統一轉成 PNG 便於流程一致
- 記錄每次處理的參數（可輸出 `{ts}_meta.json`）方便寫報告

---

## 12. 報告撰寫建議（對應題目四項要求）

1) **Find an image processing software**  
- 說明：本專案即自製影像處理軟體（Web App），可處理你選擇的彩色影像。

2) **Choose at least three techniques**  
- 列出：Interpolation、Histogram Equalization/CLAHE、Wavelet Denoising（三種）。

3) **Write down equations, parameters, principles**  
- 直接引用本 README 第 6 節三個演算法的「原理/公式/參數」。

4) **Show original, results and diagrams**  
- 在結果頁每個 pane 顯示：原圖 vs 處理後（滑桿/疊圖）與差異圖；另外顯示 histogram、映射曲線、係數分布等圖表。

---

## 13. 驗收清單（提交前自我檢查）

- [ ] 已使用 `venv`，未使用系統環境  
- [ ] 套件安裝、執行都在 venv 中  
- [ ] `requirements.txt` 已更新  
- [ ] 每次改動皆有中文 commit（標題+內容）  
- [ ] 上傳檔案進 `./input/`  
- [ ] 輸出檔案進 `./result/` 且為 `yymmddhhmmss` 命名  
- [ ] 至少 3 種影像處理技術可同時選取並生成多窗格  
- [ ] 每個窗格都有：滑桿式 / 疊圖式 / 相減式  
- [ ] 每個演算法都有對應指標（Interpolation：PSNR/SSIM 自我一致性；HE：Entropy/CII；Wavelet：PSNR/SSIM（合成噪）+EPI）  
- [ ] 有輸出圖表（histogram、enhancement curve、小波係數等）

---

## 14. 授權與聲明（可依課程需求調整）
本專案僅作為課程期末專案展示用途。若使用他人圖片，請遵守原作者授權規範。
