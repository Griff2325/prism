# Validation

Checks performed on 2026-10-17 with Python 3.12.15 on macOS:

- Fifteen unittest cases pass: malformed/bounded frames, linear sampling and zones, hue/channel cap, smooth rate-capped output, stale hold/recovery, opt-in off exactly once, empty-input safety, backwards-clock rejection, real UDP loopback discovery/control, response-address validation, partial/overlong pipe recovery, owner-only config permissions, multiple-zone selection with duplicate rejection, and empty-pipe process shutdown.
- A loopback mock replies to the actual scan datagram and receives the exact documented `colorwc` and `turn` payloads. It is an actual socket test, not a fabricated successful physical discovery.
- Preview runs execute the engine and synthetic source without any device-control adapter.
- One three-second local multicast discovery found zero physical responders. Addresses/identities are stored only under ignored `.local/`; none are committed.

Not validated: physical light latency or firmware behavior, brightness perception, supported bulb state changes, multicast across this home's network, protected movie capture, TV deployment, launcher integration, or actual movie-to-light synchronization. No physical light commands were sent.

The service uses one tiny frame and one state per selected light, bounded input reads, no image history, and standard-library sockets. No device performance/memory figures are claimed before measurement.

Run:

```sh
python3 -m unittest discover -s tests -v
python3 -m prism_lights run --duration 1
python3 examples/frame-producer.py | python3 -m prism_lights run --source stdin --duration 15
```

Hardware validation after explicit target selection should check small changes first, output cadence, input unplug/timeout, SIGTERM, coexistence with Govee Home, and recovery. UDP delivery is best effort and restore of earlier scenes is not implemented. Default hold stops network changes when input vanishes; it is not a device-side lease.
