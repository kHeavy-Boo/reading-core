# Reading Core — 日本語音声の読み間違いを減らす開発用部品

**Reading Coreは、開発者が自分のソフトに組み込むためのPython製の部品です。** 動画ナレーションや日本語読み上げで、指定された漢字の読み方をVOICEVOXの音声合成に反映します。

**完成した読み上げアプリではありません。** インストールするだけで、ゆっくりMovieMaker 4、AviUtl、ChatGPT、NVDAなどの音声が自動で直るものではありません。これらは**用途をイメージするための例**であり、対応済みソフトの一覧ではありません。

> **まず何をすればいい？** PythonとVOICEVOXを準備し、このページの「最初の音声を作る」まで進んでください。自分のAIや動画制作ソフトにつなぎたい人向けに、その後の道筋とChatGPTへの依頼文も載せています。

## どんな場面で役立つ？

たとえば、YouTubeのAIアニメ、ゆっくり解説、VOICEVOX実況、動画のナレーション。読み上げ音声が「夜の人気のない山道」の「人気」を「にんき」と読んでしまうと、音声を作り直す手間がかかります。

Reading Coreは、外部から渡された **「人気 → ひとけ」** という指定を音声合成に反映します。

| ソフト・用途の例 | どう使うイメージ？ | 現在の対応 |
| --- | --- | --- |
| [VOICEVOX](https://voicevox.hiroshiba.jp/) を使った自作ナレーション生成 | 指定した読みでWAVを作り、動画に取り込む | **付属テストでWAV生成可能** |
| [ゆっくりMovieMaker 4](https://manjubox.net/ymm4/) | ナレーション生成経路に読み補正を組み込む | 連携プログラムが必要 |
| [AviUtl](https://spring-fragrance.mints.ne.jp/aviutl/) | 補正済みWAVを動画編集に使用する | WAVの取り込みは利用者側 |
| [Ollama](https://ollama.com/) を使う自作AI | AIが文脈から読み方を決め、Reading Coreに渡す | AI連携プログラムが必要 |
| ChatGPT・Web記事読み上げ・スクリーンリーダー | 取得した文章と読み指定を受け渡す | 専用の接続開発が必要 |

**注意：Reading Core自身は文脈を理解して読み方を決めません。** 読み方は人間、外部AI、または別のプログラムが指定します。特定の動画生成AIが音声まで一体生成する場合、その音声を直接修正する機能もありません。

## 仕組みを簡単に

```text
文章（台本・記事など）
       ↓
人間または外部AIが読みを指定（例：人気 → ひとけ）
       ↓
Reading Core（指定された読みを音声合成用に反映）
       ↓
VOICEVOX（WAV音声を生成）
       ↓
音声ファイルを再生・動画編集ソフトに取り込む
```

元の表示文章は変更せず、音声合成用の文章だけを補正します。VOICEVOXの辞書も変更しません。内部では補正した文章で `/audio_query` を作り直し、アクセントやモーラの解析結果を直接書き換えない方式です。

## 最初の音声を作る：Windowsでの導入手順

**ゴール：** 4つのサンプル文章をVOICEVOXで合成し、WAVファイルを再生する。**ここまではOllamaもChatGPT APIも不要です。**

### 1. 必要なソフトを用意する

- **Python 3.10以上**：[Python公式サイト](https://www.python.org/downloads/)から導入。Windowsではインストール時にPATHへの追加を選ぶと便利です。
- **VOICEVOX**：[公式サイト](https://voicevox.hiroshiba.jp/)から導入。起動しておいてください。
- **Reading Core**：このGitHubリポジトリのファイルを取得します。

この部品はPython標準ライブラリだけで動くため、追加の `pip install` は不要です。VOICEVOXエンジンの標準接続先は `http://127.0.0.1:50021` です。

### 2. Reading Coreを入手する

**Gitを使わない場合（初心者向け）：** GitHubの緑色の **Code** → **Download ZIP** → ZIPを展開。展開した `reading-core-main` フォルダを開き、エクスプローラーのアドレス欄に `powershell` と入力してEnterを押してください。そのフォルダを開いたPowerShellが起動します。

**Gitを使う場合：** PowerShellで次を実行します。

```powershell
git clone https://github.com/kHeavy-Boo/reading-core.git
cd reading-core
```

> リポジトリが非公開の間は、アクセス権のない人はZIPの取得やcloneができません。公開前の案内を読んでいる場合は、公開後に試してください。

### 3. Pythonが使えるか確認する

```powershell
python --version
```

**成功の目安：** `Python 3.10.x`、`Python 3.11.x` など、3.10以上が表示されます。見つからない場合は `py --version` も試してください。以下の `python` コマンドも、環境に応じて `py` に置き換えられます。

### 4. コードの基本テストを実行する

```powershell
python -m unittest -v test_stage2_bridge.py
```

**成功の目安：** 最後に `Ran 10 tests` と `OK` が表示されます。これは模擬VOICEVOXによるプログラムのテストで、**まだ音声は生成しません**。

### 5. VOICEVOXを起動し、実際にWAVを作る

VOICEVOXを起動した状態で、同じPowerShellから実行します。

```powershell
python bridge_handoff_test.py
```

このサンプルは次の4例を合成します。

| 文章 | 指定する読み |
| --- | --- |
| 夜の人気のない山道を歩いた。 | 人気 → ひとけ |
| 生物は冷蔵庫に入れてください。 | 生物 → なまもの |
| 市場で魚を買いました。 | 市場 → いちば |
| 今日の天気は晴れです。 | 指定なし |

**成功の目安：** PowerShellに `結果: 4/4 件合成` と表示され、`reading_bridge_audio_test` フォルダにWAVファイルとJSONレポートが生成されます。

Windowsで出力フォルダを開くには：

```powershell
explorer .\reading_bridge_audio_test
```

WAVファイルをダブルクリックして、読みが期待どおりか耳で確認してください。**ここまでできれば、Reading CoreからVOICEVOXへ読み指定を渡して音声を作る最初の実験は成功です。**

音声が自動再生されないのは仕様です。サンプルはファイル保存まで行います。

## 次に何を作る？ 自作AI・動画制作への応用

### A. まずは動画で使いたい

上の手順で作ったWAVを、普段使っている動画編集ソフトに取り込んでください。これが最短の活用方法です。動画制作ソフト内の音声生成を自動で置き換えたい場合は、そのソフト向けの連携プログラムを別途開発します。

### B. 自分の文章を指定した読みで合成したい（Python）

`reading_engine.py` の `ReadingEngine` を使います。以下を `my_voice.py` として同じフォルダに保存してください。

```python
from reading_engine import ReadingEngine, ReadingCorrection

engine = ReadingEngine()
text_for_voice, query = engine.corrected_query(
    original_text="夜の人気のない山道を歩いた。",
    correction=ReadingCorrection(word="人気", reading="ひとけ"),
    speaker=47,
)
wav = engine.synthesize(query, speaker=47)
with open("my_voice.wav", "wb") as f:
    f.write(wav)
print("完成: my_voice.wav")
```

VOICEVOXを起動してから：

```powershell
python my_voice.py
```

**成功の目安：** `完成: my_voice.wav` と表示され、ファイルが生成されます。`speaker=47` はサンプルの話者IDなので、使用中のVOICEVOXで有効なIDに変更できます。

### C. Ollamaを使って読み方を自動で判断させたい

[Ollama公式サイト](https://ollama.com/)でローカルAIを動かし、AIが出した読み指定をReading Coreに渡す構成が考えられます。

```text
台本 → OllamaのAIモデル（文脈を判断）
     → 読み指定（例：{"word":"人気","reading":"ひとけ"}）
     → Reading Core → VOICEVOX → WAV
```

**Ollamaをインストールするだけでは接続されません。** AIモデルの導入、AIへの問い合わせ、出力の検証、Reading Coreへの受け渡し、WAVの再生は追加開発が必要です。モデルによっては読みの判断を間違えることもあります。

#### ChatGPTに開発を手伝ってもらう場合

次の依頼文をコピーして、ChatGPTに貼り付けてください。

> Windowsで動く日本語読み上げアプリを作りたいです。私はプログラミング初心者です。
>
> 使用するもの：
> - Reading Core：https://github.com/kHeavy-Boo/reading-core
> - VOICEVOX：https://voicevox.hiroshiba.jp/
> - Ollama：https://ollama.com/
>
> まずReading CoreのREADMEと実際のコードを確認してください。最初はOllamaを使わず、文章と読み指定を入力してVOICEVOXでWAVを作り、再生できる最小構成を完成させてください。
>
> 動作確認後に、OllamaのローカルAIが文脈を判断して `word` と `reading` を返す機能を追加してください。読み指定の妥当性を確認してからReading Coreへ渡してください。
>
> Windows PowerShellで実行するコマンドを**一つずつ**示し、各段階で成功の目安とエラー時の対処方法を教えてください。既存のReading Coreの制約（1リクエスト1指定、対象語は1回だけ）を守り、勝手に対応済みとみなさないでください。

これは開発の**出発点**です。環境やモデルのダウンロード状況によって所要時間は変わり、短時間での完成を保証するものではありません。

## 開発者向け：アプリとの接続方法

### Pythonから直接呼ぶ

上記 `my_voice.py` の例を参考に、`ReadingEngine.corrected_query()` で補正済みの音声クエリを作り、`ReadingEngine.synthesize()` でWAVを取得します。

### JSONで受け渡す

`ReadingBridgeLab` が受け取るJSONの例：

```json
{
  "text": "夜の人気のない山道を歩いた。",
  "speaker": 47,
  "speed": 1.0,
  "readings": [
    {"word": "人気", "reading": "ひとけ"}
  ]
}
```

`reading_bridge_lab.py` は実験用の `POST /preview` 受信機能を提供しますが、**そのファイルを直接実行するだけではサーバーは起動しません**。

以下を `run_preview.py` として保存すれば、ローカルの受信サーバーを起動できます。

```python
from reading_bridge_lab import ReadingBridgeLab, make_server

server = make_server(ReadingBridgeLab())
print(f"http://127.0.0.1:{server.server_port}/preview")
try:
    server.serve_forever()
except KeyboardInterrupt:
    pass
finally:
    server.server_close()
```

```powershell
python run_preview.py
```

表示されたURLへ、上記JSONを `Content-Type: application/json` でPOSTします。返るのは**JSONレポート**で、WAV自体ではありません。WAVは `reading_bridge_audio_test` に保存されます。ポート番号は起動ごとに変わります。この受信口は**127.0.0.1限定の開発テスト用**で、認証付きの公開APIではありません。

## 困ったときは

| 症状 | 確認すること |
| --- | --- |
| `python` が見つからない | Python 3.10以上を導入。Windowsでは `py` も試す |
| `git` が見つからない | Gitを使わず **Code → Download ZIP** で取得 |
| `test_stage2_bridge.py` が見つからない | PowerShellをReading Coreのファイルがあるフォルダで開いているか確認 |
| `Ran 10 tests` と `OK` が出ない | エラーメッセージを確認。テストはVOICEVOX不要 |
| VOICEVOXに接続できない | VOICEVOXを起動し、エンジンの `127.0.0.1:50021` を確認 |
| 話者IDのエラー | 指定した `speaker` がVOICEVOXで利用可能か確認 |
| `fallback_original` と表示される | 読み指定が1件か、対象語が文章中に1回だけあるか、読みがひらがなか確認 |
| WAVが作られたのに音が出ない | サンプルは自動再生しない。出力フォルダのWAVを開く |
| WAVの読み方が違う | 指定した読みと生成WAVを確認。Reading Core自身は正解を判断しない |
| `reading_bridge_lab.py` を実行しても待ち受けない | 上記 `run_preview.py` から起動する |

## 現在の制約と公開範囲

- 現在の公開コードは**Stage 2の独立実験版**です。SKULLYNET Ver.6.1本体のコードは含みません。
- `ReadingBridgeLab` は**1リクエストにつき読み指定1件**。複数指定は元の文章での合成へ戻します。
- 対象語は文章中に**ちょうど1回**出現する必要があります。
- 指定できる読みは**ひらがなと長音記号（ー）**です。
- `ReadingBridgeLab` は文章**400文字以下**、速度**0.5〜2.0**、話者ID**0〜999の整数**に制限します。話者IDが実際に存在するかは別問題です。
- 読み指定が不正な場合は元の文章での合成に戻しますが、VOICEVOXの通信エラーまで自動復旧するわけではありません。
- AIによる文脈判断、ChatGPT・Ollamaとの自動接続、Chrome拡張、動画編集ソフトへのプラグイン、自動音声再生は含みません。
- このコードだけで、既存ソフトの音声を直接置換できるわけではありません。

## ライセンス

このリポジトリのPythonコードと文書は [MIT License](LICENSE) で公開しています。VOICEVOX本体・各音声ライブラリには、それぞれ別の利用条件が適用されます。

## ファイル一覧

| ファイル | 内容 |
| --- | --- |
| `reading_engine.py` | VOICEVOX向け読み補正・音声合成 |
| `reading_bridge_lab.py` | 入力検証、ローカルHTTP受信、WAV・JSON保存 |
| `bridge_handoff_test.py` | 4つの文章で実際の音声合成を試す |
| `test_stage2_bridge.py` | VOICEVOX不要の10件の単体テスト |
| `README.txt` | 開発当時の実験メモ |

## 開発の背景

日本語の漢字は文脈によって読み方が変わります。辞書へ一つの読みを固定登録するだけでは対応できない場合があるため、**外部で判断した読みを、音声合成時だけ適用する**方式を検証しています。

開発記事：[VOICEVOXの誤読を激減させた「Reading Core」の開発](https://skullynetproject.com/2026/10/21/voicevox%e3%81%ae%e8%aa%a4%e8%aa%ad%e3%82%92%e6%bf%80%e6%b8%9b%e3%81%95%e3%81%9b%e3%81%9f%e3%80%8creading-core%e3%80%8d%e3%81%ae%e9%96%8b%e7%99%ba/)

---

個人開発による実験的なソフトウェアです。すべての文章で正しい読みや自然な発音を保証するものではありません。VOICEVOXおよび各音声ライブラリの利用規約をご確認ください。
