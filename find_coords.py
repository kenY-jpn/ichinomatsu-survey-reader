import fitz  # PyMuPDF
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from PIL import Image
import io

def get_coordinates(pdf_path):
    """
    PDFを開き、1ページ目を画像として表示し、
    クリックされた場所の座標（PDF上のポイント単位）を出力するヘルパー関数
    """
    print(f"PDF '{pdf_path}' を読み込んでいます...")
    # PDFファイルを開く
    doc = fitz.open(pdf_path)
    
    # 1ページ目 (インデックス0) を取得
    page = doc[0]
    
    # ページを画像(Pixmap)としてレンダリング 
    # デフォルトは 72dpi なので、画像のピクセル単位がそのままPDFのポイント単位（座標）と一致します
    pix = page.get_pixmap()
    
    # 画像データをPIL Imageに変換
    img_data = pix.tobytes("png")
    img = Image.open(io.BytesIO(img_data))
    
    # 画像を表示する準備
    fig, ax = plt.subplots(figsize=(8, 10))
    ax.imshow(img)
    ax.set_title("Click to get coordinates. Close window to exit.")
    
    print("\n--- 座標チェッカー ---")
    print("画面上のクリックした場所の座標がここに表示されます。")
    print("黒塗りしたい箇所の、①「左上」の端 と ②「右下」の端 をクリックして、")
    print("表示された2つの座標 (左上X, 左上Y, 右下X, 右下Y) をメモしてください。")
    print("------------------------\n")
    
    # クリックイベントのハンドラ関数（クリックされるたびに呼ばれる）
    def onclick(event):
        if event.xdata is not None and event.ydata is not None:
            # 小数点以下2桁で座標を出力
            print(f"クリックした座標 => X: {event.xdata:.2f}, Y: {event.ydata:.2f}")

    # クリックイベントとハンドラ関数を結びつける
    cid = fig.canvas.mpl_connect('button_press_event', onclick)
    
    # 画面を表示（ウィンドウを閉じるまでプログラムはここで待機します）
    # 画像ウィンドウでマウスを操作してください
    plt.show()

from pathlib import Path

if __name__ == "__main__":
    # ▼ ここに調べる対象のPDFファイル名を入力してください
    base_dir = Path(__file__).parent
    pdf_file = str(base_dir / "input_data" / "SKM_C301i26041520130.pdf")
    
    try:
         get_coordinates(pdf_file)
    except Exception as e:
         print(f"エラーが発生しました: {e}")
         print(f"'{pdf_file}' という名前のPDFファイルが同じフォルダに存在するか確認してください。")
         print("ファイル名が違う場合は、スクリプト下部の pdf_file の中身を書き換えてください。")
