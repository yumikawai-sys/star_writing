import pandas as pd
import re
import spacy

# 英語モデルのロード（初回のみ: python -m spacy download en_core_web_sm）
nlp = spacy.load("en_core_web_sm")

def clean_utterance(text):
    if not isinstance(text, str):
        return ""
    
    # 1. 小文字化
    text = text.lower()
    
    # 2. 正規表現：記号と数字を削除（a-zとスペースだけ残す）
    text = re.sub(r'[^a-z\s]', '', text)
    
    # 3. spaCyで解析（動詞の原形化・単数形化）
    doc = nlp(text)
    # 助詞や代名詞を除きたい場合は if not token.is_stop を追加
    cleaned_tokens = [token.lemma_ for token in doc]
    
    # 4. 余計な空白を詰めて結合
    return " ".join(cleaned_tokens).strip()

# CSVの読み込み（A列にUtteranceがある前提）
df = pd.read_csv('your_data.csv')
column_name = df.columns[0]  # A列を指定

# クレンジング実行
df['Cleaned_Utterance'] = df[column_name].apply(clean_utterance)

# 結果の保存
df.to_csv('cleaned_data.csv', index=False)
print("クレンジング完了！")
