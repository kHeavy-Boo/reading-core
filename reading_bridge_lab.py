"""Independent Bridge-shaped test receiver. NOT installed in Ver.6.1."""
import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from reading_engine import ReadingCorrection, ReadingEngine

OUTPUT = Path(__file__).parent / 'reading_bridge_audio_test'

class ReadingBridgeLab:
    def __init__(self, engine=None, output=None):
        self.engine = engine if engine is not None else ReadingEngine()
        self.output = Path(output) if output is not None else OUTPUT
        self.lock = threading.Lock()

    def process(self, payload):
        if not isinstance(payload, dict):
            raise ValueError('Expected JSON object')
        text = payload.get('text')
        if not isinstance(text, str) or not text.strip() or len(text) > 400:
            raise ValueError('text must contain 1 to 400 characters')
        speaker = payload.get('speaker', 47)
        speed = payload.get('speed', 1.0)
        if type(speaker) is not int or not 0 <= speaker <= 999:
            raise ValueError('invalid speaker')
        if type(speed) not in (int, float) or not 0.5 <= speed <= 2.0:
            raise ValueError('invalid speed')
        cues = payload.get('readings', [])
        baseline = self.engine.audio_query(text, speaker, speed)
        query, spoken = baseline, text
        mode, note = 'original', ''
        if cues not in ([], None):
            try:
                if (not isinstance(cues, list) or len(cues) != 1
                        or not isinstance(cues[0], dict)
                        or set(cues[0]) != {'word', 'reading'}):
                    raise ValueError('one word/reading instruction required')
                word, reading = cues[0]['word'], cues[0]['reading']
                if not isinstance(word, str) or not isinstance(reading, str):
                    raise ValueError('instruction must use strings')
                spoken, query = self.engine.corrected_query(
                    text, ReadingCorrection(word, reading), speaker, speed)
                mode = 'corrected'
            except ValueError as err:
                mode, note = 'fallback_original', str(err)
                query, spoken = baseline, text
        wav = self.engine.synthesize(query, speaker)
        if not isinstance(wav, bytes) or not wav.startswith(b'RIFF'):
            raise ValueError('synthesis did not return a RIFF WAV')
        name = uuid.uuid4().hex[:12]
        report = {'mode': mode, 'original_text': text, 'tts_only_text': spoken,
                  'original_kana': baseline.get('kana', ''),
                  'final_kana': query.get('kana', ''), 'note': note,
                  'wav_file': name + '.wav',
                  'instruction_origin': 'test_fixture_not_chatgpt'}
        with self.lock:
            self.output.mkdir(parents=True, exist_ok=True)
            (self.output / (name + '.wav')).write_bytes(wav)
            (self.output / (name + '.json')).write_text(
                json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        return report


def make_server(lab):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def reply(self, code, body):
            data = json.dumps(body, ensure_ascii=False).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        def do_POST(self):
            if self.path != '/preview':
                return self.reply(404, {'error': 'not found'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 8192:
                    raise ValueError('invalid request size')
                payload = json.loads(self.rfile.read(length))
                return self.reply(200, lab.process(payload))
            except (ValueError, TypeError) as e:
                return self.reply(400, {'error': str(e)})
            except Exception as e:
                return self.reply(502, {'error': type(e).__name__})
    # Loopback only; ephemeral unused port avoids collision with Ver.6.1.
    return ThreadingHTTPServer(('127.0.0.1', 0), Handler)
