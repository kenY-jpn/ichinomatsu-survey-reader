import fitz  # PyMuPDF

def mask_name_field(input_pdf, output_pdf, mask_rect_coords):
    """
    1ページ目の指定した座標を黒塗り（マスキング）して別名で保存する関数
    
    :param input_pdf: 入力元のPDFファイル名
    :param output_pdf: 保存先のPDFファイル名
    :param mask_rect_coords: 黒塗りする座標 (左上X, 左上Y, 右下X, 右下Y) のタプル
    """
    print(f"'{input_pdf}' を読み込み、座標 {mask_rect_coords} に黒塗り処理を行います...")
    # PDFファイルを開く
    doc = fitz.open(input_pdf)
    
    # 1ページ目 (インデックス0) を取得
    # （2ページ目以降は何もしないので、元のデータのまま保持されます）
    page = doc[0]
    
    # 引数で渡された座標から、PyMuPDFのRect（矩形・四角形）オブジェクトを作成
    rect = fitz.Rect(*mask_rect_coords)
    
    # 指定した四角形の領域を黒色で描き、中身を黒色で塗りつぶす (colorは枠線、fillは内側)
    # 値は「(赤, 緑, 青)」の順で、0.0(黒) ～ 1.0(白) の間で指定します。
    page.draw_rect(rect, color=(0, 0, 0), fill=(0, 0, 0))
    
    # 変更を別名ファイルとして保存
    doc.save(output_pdf)
    
    # メモリを解放
    doc.close()
    
    print(f"✅ マスク処理が完了しました！\n'{output_pdf}' として保存されました。")

from pathlib import Path

if __name__ == "__main__":
    base_dir = Path(__file__).parent
    # ▼ 1. 入力ファイルと出力ファイルの名前を合わせる
    input_filename = str(base_dir / "input_data" / "SKM_C301i26041520130.pdf")            # 元のPDFファイル名
    output_filename = str(base_dir / "masked_SKM_C301i26041520130.pdf")    # 黒塗り後の出力ファイル名
    
    # ▼ 2. find_coords.pyで取得した座標をここに入力してください
    # (左上のX座標, 左上のY座標, 右下のX座標, 右下のY座標)
    # 例: (120.50, 180.20, 350.10, 210.80)
    target_coordinates = ( 284, 680, 572, 750) # ← ※調べる前の一時的な仮の値です。書き換えてください。
    
    try:
        mask_name_field(input_filename, output_filename, target_coordinates)
    except Exception as e:
         print(f"エラーが発生しました: {e}")
         print(f"'{input_filename}' が同じフォルダに存在するか確認してください。")
