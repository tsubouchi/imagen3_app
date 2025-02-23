import os
import requests
import json
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# 環境変数からAPIキーを取得
api_key = os.getenv('GEMINI_API_KEY')

def call_gemini_api(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    headers = {
        'Content-Type': 'application/json'
    }
    
    data = {
        "contents": [{
            "parts":[{"text": prompt}]
        }]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # エラーチェック
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"APIリクエストエラー: {e}")
        return None

if __name__ == "__main__":
    print("\n=== Gemini AIチャット ===")
    print("終了するには 'quit' または 'exit' と入力してください。")
    
    while True:
        # ユーザーからの入力を受け付ける
        prompt = input("\nあなたの質問を入力してください: ")
        
        # 終了コマンドのチェック
        if prompt.lower() in ['quit', 'exit']:
            print("チャットを終了します。")
            break
            
        if not prompt.strip():  # 空の入力をチェック
            print("質問を入力してください。")
            continue
            
        # APIを呼び出して結果を取得
        result = call_gemini_api(prompt)
        
        if result:
            try:
                text = result['candidates'][0]['content']['parts'][0]['text']
                print("\n=== AIからの回答 ===")
                print(text)
                print("\n=== 使用トークン数 ===")
                print(f"プロンプトトークン: {result['usageMetadata']['promptTokenCount']}")
                print(f"応答トークン: {result['usageMetadata']['candidatesTokenCount']}")
                print(f"合計トークン: {result['usageMetadata']['totalTokenCount']}")
            except (KeyError, IndexError) as e:
                print(f"レスポンスの解析エラー: {e}")
                print("生のレスポンス:")
                print(json.dumps(result, indent=2, ensure_ascii=False)) 