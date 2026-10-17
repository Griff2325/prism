import json
import os
import unittest
import subprocess
import sys
from prism_lights.sources import JsonLineSource, MAX_LINE
from prism_lights.cli import private_write, main
from tempfile import TemporaryDirectory
from pathlib import Path


class SourceTests(unittest.TestCase):
    def setUp(self):
        r,self.w=os.pipe();self.reader=os.fdopen(r,'rb',buffering=0)
        self.source=JsonLineSource(self.reader)
    def tearDown(self):
        self.source.close();self.reader.close();os.close(self.w)
    def test_partial_latest_and_bad_lines(self):
        def line(c):return json.dumps({'version':1,'width':1,'height':1,'pixels':[[c,0,0]]}).encode()+b'\n'
        first=line(12);os.write(self.w,first[:10]);self.assertIsNone(self.source.poll())
        os.write(self.w,first[10:]+b'bad\n'+line(80))
        self.assertEqual(self.source.poll().pixels,((80,0,0),))
        self.assertEqual(self.source.rejected,1)
    def test_overlong_line_recovers(self):
        # Pipes are deliberately drained between bounded writes.
        for _ in range(20):
            os.write(self.w,b'x'*4096);self.source.poll()
        os.write(self.w,b'\n{"version":1,"width":1,"height":1,"pixels":[[1,2,3]]}\n')
        self.assertEqual(self.source.poll().pixels,((1,2,3),))
        self.assertGreaterEqual(self.source.rejected,1)
        self.assertLessEqual(len(self.source.buffer),MAX_LINE)
    def test_private_config_permissions(self):
        with TemporaryDirectory() as d:
            path=Path(d)/'.local'/'config.json'
            private_write(path,{'version':1})
            self.assertEqual(path.stat().st_mode & 0o777,0o600)
            self.assertEqual(json.loads(path.read_text()),{'version':1})
    def test_live_requires_config(self):
        with TemporaryDirectory() as d:
            self.assertEqual(main(['run','--live','--config',d+'/absent']),2)

    def test_multi_selection_and_duplicate_rejection(self):
        with TemporaryDirectory() as d:
            discovery=Path(d)/'discovery.json';config=Path(d)/'config.json'
            private_write(discovery, {'version':1,'devices':[
                {'address':'192.168.1.4','device_id':'mock-a','model':'H0000'},
                {'address':'192.168.1.5','device_id':'mock-b','model':'H0000'}]})
            self.assertEqual(main(['configure','--discovery',str(discovery),'--output',str(config),
                                   '--device','1:left','--device','2:right']),0)
            saved=json.loads(config.read_text())
            self.assertEqual([v['zone'] for v in saved['devices']],['left','right'])
            self.assertEqual(main(['configure','--discovery',str(discovery),'--output',str(config),
                                   '--device','1','--device','1']),2)
            self.assertEqual(json.loads(config.read_text()),saved)

    def test_empty_stdin_exits_without_lighting_output(self):
        result=subprocess.run([sys.executable,'-m','prism_lights','run','--source','stdin',
                               '--duration','0'],input=b'',capture_output=True,timeout=2)
        self.assertEqual(result.returncode,0)
        self.assertEqual(result.stdout,b'')
