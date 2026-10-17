"""Documented Govee LAN commands only. No cloud credentials or private API."""
from dataclasses import dataclass
import ipaddress
import json
import socket
import time
from .core import Capabilities, integer

SCAN_TARGET = ('239.255.255.250', 4001)
REPLY_PORT = 4002
CONTROL_PORT = 4003
MAX_PACKET = 8192


def packet(command, data):
    return json.dumps({'msg': {'cmd': command, 'data': data}}, separators=(',', ':')).encode()


def local_address(value, allow_loopback=False):
    try:
        ip = ipaddress.IPv4Address(value)
    except ipaddress.AddressValueError as exc:
        raise ValueError('an IPv4 address is required') from exc
    if ip.is_multicast or ip.is_unspecified or ip.is_reserved or ip.is_link_local:
        raise ValueError('invalid device address')
    if ip.is_loopback:
        if not allow_loopback:
            raise ValueError('loopback is only for protocol tests')
    elif not (ip in ipaddress.IPv4Network('10.0.0.0/8') or
              ip in ipaddress.IPv4Network('172.16.0.0/12') or
              ip in ipaddress.IPv4Network('192.168.0.0/16')):
        raise ValueError('only private LAN devices are supported')
    if str(ip).endswith('.255'):
        raise ValueError('broadcast addresses are not targets')
    return str(ip)


@dataclass(frozen=True)
class Device:
    address: str
    device_id: str
    model: str


def parse_scan(raw, sender, allow_loopback=False):
    if len(raw) > MAX_PACKET:
        raise ValueError('oversized discovery reply')
    envelope = json.loads(raw)
    if not isinstance(envelope, dict) or not isinstance(envelope.get('msg'), dict):
        raise ValueError('invalid response envelope')
    msg = envelope['msg']
    if msg.get('cmd') != 'scan':
        raise ValueError('not a discovery response')
    d = msg.get('data')
    if not isinstance(d, dict):
        raise ValueError('invalid response data')
    address = local_address(d['ip'], allow_loopback)
    # Never redirect control to an address supplied by an unrelated responder.
    if address != sender:
        raise ValueError('discovery address does not match sender')
    identity, model = d.get('device'), d.get('sku')
    if not isinstance(identity, str) or not 1 <= len(identity) <= 80:
        raise ValueError('invalid device identifier')
    if not isinstance(model, str) or not 1 <= len(model) <= 32 or not model.isalnum():
        raise ValueError('invalid model')
    return Device(address, identity, model)


def discover(seconds=3.0, interface='0.0.0.0', target=SCAN_TARGET, reply_port=REPLY_PORT,
             allow_loopback=False):
    if not 0.2 <= seconds <= 10:
        raise ValueError('discovery must be bounded to 0.2–10 seconds')
    found = {}
    # Exclusive bind prevents competing LAN clients from silently stealing replies.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((interface, reply_port))
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
        if interface != '0.0.0.0' and not allow_loopback:
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(interface))
        sock.sendto(packet('scan', {'account_topic': 'reserve'}), target)
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            sock.settimeout(max(0.001, deadline - time.monotonic()))
            try:
                raw, sender = sock.recvfrom(MAX_PACKET + 1)
                device = parse_scan(raw, sender[0], allow_loopback)
                if len(found) < 64:
                    found[device.device_id] = device
            except socket.timeout:
                break
            except (ValueError, KeyError, TypeError, UnicodeError, RecursionError):
                continue
    return tuple(found.values())


class GoveeLan:
    capabilities = Capabilities(rgb=True, power=True, zones=1, acknowledged=False)

    def __init__(self, address, port=CONTROL_PORT, allow_loopback=False, sock=None):
        self.address = local_address(address, allow_loopback)
        self.port = integer(port, 1, 65535)
        self.socket = sock or socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(.2)
        self.closed = False

    def _send(self, command, data):
        if self.closed:
            raise RuntimeError('adapter is closed')
        self.socket.sendto(packet(command, data), (self.address, self.port))

    def color(self, rgb):
        if len(rgb) != 3:
            raise ValueError('RGB must have three channels')
        r,g,b = (integer(c,0,255) for c in rgb)
        self._send('colorwc', {'color': {'r': r, 'g': g, 'b': b}, 'colorTemInKelvin': 0})

    def off(self):
        self._send('turn', {'value': 0})

    def close(self):
        self.closed = True
        self.socket.close()
