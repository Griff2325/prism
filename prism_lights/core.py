"""Bounded frame sampling and transport-independent lighting policy."""
from dataclasses import dataclass
import math
from typing import Protocol

RGB = tuple[int, int, int]
MAX_PIXELS = 4096


def integer(value, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError('integer outside supported range')
    return value


@dataclass(frozen=True)
class Frame:
    width: int
    height: int
    pixels: tuple[RGB, ...]

    @classmethod
    def parse(cls, value):
        if not isinstance(value, dict) or type(value.get('version')) is not int or value.get('version') != 1:
            raise ValueError('frame version must be 1')
        w, h = integer(value.get('width'), 1, 128), integer(value.get('height'), 1, 128)
        p = value.get('pixels')
        if w * h > MAX_PIXELS or not isinstance(p, list) or len(p) != w * h:
            raise ValueError('invalid frame dimensions or pixels')
        out = []
        for color in p:
            if not isinstance(color, list) or len(color) != 3:
                raise ValueError('each pixel must be RGB')
            out.append(tuple(integer(c, 0, 255) for c in color))
        return cls(w, h, tuple(out))

    def sample(self, zone='all') -> RGB:
        if zone not in ('all', 'left', 'right', 'top', 'bottom'):
            raise ValueError('unsupported sample zone')
        points = []
        for y in range(self.height):
            for x in range(self.width):
                if (zone == 'all' or zone == 'left' and x < max(1, self.width // 3)
                    or zone == 'right' and x >= self.width - max(1, self.width // 3)
                    or zone == 'top' and y < max(1, self.height // 3)
                    or zone == 'bottom' and y >= self.height - max(1, self.height // 3)):
                    points.append(self.pixels[y * self.width + x])
        # Linear-light average avoids dark bias; black input remains black.
        return tuple(round((sum((p[c] / 255) ** 2.2 for p in points) / len(points)) ** (1/2.2) * 255)
                     for c in range(3))


@dataclass(frozen=True)
class Capabilities:
    rgb: bool = True
    power: bool = False
    zones: int = 1
    acknowledged: bool = False


class LightAdapter(Protocol):
    capabilities: Capabilities
    def color(self, rgb: RGB) -> None: ...
    def off(self) -> None: ...
    def close(self) -> None: ...


class FrameSource(Protocol):
    def poll(self) -> Frame | None: ...
    def close(self) -> None: ...


class Engine:
    """Latest-frame-only, monotonic-time policy. No network I/O until tick()."""
    def __init__(self, adapter: LightAdapter, zone='all', hz=5.0, smoothing=0.35,
                 channel_cap=160, stale_seconds=3.0, stale_policy='hold'):
        if not adapter.capabilities.rgb:
            raise ValueError('RGB adapter required')
        if zone not in ('all', 'left', 'right', 'top', 'bottom'):
            raise ValueError('invalid zone')
        if not (0.2 <= hz <= 10 and 0.05 <= smoothing <= 5 and 0.5 <= stale_seconds <= 60):
            raise ValueError('invalid timing bounds')
        integer(channel_cap, 1, 255)
        if stale_policy not in ('hold', 'off') or stale_policy == 'off' and not adapter.capabilities.power:
            raise ValueError('unsupported stale policy')
        self.adapter, self.zone, self.interval, self.tau = adapter, zone, 1/hz, smoothing
        self.cap, self.stale_after, self.policy = channel_cap, stale_seconds, stale_policy
        self.target = self.current = None
        self.received = self.previous = self.sent_at = None
        self.last_sent = None
        self.stale = False
        self.closed = False

    def submit(self, frame: Frame, now: float):
        rgb = frame.sample(self.zone)
        # Preserve hue while bounding the largest channel.
        gain = min(1.0, self.cap / max(1, max(rgb)))
        self.target = tuple(c * gain for c in rgb)
        self.received, self.stale = now, False

    def tick(self, now: float):
        if self.closed or self.received is None:
            return False
        if self.previous is not None and now < self.previous:
            raise ValueError('clock must be monotonic')
        elapsed = max(0, now - (self.previous if self.previous is not None else now))
        self.previous = now
        if now - self.received >= self.stale_after:
            if not self.stale:
                self.stale = True
                if self.policy == 'off':
                    self.adapter.off()
                    self.sent_at, self.last_sent = now, None
            return False
        if self.current is None:
            # Ramp up from darkness, avoiding an initial full-color flash.
            self.current = (0.0, 0.0, 0.0)
        alpha = 1 - math.exp(-min(elapsed, 0.25) / self.tau)
        self.current = tuple(a + (b-a)*alpha for a, b in zip(self.current, self.target))
        out = tuple(round(c) for c in self.current)
        if self.sent_at is not None and now - self.sent_at < self.interval - 1e-8:
            return False
        if self.last_sent is not None and max(abs(a-b) for a,b in zip(out, self.last_sent)) < 2:
            return False
        self.adapter.color(out)
        self.sent_at, self.last_sent = now, out
        return True

    def close(self):
        if not self.closed:
            self.closed = True
            try:
                if self.received is not None and self.policy == 'off' and not self.stale:
                    self.adapter.off()
            finally:
                self.adapter.close()
