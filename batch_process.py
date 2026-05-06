import os
import sys
import io
import shutil
import re
from pathlib import Path

# Windows環境での文字化け（cp932エラー）対策
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import fitz  # PyMuPDF
from PIL import Image
import pandas as pd
import difflib
import numpy as np
import easyocr
import cv2  # pip install opencv-python

# ====== 設定 ======
# お部屋名の候補リスト（29室）
ROOM_NAMES = ["松風", "高砂", "鶴", "亀", "松", "竹", "梅", "丹頂", "吉祥", "万葉", "福寿", "桂", "末広", "平安", "蓬莱", "白樺", "橘", "桐", "藤", "寿", "九重", "芙蓉", "萩", "蘭", "牡丹", "百合", "葵", "梓", "楓"]

# クロップ（切り抜き）用の座標定義: (左上X, 左上Y, 右下X, 右下Y)
# ※この数値は1倍（等倍）時のポイントサイズです。
DATE_BOX = (111, 664, 252, 686) 
ROOM_BOX = (176, 703, 274, 746)

# 固定する出力列リスト（AIの出力フォーマットを強制）
FIXED_COLUMNS = [
    "元のファイル名", "対象日", "部屋名", "宿泊者名", "宿泊全般", "フロント_チェックイン", 
    "フロント_電話の対応", "客室_係りの対応", "客室_お部屋の雰囲気", "客室_清掃", 
    "客室_お部屋全般", "客室_寝具", "客室_浴衣", "ご夕食_味付け", "ご夕食_品数", 
    "ご夕食_盛り付け", "ご夕食_係りの対応", "ご朝食_味付け", "ご朝食_品数", 
    "ご朝食_係りの対応", "大浴場_大浴場", "大浴場_洗い場", "大浴場_脱衣場", 
    "自由記述", "当旅館を知ったきっかけ"
]

# ↓↓↓ ★ ここに各質問項目のチェックボックスの座標（x1, y1, x2, y2）を入力してください ★ ↓↓↓
CHECKBOX_COORDS = {
    "宿泊全般": {
        "大変満足": [244, 71, 261, 87],
        "ほぼ満足": [321, 71, 338, 87],
        "やや不満": [397, 71, 416, 87],
        "不満":     [474, 71, 491, 87]
    },
    "フロント_チェックイン": {
        "大変満足": [244, 127, 261, 144],
        "ほぼ満足": [321, 127, 338, 144],
        "やや不満": [397, 127, 416, 144],
        "不満":     [474, 127, 491, 144]
    },
    "フロント_電話": {
        "大変満足": [244, 142, 261, 159],
        "ほぼ満足": [321, 142, 338, 159],
        "やや不満": [397, 142, 416, 159],
        "不満":     [474, 142, 491, 159]
    },
    "客室_係り": {
        "大変満足": [244, 190, 261, 207],
        "ほぼ満足": [321, 190, 338, 207],
        "やや不満": [397, 190, 416, 207],
        "不満":     [474, 190, 491, 207]
    },
    "客室_雰囲気": {
        "大変満足": [244, 206, 261, 223],
        "ほぼ満足": [321, 206, 338, 223],
        "やや不満": [397, 206, 416, 223],
        "不満":     [474, 206, 491, 223]
    },
    "客室_清掃": {
        "大変満足": [244, 224, 261, 241],
        "ほぼ満足": [321, 224, 338, 241],
        "やや不満": [397, 224, 416, 241],
        "不満":     [474, 224, 491, 241]
    },
    "客室_お部屋全般": {
        "大変満足": [244, 238, 261, 255],
        "ほぼ満足": [321, 238, 338, 255],
        "やや不満": [397, 238, 416, 255],
        "不満":     [474, 238, 491, 255]
    },
    "客室_寝具": {
        "大変満足": [244, 254, 261, 271],
        "ほぼ満足": [321, 254, 338, 271],
        "やや不満": [397, 254, 416, 271],
        "不満":     [474, 254, 491, 271]
    },
    "客室_浴衣": {
        "大変満足": [244, 271, 261, 288],
        "ほぼ満足": [321, 271, 338, 288],
        "やや不満": [397, 271, 416, 288],
        "不満":     [474, 271, 491, 288]
    },
    "夕食_味付け": {
        "大変満足": [244, 319, 261, 336],
        "ほぼ満足": [321, 319, 338, 336],
        "やや不満": [397, 319, 416, 336],
        "不満":     [474, 319, 491, 336]
    },
    "夕食_品数": {
        "大変満足": [244, 335, 261, 352],
        "ほぼ満足": [321, 335, 338, 352],
        "やや不満": [397, 335, 416, 352],
        "不満":     [474, 335, 491, 352]
    },
    "夕食_盛り付け": {
        "大変満足": [244, 352, 261, 369],
        "ほぼ満足": [321, 352, 338, 369],
        "やや不満": [397, 352, 416, 369],
        "不満":     [474, 352, 491, 369]
    },
    "夕食_係り": {
        "大変満足": [244, 368, 261, 385],
        "ほぼ満足": [321, 368, 338, 385],
        "やや不満": [397, 368, 416, 385],
        "不満":     [474, 368, 491, 385]
    },
    "朝食_味付け": {
        "大変満足": [243, 415, 260, 432],
        "ほぼ満足": [320, 415, 337, 432],
        "やや不満": [396, 415, 415, 432],
        "不満":     [473, 415, 490, 432]
    },
    "朝食_品数": {
        "大変満足": [244, 431, 261, 448],
        "ほぼ満足": [321, 431, 338, 448],
        "やや不満": [397, 431, 416, 448],
        "不満":     [474, 431, 491, 448]
    },
    "朝食_係り": {
        "大変満足": [244, 447, 261, 464],
        "ほぼ満足": [321, 447, 338, 464],
        "やや不満": [397, 447, 416, 464],
        "不満":     [474, 447, 491, 464]
    },
    "大浴場_大浴場": {
        "大変満足": [244, 495, 261, 512],
        "ほぼ満足": [321, 495, 338, 512],
        "やや不満": [397, 495, 416, 512],
        "不満":     [474, 495, 491, 512]
    },
    "大浴場_洗い場": {
        "大変満足": [244, 513, 261, 530],
        "ほぼ満足": [321, 513, 338, 530],
        "やや不満": [397, 513, 416, 530],
        "不満":     [474, 513, 491, 530]
    },
    "大浴場_脱衣場": {
        "大変満足": [244, 528, 261, 545],
        "ほぼ満足": [321, 528, 338, 545],
        "やや不満": [397, 528, 416, 545],
        "不満":     [474, 528, 491, 545]
    },
    "認知経路": {
        "旅行会社":       [56, 581, 74, 602],
        "インターネット": [131, 581, 151, 602],
        "雑誌":           [219, 581, 239, 602],
        "友人・知人":     [272, 581, 292, 602],
        "その他":         [372, 581, 390, 602]
    }
}
# ↑↑↑ ========================================================================= ↑↑↑
# ==================

import ssl
ssl._create_default_https_context = ssl._create_unverified_context

# EasyOCRの初期化 (グローバルで1回だけ読み込む)
# 【必要なライブラリのインストール手順（コマンドプロンプトで実行）】
# py -m pip install easyocr numpy opencv-python
ocr = easyocr.Reader(['ja'], gpu=False)

def parse_target_date(raw_date_str: str, filename: str) -> str:
    """対象日をYYYY/MM/DD形式で推測して返す"""
    fallback_date = ""
    # 1. ファイル名からの日付推測 (例: SKM_C301i26041520130.pdf -> 260415)
    m_file = re.search(r'(\d{2})(\d{2})(\d{2})', filename)
    if m_file:
        yy, mm, dd = m_file.groups()
        yy_int = int(yy)
        if 1 <= yy_int <= 15:
            year = 2018 + yy_int  # 令和とみなす (1〜15)
        else:
            year = 2000 + yy_int  # 西暦の下2桁とみなす (24, 26など)
        fallback_date = f"{year}/{mm}/{dd}"

    # 2. OCRテキストからの抽出
    text = raw_date_str.replace(' ', '').replace('　', '')
    
    m_reiwa = re.search(r'(?:令和|R|令)(\d{1,2})[年\.・/]?(\d{1,2})[月\.・/]?(\d{1,2})', text, re.IGNORECASE)
    if m_reiwa:
        y, m, d = m_reiwa.groups()
        return f"{2018 + int(y)}/{int(m):02d}/{int(d):02d}"
        
    m_seireki = re.search(r'(20\d{2})[年\.・/]?(\d{1,2})[月\.・/]?(\d{1,2})', text)
    if m_seireki:
        y, m, d = m_seireki.groups()
        return f"{y}/{int(m):02d}/{int(d):02d}"
        
    m_nums = re.search(r'(\d{1,2})[年\.・/]?(\d{1,2})[月\.・/]?(\d{1,2})', text)
    if m_nums:
        y, m, d = m_nums.groups()
        y_int = int(y)
        if 1 <= y_int <= 15:
            year = 2018 + y_int
        elif 16 <= y_int <= 99:
            year = 2000 + y_int
        else:
            year = 2024
        return f"{year}/{int(m):02d}/{int(d):02d}"

    return fallback_date

def setup_directories(base_dir: Path):
    """フォルダパスを返します。存在しない場合は作成します。"""
    dirs = {
        "input": base_dir / "input_data",
        "processed": base_dir / "processed_data",
        "error": base_dir / "error_data",
        "output": base_dir / "output_data",
        "debug": base_dir / "debug_output",
        "template": base_dir / "template_data"
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    return dirs

def align_image(img_rgb_np, template_rgb_np):
    """
    ORB特徴量を用いて、img_rgb_np を template_rgb_np の形にホモグラフィ変換（位置合わせ）する
    """
    img_gray = cv2.cvtColor(img_rgb_np, cv2.COLOR_RGB2GRAY)
    template_gray = cv2.cvtColor(template_rgb_np, cv2.COLOR_RGB2GRAY)
    
    # 高速なORB特徴量抽出器（5000点）
    orb = cv2.ORB_create(5000)
    
    kp1, des1 = orb.detectAndCompute(img_gray, None)
    kp2, des2 = orb.detectAndCompute(template_gray, None)
    
    if des1 is None or des2 is None:
        print("    ⚠️ 特徴点が十分に抽出できなかったため、位置合わせをスキップします。")
        return img_rgb_np
        
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = bf.match(des1, des2)
    matches = sorted(matches, key=lambda x: x.distance)
    
    # 上位15%の優秀なマッチングだけを使用（最低でも50個は確保）
    good_matches = matches[:max(50, int(len(matches) * 0.15))]
    
    if len(good_matches) < 10:
        print("    ⚠️ 類似する特徴点が少なすぎるため、位置合わせをスキップします。")
        return img_rgb_np
        
    src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
    
    H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
    
    if H is None:
        print("    ⚠️ ホモグラフィ行列の計算に失敗したため、位置合わせをスキップします。")
        return img_rgb_np
        
    h, w = template_gray.shape
    aligned_img = cv2.warpPerspective(img_rgb_np, H, (w, h))
    return aligned_img

def evaluate_checkboxes(img_rgb_np, coords_dict, scale=2.0, debug_dir=None, pdf_name=""):
    """
    OpenCVを使って画像からチェックボックスのピクセル密度を計算し、チェック状態を判定する。
    """
    # グレースケールに変換
    gray = cv2.cvtColor(img_rgb_np, cv2.COLOR_RGB2GRAY)
    
    # 二値化（文字や黒いインクのチェックが「白」になるように THRESH_BINARY_INV を使用）
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    results = {}
    for question, options in coords_dict.items():
        best_option = "無回答"
        max_ratio = 0.0
        
        print(f"\n--- 【{question}】の判定 ---")
        
        for opt_name, box in options.items():
            # coords_dictの座標[x1,y1,x2,y2]は等倍(1x)想定なので、拡大率(scale)をかける
            x1, y1, x2, y2 = [int(v * scale) for v in box]
            
            h_outer = y2 - y1
            w_outer = x2 - x1
            if h_outer <= 0 or w_outer <= 0:
                continue
                
            crop_y1 = max(0, y1)
            crop_y2 = min(thresh.shape[0], y2)
            crop_x1 = max(0, x1)
            crop_x2 = min(thresh.shape[1], x2)
            
            roi_thresh = thresh[crop_y1:crop_y2, crop_x1:crop_x2]
            roi_color = img_rgb_np[crop_y1:crop_y2, crop_x1:crop_x2].copy()
            
            # 【ユーザー要望】与えた座標が枠を含んでいるか確認するためのRAW画像保存
            if debug_dir:
                safe_q = question.replace('/', '_').replace('\\', '_')
                safe_opt = opt_name.replace('/', '_').replace('\\', '_')
                coords_str = f"{box[0]}_{box[1]}_{box[2]}_{box[3]}"
                raw_name = f"{pdf_name}_{safe_q}_{safe_opt}_0_raw_[{coords_str}].png"
                cv2.imwrite(str(debug_dir / raw_name), cv2.cvtColor(roi_color, cv2.COLOR_RGB2BGR))
                
            # 動的枠検出 (findContours)
            contours, _ = cv2.findContours(roi_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            inner_roi = None
            
            if contours:
                # 面積が最大の輪郭を探す
                largest_contour = max(contours, key=cv2.contourArea)
                x_c, y_c, w_c, h_c = cv2.boundingRect(largest_contour)
                
                # 検出した枠が小さすぎないかチェック（ノイズ対策、元の枠の30%以上）
                if w_c > w_outer * 0.3 and h_c > h_outer * 0.3:
                    # 枠線自体を除外するためのインナークロップ（内側に15%縮小）
                    margin_x = int(w_c * 0.15)
                    margin_y = int(h_c * 0.15)
                    
                    inner_x1 = x_c + margin_x
                    inner_y1 = y_c + margin_y
                    inner_x2 = x_c + w_c - margin_x
                    inner_y2 = y_c + h_c - margin_y
                    
                    if inner_x1 < inner_x2 and inner_y1 < inner_y2:
                        inner_roi = roi_thresh[inner_y1:inner_y2, inner_x1:inner_x2]
                        # 検出確認用に赤枠(枠線)と緑枠(インナークロップ)を描画
                        cv2.rectangle(roi_color, (x_c, y_c), (x_c + w_c, y_c + h_c), (255, 0, 0), 1)
                        cv2.rectangle(roi_color, (inner_x1, inner_y1), (inner_x2, inner_y2), (0, 255, 0), 1)

            # 万が一枠が検出できなかった場合のフォールバック（従来の中央クロップ）
            if inner_roi is None:
                margin_x = int(w_outer * 0.15)
                margin_y = int(h_outer * 0.15)
                inner_roi = roi_thresh[margin_y:h_outer-margin_y, margin_x:w_outer-margin_x]
            
            # 白ピクセル（元は黒インク）の割合を計算
            white_pixels = cv2.countNonZero(inner_roi)
            total_pixels = inner_roi.shape[0] * inner_roi.shape[1]
            ratio = white_pixels / total_pixels if total_pixels > 0 else 0
            
            print(f"  {opt_name}: スコア {ratio*100:.2f}%")
            
            if ratio > max_ratio:
                max_ratio = ratio
                best_option = opt_name
                
            # デバッグ画像の保存
            if debug_dir:
                safe_q = question.replace('/', '_').replace('\\', '_')
                safe_opt = opt_name.replace('/', '_').replace('\\', '_')
                base_name = f"{pdf_name}_{safe_q}_{safe_opt}"
                
                # RGB -> BGR for saving
                roi_bgr = cv2.cvtColor(roi_color, cv2.COLOR_RGB2BGR)
                cv2.imwrite(str(debug_dir / f"{base_name}_1_detected.png"), roi_bgr)
                cv2.imwrite(str(debug_dir / f"{base_name}_2_inner.png"), inner_roi)
                
        # ノイズ（紙の汚れなど）を除外しつつ薄いチェックを拾うため「18%」に設定
        if max_ratio < 0.18:
            best_option = "無回答"
            
        print(f"  => 判定結果: {best_option} (最大スコア: {max_ratio*100:.2f}%)")
        results[question] = best_option
        
    return results

def process_single_pdf(pdf_path: Path, dirs: dict, template_rgb_np=None):
    """
    1つのPDFに対する処理（マスキング廃止 -> OpenCV/EasyOCRでの抽出）を行います。
    複数ページが含まれる場合は、表・裏のセットとみなし、奇数ページ（表面）だけを処理して
    抽出した辞書データ(dict)のリストを返します。
    """
    results_list = []
    
    # ====== 1. PDF読み込み ======
    doc = fitz.open(pdf_path)
    try:
        # すべてのページが表面（1ページ = 1アンケート）の想定
        for i in range(len(doc)):
            page_num_human = i + 1
            print(f"  --- {page_num_human}枚目 の処理を開始 ---")
            
            page = doc[i]
            
            zoom_factor = 2.0
            zoom = fitz.Matrix(zoom_factor, zoom_factor)
            
            # 画像化
            pix = page.get_pixmap(matrix=zoom)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            img_np = np.array(img.convert('RGB'))
            
            # テンプレートがあれば位置合わせを実行
            if template_rgb_np is not None:
                print("    ✨ テンプレート画像との位置合わせ（補正）を実行中...")
                img_np = align_image(img_np, template_rgb_np)
                img = Image.fromarray(img_np)
            
            # ====== 2. EasyOCRによる「日付」「お部屋」のローカル抽出 ======
            date_crop_box = (DATE_BOX[0] * zoom_factor, DATE_BOX[1] * zoom_factor, DATE_BOX[2] * zoom_factor, DATE_BOX[3] * zoom_factor)
            room_crop_box = (ROOM_BOX[0] * zoom_factor, ROOM_BOX[1] * zoom_factor, ROOM_BOX[2] * zoom_factor, ROOM_BOX[3] * zoom_factor)
            
            date_img = img.crop(date_crop_box)
            room_img = img.crop(room_crop_box)
            
            date_np = np.array(date_img.convert('RGB'))
            room_np = np.array(room_img.convert('RGB'))
            
            date_ocr_result = ocr.readtext(date_np, detail=0)
            room_ocr_result = ocr.readtext(room_np, detail=0)
            
            def extract_text(ocr_res):
                if not ocr_res:
                    return ""
                return "".join(ocr_res)
            
            raw_date = extract_text(date_ocr_result)
            raw_room = extract_text(room_ocr_result)
            
            # difflibで部屋名の自動補正（ファジィマッチング）
            matches = difflib.get_close_matches(raw_room, ROOM_NAMES, n=1, cutoff=0.4)
            final_room = matches[0] if matches else raw_room
            
            # ====== 3. OpenCVによるチェックボックス領域の判定 ======
            full_img_np = np.array(img.convert('RGB'))
            checkbox_results = evaluate_checkboxes(
                full_img_np, 
                CHECKBOX_COORDS, 
                scale=zoom_factor, 
                debug_dir=None,  # デバッグ画像出力をオフにする場合はNoneにする
                pdf_name=f"{pdf_path.stem}_{page_num_human}"
            )
            
            # ====== 4. データの統合 ======
            data = {}
            
            # ユーザーがCHECKBOX_COORDSに設定したキー名を、テンプレートの固定列名にマッピングする
            key_mapping = {
                "フロント_電話": "フロント_電話の対応",
                "客室_係り": "客室_係りの対応",
                "客室_雰囲気": "客室_お部屋の雰囲気",
                "夕食_味付け": "ご夕食_味付け",
                "夕食_品数": "ご夕食_品数",
                "夕食_盛り付け": "ご夕食_盛り付け",
                "夕食_係り": "ご夕食_係りの対応",
                "朝食_味付け": "ご朝食_味付け",
                "朝食_品数": "ご朝食_品数",
                "朝食_係り": "ご朝食_係りの対応",
                "認知経路": "当旅館を知ったきっかけ"
            }
            
            for old_key, val in checkbox_results.items():
                new_key = key_mapping.get(old_key, old_key)
                
                # 【ユーザー要望】大変満足を4〜不満を1、無回答を空欄に変換する
                value_mapping = {
                    "大変満足": 4,
                    "ほぼ満足": 3,
                    "やや不満": 2,
                    "不満": 1,
                    "無回答": ""
                }
                # 認知経路など、マッピング辞書にない値（インターネットなど）はそのまま出力する
                data[new_key] = value_mapping.get(val, val)
            
            # ローカルOCRで取得した値を最終的なデータに統合
            data["対象日"] = parse_target_date(raw_date, pdf_path.name)
            data["部屋名"] = "" if not raw_room.strip() else final_room
            data["元のファイル名"] = f"{pdf_path.name}_{page_num_human}枚目"
            data["宿泊者名"] = "" # マスキングされているため空欄
            data["自由記述"] = ""  # 人間が手入力するための空枠
            
            results_list.append(data)
            
    finally:
        # 正常終了時もエラー発生時も、必ずPDFファイルは閉じる
        doc.close()
    
    return results_list

def main():
    base_dir = Path(__file__).parent
    dirs = setup_directories(base_dir)
    print(f"📁 入力フォルダ: {dirs['input']} 内のPDFを探しています...")
    
    # ====== テンプレートPDFの事前読み込み ======
    template_rgb_np = None
    template_files = list(dirs["template"].glob("*.pdf"))
    if len(template_files) > 0:
        template_path = template_files[0]
        print(f"📄 テンプレートPDFを読み込みます: {template_path.name}")
        try:
            doc_tmpl = fitz.open(template_path)
            page_tmpl = doc_tmpl[0]
            zoom_factor = 2.0
            zoom = fitz.Matrix(zoom_factor, zoom_factor)
            pix_tmpl = page_tmpl.get_pixmap(matrix=zoom)
            img_tmpl = Image.open(io.BytesIO(pix_tmpl.tobytes("png")))
            template_rgb_np = np.array(img_tmpl.convert('RGB'))
            doc_tmpl.close()
        except Exception as e:
            print(f"❌ テンプレートPDFの読み込みに失敗しました: {e}")
            print("  位置合わせ処理はスキップされます。")
    else:
        print("⚠️ template_data フォルダにテンプレートPDFがありません。")
        print("  位置合わせ処理なし（従来通りの処理）で進行します。")

    all_results = []
    pdf_files = list(dirs["input"].glob("*.pdf"))
    
    if len(pdf_files) == 0:
        print("処理対象のPDFファイルが見つかりませんでした。")
        return

    for pdf_path in pdf_files:
        print(f"\n🔄 処理中: {pdf_path.name} ...")
        try:
            # AI/OpenCVによる抽出処理を実行
            extracted_data_list = process_single_pdf(pdf_path, dirs, template_rgb_np)
            all_results.extend(extracted_data_list)
            
            # エラーが起きずに完走したので、元のPDFを処理済みフォルダへ移動
            destination = dirs["processed"] / pdf_path.name
            shutil.move(str(pdf_path), str(destination))
            print(f"✅ 完了: {pdf_path.name} -> processed_data フォルダへ移動しました")
            
        except Exception as e:
            import traceback
            print(f"❌ エラー ({pdf_path.name}): {e}")
            traceback.print_exc()
            error_destination = dirs["error"] / pdf_path.name
            try:
                if error_destination.exists():
                    error_destination.unlink()
                shutil.move(str(pdf_path), str(error_destination))
                print(f"   -> error_data フォルダへ移動し、次のファイルの処理へ進みます。")
            except PermissionError:
                print(f"⚠️ ファイル {pdf_path.name} が他のプログラム（または内部処理）でロックされているため移動できませんでした。")
                print("   PDFビューアー等でファイルを開いている場合は閉じてください。")

    if len(all_results) > 0:
        print("\n📊 すべてのファイルの処理が終わり、データの集計に入ります...")
        
        df = pd.DataFrame(all_results)
        
        # 指定された固定列フォーマットに強制変換する
        for col in FIXED_COLUMNS:
            if col not in df.columns:
                df[col] = ""  # 存在しない列は空欄にする
                
        # 完全一致させるために列を絞り込んで並び替える
        df = df[FIXED_COLUMNS]
        
        excel_path = dirs["output"] / "survey_results_local.xlsx"
        try:
            df.to_excel(excel_path, index=False)
            print(f"🎉 最終出力完了！すべての結果をExcelシートにまとめました！\n保存先: {excel_path}")
        except PermissionError:
            print(f"❌ エラー: Excelファイル ({excel_path}) が別のプログラムで開かれているため保存できませんでした。")
            print("ファイルを閉じてから再度実行するか、別のファイル名で保存するように変更してください。")
            # 別の名前で保存するフォールバック
            fallback_path = dirs["output"] / "survey_results_local_fallback.xlsx"
            df.to_excel(fallback_path, index=False)
            print(f"⚠️ 代わりに {fallback_path} に保存しました。")
        except Exception as e:
            print(f"❌ エラー: Excelファイルの保存中にエラーが発生しました。詳細: {e}")
    else:
        print("\n⚠️ 抽出に成功したデータが一つもありませんでした。")

if __name__ == "__main__":
    main()
