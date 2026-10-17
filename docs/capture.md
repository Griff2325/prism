# Content sources and capture limits

The output harness and the video source are separate problems. Working Govee color commands do not prove movie synchronization works.

| Source | What it can actually provide | Status |
| --- | --- | --- |
| Included simulator | Synthetic changing RGB samples | Implemented and tested |
| Local JSON-lines producer | Small samples supplied by an authorized source | Implemented and tested |
| Launcher scene | Colors of the launcher's own artwork/render state | Integration proposed; not connected |
| Android MediaProjection | User-approved capture of content the platform permits | Diagnostic probe captured Vista and a normal YouTube video on the tested Fire TV; not connected to the light engine |
| Netflix on the tested TV | Ordinary capture did not expose usable movie frames during owner-confirmed playback | Failed with this method; no bypass or universal compatibility claim |
| External HDMI sync hardware | Colors from a compatible external HDMI source routed through it | Requires supported hardware and topology |
| Supported Govee camera/DreamView hardware | Optical sampling of the visible TV image | Potential hardware path; pairing/model support must be checked |

Android's [MediaProjection documentation](https://developer.android.com/media/grow/media-projection) requires user-approved sessions and lifecycle handling. [`FLAG_SECURE`](https://developer.android.com/reference/android/view/WindowManager.LayoutParams#FLAG_SECURE) prevents secure windows appearing in screenshots or nonsecure displays. An Android permission prompt does not grant access to protected movie pixels. Fire OS feature availability also needs checking on the particular device; no privileged capture grant or DRM/HDCP bypass is part of this project.

Govee [documents this topology restriction](https://us.govee.com/blogs/tv-lighting/how-to-setup-govee-ai-sync-box-2-to-tv) and the [camera-led DreamView option](https://us.govee.com/support/faqs/can-other-govee-lights-sync-with-this-backlight). A television running its **built-in Fire TV apps** is not outputting those app frames as an external HDMI video source for a sync box. HDMI ARC/eARC carries return audio, not those video frames. An HDMI sync box would need the movie to come from a compatible external player routed through it. A camera-based product samples the physical screen and follows a different path. Neither approach is implemented by this Python harness, and existing bulb compatibility with any DreamView group must be verified in Govee Home before buying equipment.

The official [Govee cloud control API](https://developer.govee.com/reference/control-you-devices) is subject to device/account request limits. Network latency and rate limits make it a poor substitute for frequent local movie-color output. No cloud adapter is included; do not route high-frequency frame output through it. Older Developer API versions document different limits, so a future cloud adapter must use the limits of its exact endpoint and obey 429/backoff headers.

No scenes inferred from audio, playback metadata or a title should be described as actual frame synchronization. Such a mode could be useful as deliberately labeled ambience, but it is a different source.

## Android capture diagnostic

`tools/android-capture-probe/` is an isolated diagnostic app, not an Android deployment of the Prism controller. It uses the standard MediaProjection consent screen, a foreground service, a 480×270 RGBA ImageReader and ten-second samples at roughly two frames per second. It has no Internet or audio-recording permission. It saves only first/last thumbnails and central-region statistics in its private app files, and stops the screen-sharing session after five minutes. Shell commands are protected by the Android DUMP permission; an ordinary third-party app cannot trigger them. Stop the service when finished rather than relying on the timeout.

Build with JDK 17+, Android SDK platform 34 and build-tools 34.0.0 (or explicit `ANDROID_BUILD_TOOLS` / `ANDROID_JAR`), then authorize your own device:

```sh
bash tools/android-capture-probe/build.sh
adb -s YOUR_ADB_SERIAL install build/android-capture-probe/prism-capture-probe.apk
adb -s YOUR_ADB_SERIAL shell am start -n com.griffin.prismprobe/.ProbeActivity
```

Select the start button and approve the system screen-sharing prompt. Open a known moving, unprotected source first as a positive control. Then request one labeled sample:

```sh
adb -s YOUR_ADB_SERIAL shell am startservice -n com.griffin.prismprobe/.CaptureService -a SAMPLE --es label baseline
adb -s YOUR_ADB_SERIAL shell run-as com.griffin.prismprobe ls files
# After sampling: retrieve a chosen file into an ignored private directory.
mkdir -p .local/capture-results
adb -s YOUR_ADB_SERIAL exec-out run-as com.griffin.prismprobe cat files/baseline.csv > .local/capture-results/baseline.csv
adb -s YOUR_ADB_SERIAL shell am stopservice -n com.griffin.prismprobe/.CaptureService
adb -s YOUR_ADB_SERIAL uninstall com.griffin.prismprobe
```

CSV columns are device monotonic milliseconds, sample index, central mean RGB-channel value, central near-black pixel fraction, and central mean absolute RGB difference from the previous sample (`-1` for the first). Near-black means every channel is below 8; the sampled center spans the middle half of each axis. A static or excluded surface can stop producing frames, so a missing sample alone is inconclusive. Confirm that actual video is playing on the physical TV and inspect captured video frames rather than relying on menus, subtitles or playback controls. The permission Activity can interrupt a player, so establish playback again after approval without reopening the probe Activity. The Netflix follow-up used owner confirmation and an advancing active playback session during capture; an earlier sample taken before playback resumed was inconclusive. This short diagnostic establishes color availability, not maximum capture rate, sustained TV performance, bulb latency or end-to-end synchronization. Never publish captured account screens, private content or raw TV dumps.
