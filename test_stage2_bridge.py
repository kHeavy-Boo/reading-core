"""10 independent local tests. No Ollama or live VOICEVOX required."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock
from reading_bridge_lab import ReadingBridgeLab, make_server

class Stage2Tests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.mock_engine = MagicMock()
        self.mock_engine.audio_query.return_value = {'kana': 'ニンキ'}
        self.mock_engine.corrected_query.return_value = ('夜のひとけのない山道。', {'kana': 'ヒトケ'})
        self.mock_engine.synthesize.return_value = b'RIFF' + b'0' * 40
        self.lab = ReadingBridgeLab(self.mock_engine, Path(self.folder.name))
        self.payload = {'text': '夜の人気のない山道。',
                        'readings': [{'word': '人気', 'reading': 'ひとけ'}]}

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

if __name__ == '__main__':
    unittest.main(verbosity=2)
