"""Exercise QEMU's JSON wire contracts, including reconnect synchronization."""
import importlib.util
import json
from pathlib import Path
import socket
import tempfile
import threading
import unittest

spec=importlib.util.spec_from_file_location('novaos_iso_boot',Path(__file__).parent/'integration/iso_boot.py')
boot=importlib.util.module_from_spec(spec)
spec.loader.exec_module(boot)


class IsoProtocolTests(unittest.TestCase):
    def serve(self, handler, check):
        with tempfile.TemporaryDirectory(prefix='novaos-qmp-') as directory:
            path=Path(directory)/'rpc.sock'
            listener=socket.socket(socket.AF_UNIX);listener.bind(str(path));listener.listen(1)
            errors=[]
            def run():
                try:
                    conn,_=listener.accept()
                    with conn,conn.makefile('rwb',buffering=0) as stream:
                        handler(stream)
                except Exception as error: errors.append(error)
                finally: listener.close()
            worker=threading.Thread(target=run,daemon=True);worker.start()
            try: check(path)
            finally: worker.join(timeout=5)
            self.assertFalse(worker.is_alive(),'Protocol server did not finish')
            if errors: raise errors[0]

    def test_guest_agent_discards_stale_reply_before_ping(self):
        def handler(stream):
            request=json.loads(stream.readline().lstrip(b'\xff'))
            self.assertEqual(request['execute'],'guest-sync-delimited')
            stream.write(b'{"return":{}}\n')
            stream.write(b'\xff'+json.dumps({'return':request['arguments']['id']}).encode()+b'\n')
            self.assertEqual(json.loads(stream.readline())['execute'],'guest-ping')
            stream.write(b'{"return":{}}\n')
        def check(path):
            client=boot.JsonSocket(path)
            try: self.assertEqual(client.call('guest-ping'),{})
            finally: client.close()
        self.serve(handler,check)

    def test_qmp_skips_events_between_command_responses(self):
        def handler(stream):
            stream.write(b'{"QMP":{"version":{}}}\n')
            self.assertEqual(json.loads(stream.readline())['execute'],'qmp_capabilities')
            stream.write(b'{"event":"RESUME"}\n{"return":{}}\n')
            self.assertEqual(json.loads(stream.readline())['execute'],'query-status')
            stream.write(b'{"return":{"status":"running"}}\n')
        def check(path):
            client=boot.JsonSocket(path,qmp=True)
            try: self.assertEqual(client.call('query-status')['status'],'running')
            finally: client.close()
        self.serve(handler,check)


if __name__=='__main__':unittest.main()
