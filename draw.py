import os
import json
import time
import asyncio
from dotenv import load_dotenv
from google import genai
from PIL import Image
import matplotlib.pyplot as plt
from deep_translator import GoogleTranslator
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# .envファイルから環境変数を読み込む
load_dotenv()

# Google Cloud プロジェクト情報の設定
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = "us-central1"

# Generative AI クライアントの初期化
client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

# 翻訳機の初期化
translator = GoogleTranslator(source='ja', target='en')

def translate_to_english(text):
    """日本語のテキストを英語に翻訳する関数"""
    try:
        return translator.translate(text)
    except Exception as e:
        print(f"翻訳エラー: {str(e)}")
        return text

def should_retry_error(exception):
    """リトライすべきエラーかどうかを判断する関数"""
    if hasattr(exception, 'code'):
        # Resource Exhaustedやその他の一時的なエラーの場合はリトライ
        return exception.code in [429, 503, 504]
    return False

@retry(
    stop=stop_after_attempt(3),  # 最大3回試行
    wait=wait_exponential(multiplier=1, min=4, max=10),  # 4-10秒の間で指数的に待機時間を増やす
    retry=retry_if_exception_type((Exception,)),
    before_sleep=lambda retry_state: print(f"リトライ待機中... ({retry_state.attempt_number}/3)")
)
async def generate_image_with_retry(prompt, config):
    """リトライ機能付きの画像生成関数"""
    return client.models.generate_images(
        model="imagen-3.0-generate-002",
        prompt=prompt,
        config=config,
    )

async def generate_single_image(prompt, session_dir, prompt_index, image_count):
    """1つのプロンプトに対して画像を生成する非同期関数"""
    try:
        print(f"\n=== プロンプト {prompt_index} の処理を開始 ===")
        # プロンプトを英語に翻訳
        english_prompt = translate_to_english(prompt)
        print(f"元のプロンプト: {prompt}")
        print(f"英語の翻訳: {english_prompt}")
        print("画像生成中...")

        # 画像生成の設定
        config = genai.types.GenerateImagesConfig(
            number_of_images=image_count,
            aspect_ratio="1:1",
            enhance_prompt=True,
            safety_filter_level="BLOCK_MEDIUM_AND_ABOVE",
            person_generation="DONT_ALLOW",
        )

        # リトライ機能付きで画像を生成
        image = await generate_image_with_retry(english_prompt, config)
        
        result = None
        if image.generated_images:
            print("=== 拡張されたプロンプト ===")
            print(image.generated_images[0].enhanced_prompt)
            
            # プロンプトごとのディレクトリを作成
            prompt_dir = f"{session_dir}/prompt_{prompt_index}"
            os.makedirs(prompt_dir, exist_ok=True)
            
            image_paths = []
            for j, gen_image in enumerate(image.generated_images, 1):
                # 画像を保存
                save_path = f"{prompt_dir}/image_{j}.png"
                gen_image.image._pil_image.save(save_path)
                image_paths.append(f"prompt_{prompt_index}/image_{j}.png")
                print(f"画像を保存しました: {save_path}")
                
                # 画像を表示
                plt.figure(figsize=(10, 10))
                plt.imshow(gen_image.image._pil_image)
                plt.axis('off')
                plt.show()
            
            result = {
                'prompt': prompt,
                'english_prompt': english_prompt,
                'enhanced_prompt': image.generated_images[0].enhanced_prompt,
                'images': image_paths,
                'status': 'success'
            }
            print(f"=== プロンプト {prompt_index} の処理が完了 ===\n")
        
        return result
    
    except asyncio.CancelledError:
        print(f"\nプロンプト {prompt_index} の処理を中断しました。")
        raise
    except Exception as e:
        error_message = str(e)
        print(f"プロンプト {prompt_index} でエラーが発生しました: {error_message}")
        
        # エラー情報を含むresultを返す
        return {
            'prompt': prompt,
            'english_prompt': english_prompt if 'english_prompt' in locals() else None,
            'error': error_message,
            'status': 'error',
            'retry_count': getattr(e, 'retry_count', 0)
        }

async def generate_images(prompts, image_count=1, session_id=None):
    """複数の画像を非同期で生成する関数"""
    try:
        if session_id is None:
            session_id = int(time.time())
        
        # セッション用のディレクトリを作成
        session_dir = f"images/{session_id}"
        os.makedirs(session_dir, exist_ok=True)
        
        results = []
        # プロンプトを1つずつ処理（同時実行を避ける）
        for i, prompt in enumerate(prompts, 1):
            try:
                # 2秒間待機してレート制限を回避
                if i > 1:
                    print(f"\nレート制限を回避するため {i*2} 秒待機します...")
                    await asyncio.sleep(i * 2)
                
                result = await generate_single_image(prompt, session_dir, i, image_count)
                if result:
                    results.append(result)
            except asyncio.CancelledError:
                print("\n画像生成をキャンセルしました。")
                raise
            except Exception as e:
                print(f"プロンプト {i} の処理中にエラーが発生: {str(e)}")
        
        # 成功した結果のみをカウント
        successful_results = [r for r in results if r.get('status') == 'success']
        
        # 処理結果のサマリーを表示
        print("\n=== 処理結果のサマリー ===")
        print(f"総プロンプト数: {len(prompts)}")
        print(f"成功したプロンプト数: {len(successful_results)}")
        print(f"生成された画像の総数: {sum(len(r['images']) for r in successful_results)}")
        
        # エラーがあった場合は表示
        failed_results = [r for r in results if r.get('status') == 'error']
        if failed_results:
            print("\n=== 失敗したプロンプト ===")
            for r in failed_results:
                print(f"プロンプト: {r['prompt']}")
                print(f"エラー: {r.get('error')}")
                print(f"リトライ回数: {r.get('retry_count', 0)}")
        
        # 生成結果をJSONファイルとして保存
        with open(f"{session_dir}/metadata.json", 'w', encoding='utf-8') as f:
            json.dump({
                'session_id': session_id,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'summary': {
                    'total_prompts': len(prompts),
                    'successful_prompts': len(successful_results),
                    'total_images': sum(len(r['images']) for r in successful_results),
                    'failed_prompts': len(failed_results)
                },
                'results': results
            }, f, ensure_ascii=False, indent=2)
        
        return results
    
    except asyncio.CancelledError:
        print("\n画像生成を中断しました。")
        raise
    except KeyboardInterrupt:
        print("\n画像生成を中断しました。")
        raise
    except Exception as e:
        print(f"\n予期せぬエラーが発生しました: {str(e)}")
        raise

async def main():
    print("\n=== Imagen 画像生成 ===")
    print("終了するには 'quit' または 'exit' と入力してください。")
    print("複数行のプロンプトを一括で入力する場合は、空行を2回入力してください。")
    print("プロンプトを直接コピー＆ペーストすることもできます。")
    print("入力を完了するには、'done'と入力してください。")
    print("プログラムを終了するには Ctrl+C を押してください。")
    
    try:
        while True:
            try:
                prompts = []
                current_prompt = []
                
                print("\n=== プロンプトを入力してください ===")
                print("(複数行の場合は、最後に空行を2回入力してください)")
                
                while True:
                    try:
                        # 複数行の入力を受け付ける
                        lines = []
                        while True:
                            line = input().strip() if not lines else input("... ").strip()
                            
                            if line.lower() in ['quit', 'exit']:
                                print("\nプログラムを終了します。")
                                return
                            
                            if line.lower() == 'done':
                                if current_prompt:
                                    prompts.append(' '.join(current_prompt))
                                break
                            
                            # 空行が入力された場合
                            if not line:
                                if lines:  # 複数行入力の終了
                                    current_prompt.append(' '.join(lines))
                                    lines = []
                                elif current_prompt:  # プロンプトの区切り
                                    prompts.append(' '.join(current_prompt))
                                    current_prompt = []
                                continue
                            
                            lines.append(line)
                        
                        if line.lower() == 'done':
                            break
                    
                    except KeyboardInterrupt:
                        print("\n\nプログラムを終了します。")
                        return
                
                if not prompts and not current_prompt:
                    print("説明を入力してください。")
                    continue
                
                if current_prompt:  # 未保存のプロンプトがある場合
                    prompts.append(' '.join(current_prompt))
                
                # 入力されたプロンプトの確認
                print("\n=== 入力されたプロンプト ===")
                for i, p in enumerate(prompts, 1):
                    print(f"\nプロンプト {i}:")
                    print(p)
                
                try:
                    if input("\nこれらのプロンプトで生成を開始しますか？ (y/n): ").lower() != 'y':
                        continue
                except KeyboardInterrupt:
                    print("\n\nプログラムを終了します。")
                    return
                
                # 画像の生成数を指定
                try:
                    count = int(input("\n各プロンプトに対して生成する画像の数（1-4）: "))
                    count = max(1, min(4, count))
                except ValueError:
                    count = 1
                except KeyboardInterrupt:
                    print("\n\nプログラムを終了します。")
                    return
                
                print("\n画像を生成中...")
                await generate_images(prompts, image_count=count)
                
            except Exception as e:
                if isinstance(e, KeyboardInterrupt):
                    raise
                print(f"予期せぬエラーが発生しました: {str(e)}")
    
    except KeyboardInterrupt:
        print("\n\nプログラムを終了します。お疲れ様でした。")
        return

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nプログラムを正常に終了しました。")
    except Exception as e:
        print(f"\nエラーが発生しました: {str(e)}")
    finally:
        print("お疲れ様でした。") 