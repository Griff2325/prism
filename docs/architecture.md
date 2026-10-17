# Architecture and input contract

```text
local producer → bounded JSON-lines reader → latest Frame → per-light zone sampler
                                                     → smoothing and rate cap
                                                     → LightAdapter (Govee UDP)
```

The producer owns obtaining legitimate content samples. The harness owns sampling, bounded timing and device output. `core.py` contains transport-independent frame validation, linear-light averaging, capabilities and the engine. `sources.py` includes a nonblocking pipe reader and synthetic scene. `govee.py` implements only documented LAN discovery, global RGB and opt-in off commands. `cli.py` handles explicit device selection and process lifetime.

## Input

Each UTF-8 line is one complete object:

```json
{"version":1,"width":3,"height":1,"pixels":[[150,80,20],[40,100,130],[70,40,140]]}
```

Pixels are row-major RGB integers from 0 to 255. In this example, each pixel can already be a producer-computed screen-zone average; sending a full screenshot is unnecessary. A producer can also send a small thumbnail from an authorized unprotected source. Width and height are each 1–128, their product at most 4096, and a serialized line at most 64 KiB. Include a newline; partial lines do not update lighting. Unknown fields are ignored, but schema version, dimensions and pixels are validated. No timestamps from another clock are trusted.

The reader retains the newest complete valid frame found in each bounded read and discards older frames in that read. It reads at most 64 KiB per 20 ms policy tick; therefore a producer **must also remain bounded** (recommended 5–10 small frames/second). An oversized or malformed line is rejected and does not refresh the watchdog. Stdin EOF exits after the stale timeout; empty EOF exits immediately. No input files or RGB history are stored.

Each engine averages its configured region in linear-light space, preserves hue while capping its largest channel, and exponentially approaches the newest target using monotonic elapsed time. Output is independently capped at 0.2–10 Hz, with a two-level RGB change threshold. The 50 Hz policy tick does not mean 50 Hz network traffic. Default output is 5 Hz. A small tick-time cap prevents a long process stall from causing an immediate large jump.

Configuration selects at most eight unique private IPv4 targets. Discovery validates that a response's advertised address matches its packet sender, accepts at most 64 identities and bounds packets to 8192 bytes. This does not authenticate a Govee device; the documented UDP protocol has no authentication. Deploy on a trusted home LAN. Discovery emits one multicast request with TTL 1 and listens for at most ten seconds. Port 4002 must be available; the harness uses an exclusive listener rather than silently competing with another client.

## Extending it

A new adapter implements `capabilities`, `color(rgb)`, `off()` when advertised, and `close()`. The current engine requires RGB, uses one color per adapter, and deliberately does not promise segment-addressable output. A new source implements `poll()` and `close()`. It must never block a policy tick and must signal input loss by producing no frames. More advanced adapters should explicitly advertise acknowledgments or zones and have corresponding engine policy rather than silently claiming support.

For eventual TV integration, sample Vista's own Canvas or render-state colors at a low cadence only while visible; that is a launcher ambience source, not a streaming-app movie source. A TV-native Govee UDP adapter could avoid a separate host. If a network bridge is later needed, use explicit pairing, authenticated/replay-resistant input, bounds and a watchdog. Do not weaken a launcher's global HTTPS policy or expose this local pipe as an unauthenticated HTTP endpoint.
