import json
import socket
import threading
import unittest
from prism_lights.govee import packet, parse_scan, discover, GoveeLan, local_address


class ProtocolTests(unittest.TestCase):
    def test_scan_validation(self):
        raw=packet('scan',{'ip':'192.168.1.4','device':'mock-light','sku':'H0000'})
        self.assertEqual(parse_scan(raw,'192.168.1.4').model,'H0000')
        for raw,sender in [(raw,'192.168.1.5'),(b'{}','192.168.1.4'),
                           (b'{"msg":[]}','192.168.1.4'),(b'x'*9000,'192.168.1.4')]:
            with self.assertRaises((ValueError,KeyError)):parse_scan(raw,sender)
        for addr in ['8.8.8.8','239.255.255.250','0.0.0.0','127.0.0.1','192.168.1.255']:
            with self.assertRaises(ValueError):local_address(addr)

    def test_mock_discovery_and_real_udp_commands(self):
        # Loopback protocol peer only. No broadcast, real light or physical LAN.
        server=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);server.bind(('127.0.0.1',0));server.settimeout(2)
        holder=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);holder.bind(('127.0.0.1',0));reply_port=holder.getsockname()[1];holder.close()
        received=[];errors=[]
        def peer():
            try:
                raw,sender=server.recvfrom(8192);received.append(json.loads(raw))
                server.sendto(b'{"msg":[]}',('127.0.0.1',reply_port))
                server.sendto(packet('scan',{'ip':'127.0.0.1','device':'mock-only','sku':'H0000'}),('127.0.0.1',reply_port))
                for _ in range(2):
                    raw,_=server.recvfrom(8192);received.append(json.loads(raw))
            except Exception as e:errors.append(e)
        thread=threading.Thread(target=peer);thread.start()
        try:
            devices=discover(.2,target=server.getsockname(),reply_port=reply_port,allow_loopback=True)
            self.assertEqual(len(devices),1)
            adapter=GoveeLan('127.0.0.1',server.getsockname()[1],allow_loopback=True)
            adapter.color((12,34,56));adapter.off();adapter.close()
            thread.join(3)
            self.assertEqual(errors,[])
            self.assertEqual(received[0],{'msg':{'cmd':'scan','data':{'account_topic':'reserve'}}})
            self.assertEqual(received[1],{'msg':{'cmd':'colorwc','data':{'color':{'r':12,'g':34,'b':56},'colorTemInKelvin':0}}})
            self.assertEqual(received[2],{'msg':{'cmd':'turn','data':{'value':0}}})
        finally:
            thread.join(3);server.close()
