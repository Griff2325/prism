import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import signal
import sys
import time
from .core import Capabilities, Engine
from .govee import discover, GoveeLan, local_address
from .sources import JsonLineSource, Simulator


class Preview:
    capabilities = Capabilities(rgb=True, power=True)
    def color(self, rgb):
        print(json.dumps({'preview_rgb': rgb}), flush=True)
    def off(self):
        print('{"preview_power":"off"}', flush=True)
    def close(self):
        pass


def private_write(path, value):
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, 'w') as out:
            json.dump(value, out, indent=2)
            out.write('\n')
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def read_json(path):
    if Path(path).stat().st_size > 65536:
        raise ValueError('configuration too large')
    with open(path) as source:
        return json.load(source)


def make_parser():
    p = argparse.ArgumentParser(description='Prism local frame-to-light harness')
    sub = p.add_subparsers(dest='command', required=True)
    d = sub.add_parser('discover', help='one bounded, read-only LAN discovery')
    d.add_argument('--seconds', type=float, default=3)
    d.add_argument('--interface', default='0.0.0.0')
    d.add_argument('--output', default='.local/discovery.json')
    c = sub.add_parser('configure', help='select discovered RGB lights; sends nothing')
    c.add_argument('--discovery', default='.local/discovery.json')
    c.add_argument('--device', action='append', required=True, help='repeat INDEX or INDEX:ZONE; 1-based discovery index')
    c.add_argument('--output', default='.local/config.json')
    c.add_argument('--zone', choices=['all','left','right','top','bottom'], default='all')
    r = sub.add_parser('run', help='preview by default; --live explicitly permits light changes')
    r.add_argument('--source', choices=['simulator','stdin'], default='simulator')
    r.add_argument('--config', default='.local/config.json')
    r.add_argument('--live', action='store_true')
    r.add_argument('--duration', type=float, default=10, help='seconds; 0 for persistent service')
    r.add_argument('--hz', type=float, default=5)
    r.add_argument('--smoothing', type=float, default=.35)
    r.add_argument('--channel-cap', type=int, default=160)
    r.add_argument('--stale-seconds', type=float, default=3)
    r.add_argument('--stale-policy', choices=['hold','off'], default='hold')
    return p


def run(args):
    if not 0 <= args.duration <= 86400:
        raise ValueError('duration must be 0 or at most one day')
    targets = []
    if args.live:
        config = read_json(args.config)
        if config.get('version') != 1 or config.get('selected') is not True:
            raise ValueError('explicitly selected device configuration required')
        devices = config.get('devices')
        if not isinstance(devices, list) or not 1 <= len(devices) <= 8:
            raise ValueError('select 1–8 devices')
        validated = [(local_address(d['device']['address']), d.get('zone', 'all')) for d in devices]
        if len({a for a,z in validated}) != len(validated):
            raise ValueError('duplicate device selection')
        targets = validated
    engines = []
    source = None
    stopped = False
    def stop(signum, frame):
        nonlocal stopped
        stopped = True
    previous = {sig: signal.signal(sig, stop) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        for address, zone in targets or [(None, 'all')]:
            adapter = GoveeLan(address) if address else Preview()
            try:
                engines.append(Engine(adapter, zone, args.hz, args.smoothing, args.channel_cap,
                                      args.stale_seconds, args.stale_policy))
            except Exception:
                adapter.close()
                raise
        source = Simulator(time.monotonic) if args.source == 'simulator' else JsonLineSource(sys.stdin.buffer)
        start = time.monotonic()
        while not stopped and (not args.duration or time.monotonic() - start < args.duration):
            frame = source.poll()
            now = time.monotonic()
            for engine in engines:
                if frame is not None:
                    engine.submit(frame, now)
                engine.tick(now)
            if getattr(source, 'eof', False) and all(e.stale or e.received is None for e in engines):
                break
            time.sleep(.02)
        print('Stopped; rejected input frames: ' + str(source.rejected), file=sys.stderr)
    finally:
        try:
            for engine in engines:
                try:
                    engine.close()
                except OSError:
                    # Cleanup is best effort; still release the other adapters.
                    pass
        finally:
            if source:
                source.close()
            for sig, handler in previous.items():
                signal.signal(sig, handler)
    return 0


def main(argv=None):
    args = make_parser().parse_args(argv)
    try:
        if args.command == 'discover':
            devices = discover(args.seconds, args.interface)
            private_write(args.output, {'version': 1, 'devices': [asdict(d) for d in devices]})
            print('Found ' + str(len(devices)) + ' LAN device(s); private details saved locally.')
            for i,d in enumerate(devices,1):
                print(str(i) + ': ' + d.model)
        elif args.command == 'configure':
            data = read_json(args.discovery)
            if data.get('version') != 1 or not 1 <= len(args.device) <= 8:
                raise ValueError('select 1–8 discovery indices')
            selected = []
            for choice in args.device:
                index, _, zone = choice.partition(':')
                index, zone = int(index), zone or args.zone
                if not 1 <= index <= len(data['devices']) or zone not in ('all','left','right','top','bottom'):
                    raise ValueError('invalid device index or zone')
                device = data['devices'][index-1]
                local_address(device['address'])
                selected.append({'device':device,'zone':zone})
            if len({d['device']['address'] for d in selected}) != len(selected):
                raise ValueError('duplicate selection')
            private_write(args.output, {'version': 1, 'selected': True, 'devices': selected})
            print('Device selected locally. No light commands sent; run --live to opt in.')
        else:
            return run(args)
        return 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print('Prism could not complete this operation (' + type(exc).__name__ + '). '
              'Check configuration, LAN Control, UDP port availability and input format.', file=sys.stderr)
        return 2
