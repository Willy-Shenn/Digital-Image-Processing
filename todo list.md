# TODO（依專案技術文件整理）

## 環境與版本控制
- [x] 建立並啟用專案虛擬環境 `venv`，所有安裝與執行均在其中完成
- [x] 依需求安裝套件並維護 `requirements.txt`（新增/更新/移除後立即 `pip freeze > requirements.txt`）
- [ ] 每次程式修改皆以中文撰寫 git commit（含標題與詳細內容）

## 資料夾與檔名規範
- [x] 確保 `./input`、`./result` 目錄存在並符合 I/O 規範
- [x] 實作時間戳記命名（`yymmddhhmmss`）並套用於所有輸出檔：處理結果、差異圖、圖表、可選的原圖備份
- [x] 依建議前綴保存各演算法輸出（例：`{ts}_interp_bicubic.png`、`{ts}_histeq_clahe.png`、`{ts}_wavelet_denoise.png`、`{ts}_diff_*.png`、`{ts}_hist_*.png` 等）

## Flask 後端流程
- [x] 路由設計：`GET /` 上傳頁、`POST /process` 執行處理、`GET /result/<ts>` 顯示多窗格結果、`GET /files/<path>` 提供檔案存取
- [x] 處理流程：接收上傳 → 存入 `./input` → 產生時間戳 → 針對勾選技術執行處理與輸出 → 回傳檔案路徑與指標

## 影像處理技術實作
- [x] Interpolation：支援 bilinear/bicubic 放大（可設定倍率）；執行自我一致性評估（先縮小再放大）；輸出處理圖、差異圖、評估指標（MSE/PSNR/SSIM）
- [x] Histogram Equalization / CLAHE：於亮度通道進行；支援 `clipLimit`、`tileGridSize`；產生前後直方圖與映射/增強曲線；計算 Entropy、RMS 對比與 CII；輸出差異圖
- [x] Wavelet Denoising：DWT 分解與 soft-threshold（MAD 估噪 + 通用閾值）；可選母小波與層數；輸出高頻係數分布/threshold 曲線或子帶示意；計算 PSNR/SSIM（合成噪測試）與 EPI；輸出差異圖

## 前端互動與顯示
- [x] 上傳頁支援多技術勾選（至少三項可同時選）
- [x] 結果頁依技術數量橫向分割 panes（flex 等寬）
- [x] 每個 pane 提供三種比較模式：滑桿式左右分割、疊圖透明度垂直滑桿、相減式差異圖
- [x] 每個 pane 顯示對應的品質指標與圖表（直方圖、增強曲線、小波係數/threshold 等）

## 輸出與附加建議
- [x] 產出並保存必要圖表至 `./result`（同時間戳前綴）
- [x] 可選：限制上傳檔案大小、限定 jpg/png、統一轉存為 PNG、輸出 `{ts}_meta.json` 記錄參數

## 驗收自檢（對應 README 檢查項）
- [x] 使用 venv 並於其中安裝/執行
- [x] `requirements.txt` 已更新
- [ ] 有中文 commit（標題+內容）
- [x] I/O 目錄與時間戳命名符合規範
- [x] 三種技術可同時處理並生成多窗格比較
- [x] 每個窗格具備滑桿式/疊圖式/相減式比較
- [x] 指標齊全（Interpolation：PSNR/SSIM 自我一致；HE：Entropy/CII；Wavelet：PSNR/SSIM+EPI）
- [x] 必要圖表齊全（直方圖、增強曲線、小波係數/threshold 等）
