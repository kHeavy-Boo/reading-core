"""Simulate Bridge sending text + Skully pronunciation cues. No AI inference here."""
import json
import threading
import urllib.request
from reading_bridge_lab import ReadingBridgeLab, make_server

# Explicit cues simulate Skully's future metadata. They are NOT sent by ChatGPT yet.
CASES = [
    {'text': '夜の人気のない山道を歩いた。', 'speaker': 47,
     'readings': [{'word': '人気', 'reading': 'ひとけ'}]},
    {'text': '生物は冷蔵庫に入れてください。', 'speaker': 47,
     'readings': [{'word': '生物', 'reading': 'なまもの'}]},
    {'text': '市場で魚を買いました。', 'speaker': 47,
     'readings': [{'word': '市場', 'reading': 'いちば'}]},
    {'text': '今日の天気は晴れです。', 'speaker': 47},
]

def main():
    lab = ReadingBridgeLab()
    server = make_server(lab)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    success = 0
    try:
        print('Stage2: Bridge形式 → Reading Engine → VOICEVOX', flush=True)
        print('注意：読み方指示はテストコード内の指定値です。ChatGPT自動連携は未実装。', flush=True)
        for i, payload in enumerate(CASES, 1):
            print(f"\n[{i}] {payload['text']}", flush=True)
            req = urllib.request.Request(
                f'http://127.0.0.1:{server.server_port}/preview',
                data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                headers={'Content-Type': 'application/json'}, method='POST')
            try:
                with urllib.request.urlopen(req, timeout=60) as response:
                    report = json.load(response)
                print('  状態:', report['mode'])
                print('  元の読み:', report['original_kana'])
                print('  音声の読み:', report['final_kana'])
                print('  TTS用の文章:', report['tts_only_text'])
                print('  WAV:', report['wav_file'])
                success += 1
            except Exception as e:
                print('  失敗:', repr(e))
        print(f'\n結果: {success}/{len(CASES)} 件合成')
        print('保存先:', lab.output)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)

if __name__ == '__main__':
    main()
