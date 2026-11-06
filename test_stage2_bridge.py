"""10 independent local tests. No Ollama or live VOICEVOX required."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock
from reading_bridge_lab import ReadingBridgeLab, make_server
from reading_engine import ReadingEngine, ReadingCorrection, registered_readings

class Stage2Tests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.mock_engine = MagicMock()
        self.mock_engine.audio_query.return_value = {'kana': 'ニンキ'}
        self.mock_engine.corrected_query.return_value = ('夜のひとけのない山道。', {'kana': 'ヒトケ'})
        self.mock_engine.corrected_query_many.return_value = ('補正した文章', {'kana': 'ホセイ'})
        self.mock_engine.synthesize.return_value = b'RIFF' + b'0' * 40
        self.md_path = Path(self.folder.name) / 'misread.md'
        self.md_path.write_text('', encoding='utf-8')
        self.lab = ReadingBridgeLab(self.mock_engine, Path(self.folder.name), self.md_path)
        self.payload = {'text': '夜の人気のない山道。',
                        'readings': [{'word': '人気', 'reading': 'ひとけ'}]}

    def set_md(self, rows):
        self.md_path.write_text(
            '# 誤読\n\n## 再生に適用する登録語\n'
            '| 表記 | 読み | 適用条件 | 登録根拠・メモ |\n'
            '| --- | --- | --- | --- |\n' + '\n'.join(rows) +
            '\n\n## 要確認の候補（再生には使わない）\n'
            '| 表記 | 想定読み | 確認する文脈・理由 | 確認状態 |\n'
            '| --- | --- | --- | --- |\n'
            '| 太美 | ふとみ | 北海道の地名 | 未確認 |\n', encoding='utf-8')

    def tearDown(self):
        self.folder.cleanup()

    def test_01_correction_success(self):
        self.assertEqual(self.lab.process(self.payload)['mode'], 'corrected')

    def test_02_preserve_display_text(self):
        self.assertEqual(self.lab.process(self.payload)['original_text'], self.payload['text'])

    def test_03_uses_corrected_query(self):
        self.lab.process(self.payload)
        self.assertEqual(self.mock_engine.synthesize.call_args.args[0]['kana'], 'ヒトケ')

    def test_04_without_cues_original(self):
        self.assertEqual(self.lab.process({'text': '天気は晴れ。'})['mode'], 'original')
        self.mock_engine.corrected_query.assert_not_called()

    def test_05_multiple_cues_fallback(self):
        p = dict(self.payload)
        p['readings'] = self.payload['readings'] * 2
        self.assertEqual(self.lab.process(p)['mode'], 'fallback_original')

    def test_06_invalid_reading_fallback(self):
        self.mock_engine.corrected_query.side_effect = ValueError('bad reading')
        self.assertEqual(self.lab.process(self.payload)['mode'], 'fallback_original')

    def test_07_empty_text_reject(self):
        with self.assertRaises(ValueError):
            self.lab.process({'text': ''})

    def test_08_long_text_reject(self):
        with self.assertRaises(ValueError):
            self.lab.process({'text': 'あ' * 401})

    def test_09_bad_speed_reject(self):
        with self.assertRaises(ValueError):
            self.lab.process({'text': 'テスト', 'speed': 8})

    def test_10_only_local_server(self):
        server = make_server(self.lab)
        try:
            self.assertEqual(server.server_address[0], '127.0.0.1')
        finally:
            server.server_close()


    def test_11_md_applied_without_external_cue(self):
        self.set_md(['| 安定性 | あんていせい | * | 誤読訂正 |'])
        p = {'text': '安定性が大事です。'}
        self.assertEqual(self.lab.process(p)['mode'], 'md_corrected')
        args = self.mock_engine.corrected_query.call_args.args
        self.assertEqual(args[1], ReadingCorrection('安定性', 'あんていせい'))

    def test_12_md_wins_over_external_cue(self):
        self.set_md(['| 安定性 | あんていせい | * | 誤読訂正 |'])
        p = {'text': '安定性が大事です。',
             'readings': [{'word': '安定性', 'reading': 'やすていせい'}]}
        report = self.lab.process(p)
        self.assertEqual(report['mode'], 'md_corrected')
        self.assertEqual(self.mock_engine.corrected_query.call_args.args[1].reading, 'あんていせい')

    def test_13_context_mismatch_never_applied(self):
        self.set_md(['| 人気 | ひとけ | 人気のない | 例文 |'])
        report = self.lab.process({'text': '人気の商品です。'})
        self.assertEqual(report['mode'], 'original')
        self.mock_engine.corrected_query.assert_not_called()

    def test_14_candidate_never_applied(self):
        self.set_md([])
        report = self.lab.process({'text': '太美に住んでいます。'})
        self.assertEqual(report['mode'], 'original')

    def test_15_multi_md_corrections(self):
        self.set_md(['| 安定性 | あんていせい | * | 訂正 |',
                     '| 人気 | ひとけ | 人気のない | 例文 |'])
        report = self.lab.process({'text': '安定性と人気のない山道について。'})
        self.assertEqual(report['mode'], 'md_corrected')
        corrections = self.mock_engine.corrected_query_many.call_args.args[1]
        self.assertEqual([c.word for c in corrections], ['安定性', '人気'])

    def test_16_md_specific_context_wins(self):
        self.set_md(['| 人気 | にんき | * | 既定 |',
                     '| 人気 | ひとけ | 人気のない | 文脈 |'])
        rules = registered_readings('人気のない山道。', self.md_path)
        self.assertEqual(rules, [ReadingCorrection('人気', 'ひとけ')])

    def test_17_repeated_word_skipped(self):
        self.set_md(['| 安定性 | あんていせい | * | 訂正 |'])
        self.assertEqual(registered_readings('安定性と安定性', self.md_path), [])

    def test_18_compound_kanji_not_replaced(self):
        self.set_md(['| 生物 | なまもの | 生物は冷蔵庫 | 例文 |'])
        self.assertEqual(registered_readings('微生物は冷蔵庫に入れない。', self.md_path), [])

    def test_19_read_md_again_after_update(self):
        self.set_md([])
        self.assertEqual(registered_readings('安定性が大事', self.md_path), [])
        self.set_md(['| 安定性 | あんていせい | * | 訂正 |'])
        self.assertEqual(registered_readings('安定性が大事', self.md_path),
                         [ReadingCorrection('安定性', 'あんていせい')])

    def test_20_corrected_query_many_generates_fresh_audio_query(self):
        engine = ReadingEngine()
        engine.audio_query = MagicMock(return_value={'kana': 'テスト'})
        spoken, query = engine.corrected_query_many(
            '安定性と人気のない山道。',
            [ReadingCorrection('安定性', 'あんていせい'),
             ReadingCorrection('人気', 'ひとけ')], speaker=47)
        self.assertEqual(spoken, 'あんていせいとひとけのない山道。')
        engine.audio_query.assert_called_once_with(spoken, speaker=47, speed=1.0)
        self.assertEqual(query, {'kana': 'テスト'})

    def test_21_unregistered_external_still_works(self):
        self.set_md(['| 安定性 | あんていせい | * | 訂正 |'])
        self.assertEqual(self.lab.process(self.payload)['mode'], 'corrected')

    def test_22_md_and_external(self):
        self.set_md(['| 安定性 | あんていせい | * | 訂正 |'])
        report = self.lab.process({'text': '安定性と人気のない山道。',
                                   'readings': [{'word': '人気', 'reading': 'ひとけ'}]})
        self.assertEqual(report['mode'], 'md_and_external')
        self.mock_engine.corrected_query_many.assert_called_once()

    def test_23_unrelated_text_no_md(self):
        self.set_md(['| 安定性 | あんていせい | * | 訂正 |'])
        self.assertEqual(self.lab.process({'text': '今日は晴れ。'})['mode'], 'original')

    def test_24_invalid_registered_reading_skipped_and_logged(self):
        self.set_md(['| 安定性 | カタカナ | * | 誤記 |'])
        report = self.lab.process({'text': '安定性が大事。'})
        self.assertEqual(report['mode'], 'original')
        self.assertIn('MD lookup skipped', report['note'])

if __name__ == '__main__':
    unittest.main(verbosity=2)
