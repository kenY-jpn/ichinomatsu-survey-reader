import os
import sys
import io
import shutil
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

# ↓↓↓ ★ ここに各質問項目のチェックボックスの座標（x1, y1, x2, y2）を入力してください ★ ↓↓↓
CHECKBOX_COORDS = {
    "宿泊全般": {
        "大変満足": [245, 72, 256, 82],
        "ほぼ満足": [322, 72, 333, 82],
        "やや不満": [398, 72, 411, 82],
        "不満":     [475, 72, 486, 82]
    },
    "フロント_チェックイン": {
        "大変満足": [245, 128, 256, 139],
        "ほぼ満足": [322, 128, 333, 139],
        "やや不満": [398, 128, 411, 139],
        "不満":     [475, 128, 486, 139]
    },
    "フロント_電話": {
        "大変満足": [245, 143, 256, 154],
        "ほぼ満足": [322, 143, 333, 154],
        "やや不満": [398, 143, 411, 154],
        "不満":     [475, 143, 486, 154]
    },
    "客室_係り": {
        "大変満足": [245, 191, 256, 202],
        "ほぼ満足": [322, 191, 333, 202],
        "やや不満": [398, 191, 411, 202],
        "不満":     [475, 191, 486, 202]
    },
    "客室_雰囲気": {
        "大変満足": [245, 207, 256, 218],
        "ほぼ満足": [322, 207, 333, 218],
        "やや不満": [398, 207, 411, 218],
        "不満":     [475, 207, 486, 218]
    },
    "客室_清掃": {
        "大変満足": [245, 225, 256, 236],
        "ほぼ満足": [322, 225, 333, 236],
        "やや不満": [398, 225, 411, 236],
        "不満":     [475, 225, 486, 236]
    },
    "客室_お部屋全般": {
        "大変満足": [245, 239, 256, 250],
        "ほぼ満足": [322, 239, 333, 250],
        "やや不満": [398, 239, 411, 250],
        "不満":     [475, 239, 486, 250]
    },
    "客室_寝具": {
        "大変満足": [245, 255, 256, 266],
        "ほぼ満足": [322, 255, 333, 266],
        "やや不満": [398, 255, 411, 266],
        "不満":     [475, 255, 486, 266]
    },
    "客室_浴衣": {
        "大変満足": [245, 272, 256, 283],
        "ほぼ満足": [322, 272, 333, 283],
        "やや不満": [398, 272, 411, 283],
        "不満":     [475, 272, 486, 283]
    },
    "夕食_味付け": {
        "大変満足": [245, 320, 256, 331],
        "ほぼ満足": [322, 320, 333, 331],
        "やや不満": [398, 320, 411, 331],
        "不満":     [475, 320, 486, 331]
    },
    "夕食_品数": {
        "大変満足": [245, 336, 256, 347],
        "ほぼ満足": [322, 336, 333, 347],
        "やや不満": [398, 336, 411, 347],
        "不満":     [475, 336, 486, 347]
    },
    "夕食_盛り付け": {
        "大変満足": [245, 353, 256, 364],
        "ほぼ満足": [322, 353, 333, 364],
        "やや不満": [398, 353, 411, 364],
        "不満":     [475, 353, 486, 364]
    },
    "夕食_係り": {
        "大変満足": [245, 369, 256, 380],
        "ほぼ満足": [322, 369, 333, 380],
        "やや不満": [398, 369, 411, 380],
        "不満":     [475, 369, 486, 380]
    },
    "朝食_味付け": {
        "大変満足": [244, 416, 255, 427],
        "ほぼ満足": [321, 416, 332, 427],
        "やや不満": [397, 416, 410, 427],
        "不満":     [474, 416, 485, 427]
    },
    "朝食_品数": {
        "大変満足": [245, 432, 256, 443],
        "ほぼ満足": [322, 432, 333, 443],
        "やや不満": [398, 432, 411, 443],
        "不満":     [475, 432, 486, 443]
    },
    "朝食_係り": {
        "大変満足": [245, 448, 256, 459],
        "ほぼ満足": [322, 448, 333, 459],
        "やや不満": [398, 448, 411, 459],
        "不満":     [475, 448, 486, 459]
    },
    "大浴場_大浴場": {
        "大変満足": [245, 496, 256, 507],
        "ほぼ満足": [322, 496, 333, 507],
        "やや不満": [398, 496, 411, 507],
        "不満":     [475, 496, 486, 507]
    },
    "大浴場_洗い場": {
        "大変満足": [245, 514, 256, 525],
        "ほぼ満足": [322, 514, 333, 525],
        "やや不満": [398, 514, 411, 525],
        "不満":     [475, 514, 486, 525]
    },
    "大浴場_脱衣場": {
        "大変満足": [245, 529, 256, 540],
        "ほぼ満足": [322, 529, 333, 540],
        "やや不満": [398, 529, 411, 540],
        "不満":     [475, 529, 486, 540]
    },
    "認知経路": {
        "旅行会社":       [57, 582, 69, 597],
        "インターネット": [132, 582, 146, 597],
        "雑誌":           [220, 582, 234, 597],
        "友人・知人":     [273, 582, 287, 597],
        "その他":         [373, 582, 385, 597]
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

def setup_directories(base_dir: Path):
    """フォルダパスを返します。存在しない場合は作成します。"""
    dirs = {
        "input": base_dir / "input_data",
        "processed": base_dir / "processed_data",
        "error": base_dir / "error_data",
        "output": base_dir / "output_data"
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    return dirs

def evaluate_checkboxes(img_rgb_np, coords_dict, scale=2.0):
    """
    OpenCVを使って画像からチェックボックスのピクセル密度を計算し、チェック状態を判定する。
    """
    # グレースケールに変換
    gray = cv2.cvtColor(img_rgb_np, cv2.COLOR_RGB2GRAY)
    
    # 二値化（文字や黒いインクのチェックが「白」になるように THRESH_BINARY_INV を使用）
    # 大津の二値化も組み合わせて自動でしきい値を決定
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    results = {}
    for question, options in coords_dict.items():
        best_option = "無回答"
        max_ratio = 0.0
        
        for opt_name, box in options.items():
            # coords_dictの座標[x1,y1,x2,y2]は等倍(1x)想定なので、拡大率(scale)をかける
            x1, y1, x2, y2 = [int(v * scale) for v in box]
            
            h = y2 - y1
            w = x2 - x1
            if h <= 0 or w <= 0:
                continue
                
            # ★重要枠線そのものを誤検知しないよう、上下左右15%程度を削って内側だけを抽出する
            margin_y = int(h * 0.15)
            margin_x = int(w * 0.15)
            
            crop_y1 = y1 + margin_y
            crop_y2 = y2 - margin_y
            crop_x1 = x1 + margin_x
            crop_x2 = x2 - margin_x
            
            if crop_y1 >= crop_y2 or crop_x1 >= crop_x2:
                continue
                
            roi = thresh[crop_y1:crop_y2, crop_x1:crop_x2]
            
            # 白ピクセル（元は黒インク）の割合を計算
            white_pixels = cv2.countNonZero(roi)
            total_pixels = roi.shape[0] * roi.shape[1]
            ratio = white_pixels / total_pixels if total_pixels > 0 else 0
            
            if ratio > max_ratio:
                max_ratio = ratio
                best_option = opt_name
                
        # どの選択肢も「1%」未満しか塗られていなければ「無回答」とする（閾値を下げて感度を上げました）
        if max_ratio < 0.01:
            best_option = "無回答"
            
        results[question] = best_option
        
    return results

def process_single_pdf(pdf_path: Path, dirs: dict):
    """
    1つのPDFに対する処理（マスキング廃止 -> OpenCV/EasyOCRでの抽出）を行います。
    抽出した辞書データ(dict)を返します。
    """
    # ====== 1. PDF読み込みと画像化 ======
    doc = fitz.open(pdf_path)
    try:
        page1 = doc[0]  # 1ページ目
        
        zoom_factor = 2.0
        zoom = fitz.Matrix(zoom_factor, zoom_factor)
        
        # 1ページ目の画像化 (マスキングを廃止し、メモリ上のデータとして直接利用)
        pix1 = page1.get_pixmap(matrix=zoom)
        img1 = Image.open(io.BytesIO(pix1.tobytes("png")))
        
        # ====== 2. EasyOCRによる「日付」「お部屋」のローカル抽出 ======
        date_crop_box = (DATE_BOX[0] * zoom_factor, DATE_BOX[1] * zoom_factor, DATE_BOX[2] * zoom_factor, DATE_BOX[3] * zoom_factor)
        room_crop_box = (ROOM_BOX[0] * zoom_factor, ROOM_BOX[1] * zoom_factor, ROOM_BOX[2] * zoom_factor, ROOM_BOX[3] * zoom_factor)
        
        date_img = img1.crop(date_crop_box)
        room_img = img1.crop(room_crop_box)
        
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
        full_img_np = np.array(img1.convert('RGB'))
        checkbox_results = evaluate_checkboxes(full_img_np, CHECKBOX_COORDS, scale=zoom_factor)
    finally:
        # 正常終了時もエラー発生時も、必ずPDFファイルは閉じる
        doc.close()
    
    # ====== 4. データの統合 ======
    # OpenCVで取得したチェックボックスの結果をベースにする
    data = checkbox_results.copy()
    
    # ローカルOCRで取得した値を最終的なデータに統合
    data["日付"] = raw_date
    data["お部屋"] = final_room
    data["元のファイル名"] = pdf_path.name
    data["自由記述"] = ""  # 人間が手入力するための空枠
    
    return data

def main():
    base_dir = Path(__file__).parent
    dirs = setup_directories(base_dir)
    print(f"📁 入力フォルダ: {dirs['input']} 内のPDFを探しています...")

    all_results = []
    pdf_files = list(dirs["input"].glob("*.pdf"))
    
    if len(pdf_files) == 0:
        print("処理対象のPDFファイルが見つかりませんでした。")
        return

    for pdf_path in pdf_files:
        print(f"\n🔄 処理中: {pdf_path.name} ...")
        try:
            # AI/OpenCVによる抽出処理を実行
            extracted_data = process_single_pdf(pdf_path, dirs)
            all_results.append(extracted_data)
            
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
        
        # '元のファイル名' 列を一番左に持ってくるための並び替え処理
        cols = ['元のファイル名'] + [col for col in df.columns if col != '元のファイル名']
        df = df[cols]
        
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
