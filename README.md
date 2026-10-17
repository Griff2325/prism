# Prism

A small, reusable frame-to-light service with a documented Govee LAN adapter. It accepts low-resolution RGB samples, smooths transitions, maps screen regions to selected lights, and limits command traffic. It runs with Python 3.10+ and the standard library; no account or cloud key is needed for the LAN path.

This is a working connectivity harness, **not yet a Fire TV movie capture application**. Synthetic input and a loopback UDP light simulator are tested. Physical light control and TV integration are pending device selection. See [input and capture limits](docs/capture.md).

## Try it without changing any lights

From this directory:

```sh
python3 -m prism_lights run --duration 10
python3 examples/frame-producer.py | python3 -m prism_lights run --source stdin --duration 15
python3 -m unittest discover -s tests -v
```

The preview prints computed RGB output. It opens no light-control socket. The simulator is deliberately synthetic; it is not movie footage.

## Connect compatible Govee lights

1. In Govee Home, check the exact model and enable its **LAN Control** setting. Connect the host and light to the same reachable LAN.
2. Run one read-only discovery. Device identifiers and addresses go to ignored, owner-readable `.local/discovery.json`; the terminal shows only model numbers and selection indices.
3. Select only RGB lights you intend to control, assigning each a sampling region. Selection itself sends no light commands.
4. Use `--live` explicitly to permit visible changes.

```sh
python3 -m prism_lights discover --seconds 3
python3 -m prism_lights configure --device 1:left --device 2:right
python3 -m prism_lights run --live --source simulator --duration 10
```

Supported regions: `all`, `left`, `right`, `top`, `bottom`. Up to eight selected lights are supported; each receives one global RGB color. LAN control does not imply individual RGBIC segment control. `--interface` on discovery can choose the host's local IPv4 address on a multihomed machine. It does not scan subnets.

The defaults are five color packets per second per light, a 350 ms smoothing time, and a maximum RGB channel of 160. A channel cap is not calibrated physical brightness or a guaranteed percentage of a bulb's output. This implementation sends no brightness-setting or power-on command. Device-specific behavior still requires a physical test: some firmware may change state when receiving color commands.

On input loss, invalid frames, producer exit, or capture stop, valid frames stop refreshing the three-second watchdog. The default `hold` policy stops commands and leaves each light at its last state. It does not claim to restore earlier app scenes. `--stale-policy off` explicitly opts into a best-effort power-off on timeout and normal shutdown; subsequent color commands do not explicitly turn it back on. UDP provides no delivery acknowledgment. A hard process kill or host failure cannot send cleanup, so use `hold` when uncertain.

No lights are discovered automatically in the background. No cloud login, MQTT dependency, capture grant, root access, or raw image recording is included.

## Reuse and deployment

The core depends on small `FrameSource` and `LightAdapter` contracts, not Govee or a UI. Input is a local JSON-lines pipe; no HTTP server, LAN input listener, unauthenticated remote control endpoint, or global Android cleartext-network exception is introduced. [Architecture and input format](docs/architecture.md) describes how another app can provide only zone colors.

A laptop is useful for setup and tests. A persistent process can instead run on an existing Linux home server or Raspberry Pi with Python and LAN access. This release still **needs such a host**; there is no Android APK or autonomous TV deployment. An Android-native transport/core port is a separate integration step. The current service does not capture the TV or receive launcher frames by itself.

## Device support and validation

The [official LAN guide](https://app-h5.govee.com/user-manual/wlan-guide) is the authority for model support and setup. As checked on 2026-10-17, its model search lists H6008; H600B returned no match. Firmware and the actual LAN Control toggle still need checking. The cloud supported-model list is a different list and does not prove LAN support.

A three-second physical-network discovery during development found zero responders. No physical light commands were sent. This is compatible with LAN Control being off, unsupported hardware, or multicast filtering; it is not evidence that a light is absent. [Validation](docs/validation.md) separates unit/protocol checks from untested hardware behavior.

### Other connection routes under investigation

Govee lists [H600B as Matter-compatible](https://us.govee.com/blogs/led-light-bulbs/best-smart-bulbs). Matter is a separate connection path from Govee's LAN API; its pairing code can be found on the product or in device settings according to [Govee's setup guide](https://us.govee.com/pages/matter-faq). Pairing still needs a Matter controller. This harness does not yet include a Matter adapter or controller.

For H6008 revisions without the LAN toggle, [community Bluetooth implementations report physical H6008 control](https://github.com/hardcpp/GoveeBleMqttServer). That protocol is unofficial and compatibility with the tested installation's exact revision remains unverified. A separate bounded Bluetooth discovery observed nearby H6008 and H600B advertisements, but advertisement visibility does not prove control, ownership, multi-device capacity, latency or reliable scene synchronization. No Bluetooth command adapter is included in this release.
