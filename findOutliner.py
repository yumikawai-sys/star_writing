import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# 1. 設定
INPUT_FILE = "input.csv"          # 元のCSVファイル名
OUTPUT_FILE = "outliers.csv"     # 異常データの書き出し先
THRESHOLD = 0.7                  # 類似度の閾値（低いほど「明らかにおかしいもの」に絞られます）

# 2. モデルのロード（ローカルで動作）
print("モデルをロード中...")
model = SentenceTransformer('intfloat/multilingual-e5-small')

def main():
    try:
        # CSV読み込み（列番号で指定: C列=2, D列=3）
        # header=None の場合は列番号で、ヘッダーがある場合は名前で指定できるよう調整
        df = pd.read_csv(INPUT_FILE)
        
        # 列名を取得（C列とD列を特定）
        u_col = df.columns[2]  # C列: Utterance
        i_col = df.columns[3]  # D列: Intent
        
        print(f"分析開始: {u_col} (Utterance) と {i_col} (Intent) をチェックします。")

        outlier_list = []

        # Intentごとにグループ化して分析
        unique_intents = df[i_col].unique()
        
        for intent in unique_intents:
            subset = df[df[i_col] == intent].copy()
            
            # データが1つしかない場合は比較できないのでスキップ
            if len(subset) < 2:
                continue
                
            # Utteranceをベクトル化
            embeddings = model.encode(subset[u_col].tolist())
            
            # そのIntent全体の平均ベクトル（中心点）を計算
            centroid = np.mean(embeddings, axis=0).reshape(1, -1)
            
            # 各データの中心との類似度を計算
            similarities = cosine_similarity(embeddings, centroid).flatten()
            subset['similarity_score'] = similarities
            
            # 閾値より低い（意味が乖離している）ものを抽出
            outliers = subset[subset['similarity_score'] < THRESHOLD]
            outlier_list.append(outliers)

        # 3. 異常データの統合と保存
        if outlier_list:
            final_outliers = pd.concat(outlier_list)
            
            # 類似度が低い（おかしな可能性が高い）順に並び替え
            final_outliers = final_outliers.sort_values(by='similarity_score')
            
            # 別のCSVとして書き出し
            final_outliers.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
            
            print(f"完了！ {len(final_outliers)} 件の不一致候補を '{OUTPUT_FILE}' に保存しました。")
        else:
            print("不一致データは見つかりませんでした。")

    except Exception as e:
        print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()
