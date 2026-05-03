import os
import sys
import io
import fitz  # PyMuPDF
from PIL import Image
import difflib
import numpy as np
import easyocr
import cv2  # pip install opencv-python

# Windows環境での文字化け（cp932エラー）対策
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# ====== 設定 ======
# お部屋名の候補リスト（29室）
ROOM_NAMES = ["松風", "高砂", "鶴", "亀", "松", "竹", "梅", "丹頂", "吉祥", "万葉", "福寿", "桂", "末広", "平安", "蓬莱", "白樺", "橘", "桐", "藤", "寿", "九重", "芙蓉", "萩", "蘭", "牡丹", "百合", "葵", "梓", "楓"]

# クロップ（切り抜き）用の座標定義: (左上X, 左上Y, 右下X, 右下Y)
DATE_BOX = (50, 700, 250, 750) 
ROOM_BOX = (50, 750, 250, 800)

# ↓↓↓ ★ ここに各質問項目のチェックボックスの座標（x1, y1, x2, y2）を入力してください ★ ↓↓↓
CHECKBOX_COORDS = {
    "宿泊全般": {
        "大変満足": [100, 200, 120, 220],
        "ほぼ満足": [130, 200, 150, 220],
        "やや不満": [160, 200, 180, 220],
        "不満":     [190, 200, 210, 220]
    },
    "フロント_チェックイン": {
        "大変満足": [100, 250, 120, 270],
        "ほぼ満足": [130, 250, 150, 270],
        "やや不満": [160, 250, 180, 270],
        "不満":     [190, 250, 210, 270]
    }
}
# ↑↑↑ ========================================================================= ↑↑↑
# ==================

import ssl
ssl._create_default_https_context = ssl._create_unverified_context

# EasyOCRの初期化
ocr = easyocr.Reader(['ja'], gpu=False)

def evaluate_checkboxes(img_rgb_np, coords_dict, scale=2.0):
    """
    OpenCVを使って画像からチェックボックスの中身（ピクセル密度）を判定する関数
    """
    gray = cv2.cvtColor(img_rgb_np, cv2.COLOR_RGB2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    results = {}
    for question, options in coords_dict.items():
        best_option = "無回答"
        max_ratio = 0.0
        
        for opt_name, box in options.items():
            x1, y1, x2, y2 = [int(v * scale) for v in box]
            
            h = y2 - y1
            w = x2 - x1
            if h <= 0 or w <= 0: continue
            
            # 枠線を誤検知しないよう、上下左右を15%削る
            margin_y = int(h * 0.15)
            margin_x = int(w * 0.15)
            
            crop_y1 = y1 + margin_y
            crop_y2 = y2 - margin_y
            crop_x1 = x1 + margin_x
            crop_x2 = x2 - margin_x
            
            if crop_y1 >= crop_y2 or crop_x1 >= crop_x2: continue
            
            roi = thresh[crop_y1:crop_y2, crop_x1:crop_x2]
            
            white_pixels = cv2.countNonZero(roi)
            total_pixels = roi.shape[0] * roi.shape[1]
            ratio = white_pixels / total_pixels if total_pixels > 0 else 0
            
            if ratio > max_ratio:
                max_ratio = ratio
                best_option = opt_name
                
        # 3%未満なら無回答
        if max_ratio < 0.03:
            best_option = "無回答"
            
        results[question] = best_option
    return results

def extract_survey_data(pdf_path):
    print(f"'{pdf_path}' を読み込み、画像データに変換しています...")
    try:
        doc = fitz.open(pdf_path)
        page = doc[0]  
        
        zoom_factor = 2.0
        zoom = fitz.Matrix(zoom_factor, zoom_factor)
        pix = page.get_pixmap(matrix=zoom)
        
        # 1ページ目の画像化
        img_data = pix.tobytes("png")
        image = Image.open(io.BytesIO(img_data))
        
        # ====== EasyOCRによる抽出 ======
        date_crop_box = (DATE_BOX[0] * zoom_factor, DATE_BOX[1] * zoom_factor, DATE_BOX[2] * zoom_factor, DATE_BOX[3] * zoom_factor)
        room_crop_box = (ROOM_BOX[0] * zoom_factor, ROOM_BOX[1] * zoom_factor, ROOM_BOX[2] * zoom_factor, ROOM_BOX[3] * zoom_factor)
        
        date_img = image.crop(date_crop_box)
        room_img = image.crop(room_crop_box)
        
        date_np = np.array(date_img.convert('RGB'))
        room_np = np.array(room_img.convert('RGB'))
        
        date_ocr_result = ocr.readtext(date_np, detail=0)
        room_ocr_result = ocr.readtext(room_np, detail=0)
        
        def extract_text(ocr_res):
            if not ocr_res: return ""
            return "".join(ocr_res)
        
        raw_date = extract_text(date_ocr_result)
        raw_room = extract_text(room_ocr_result)
        
        matches = difflib.get_close_matches(raw_room, ROOM_NAMES, n=1, cutoff=0.4)
        final_room = matches[0] if matches else raw_room
        
        # ====== OpenCVによるチェックボックス判定 ======
        full_img_np = np.array(image.convert('RGB'))
        checkbox_results = evaluate_checkboxes(full_img_np, CHECKBOX_COORDS, scale=zoom_factor)
        
        doc.close()
        
        # ====== 結果の結合と出力 ======
        data = checkbox_results.copy()
        data["日付"] = raw_date
        data["お部屋"] = final_room
        data["自由記述"] = ""
        
        print("\n=== 解析結果（OpenCV + EasyOCR 完全ローカル） ===")
        import json
        print(json.dumps(data, ensure_ascii=False, indent=2))
        print("==============================")
        
    except Exception as e:
        print(f"読み込みエラーが発生しました: {e}")

if __name__ == "__main__":
    target_pdf = "masked_SKM_C301i26041520130.pdf" 
    extract_survey_data(target_pdf)
