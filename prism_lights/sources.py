"""Public frame contract; no display capture or video recording occurs here."""
import json
import math
import os
import selectors
from .core import Frame

MAX_LINE = 65536


class JsonLineSource:
    """Nonblocking bounded pipe reader. Retains only the newest available frame."""
    def __init__(self, stream):
        self.fd = stream.fileno()
        self.old_blocking = os.get_blocking(self.fd)
        os.set_blocking(self.fd, False)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.fd, selectors.EVENT_READ)
        self.buffer = b''
        self.eof = False
        self.rejected = 0
        self.dropping = False

    def poll(self):
        if self.eof or not self.selector.select(0):
            return None
        raw = os.read(self.fd, MAX_LINE)
        if not raw:
            self.eof = True
            if self.buffer:
                self.rejected += 1  # Incomplete lines are not frames.
            self.buffer = b''
            return None
        # A strict per-poll read budget prevents a noisy producer starving ticks.
        chunks = (self.buffer + raw).split(b'\n')
        self.buffer = chunks.pop()
        latest = None
        for line in chunks:
            if self.dropping:
                self.dropping = False
                continue
            if len(line) > MAX_LINE:
                self.rejected += 1
                continue
            try:
                latest = Frame.parse(json.loads(line))
            except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
                self.rejected += 1
        if len(self.buffer) > MAX_LINE:
            self.buffer = b''
            self.dropping = True
            self.rejected += 1
        return latest

    def close(self):
        self.selector.close()
        os.set_blocking(self.fd, self.old_blocking)


class Simulator:
    """Synthetic changing sky/fire/water colors; never represented as captured TV."""
    eof = False
    rejected = 0

    def __init__(self, clock):
        self.clock, self.start = clock, clock()

    def poll(self):
        t = self.clock() - self.start
        p = []
        for y in range(6):
            for x in range(12):
                p.append([round(95 + 85*math.sin(t*.7+x*.2+y*.1)),
                          round(85 + 65*math.sin(t*.47+x*.1+2)),
                          round(90 + 80*math.sin(t*.33+y*.15+4))])
        return Frame.parse({'version': 1, 'width': 12, 'height': 6, 'pixels': p})

    def close(self):
        pass
