# Content sources and capture limits

The output harness and the video source are separate problems. Working Govee color commands do not prove movie synchronization works.

| Source | What it can actually provide | Status |
| --- | --- | --- |
| Included simulator | Synthetic changing RGB samples | Implemented and tested |
| Local JSON-lines producer | Small samples supplied by an authorized source | Implemented and tested |
| Launcher scene | Colors of the launcher's own artwork/render state | Integration proposed; not connected |
| Android MediaProjection | User-approved capture of content the platform permits | Not implemented or validated on this Fire TV |
| Protected streaming app | Secure video surfaces can be omitted or appear black | No capture path claimed |
| External HDMI sync hardware | Colors from a compatible external HDMI source routed through it | Requires supported hardware and topology |
| Supported Govee camera/DreamView hardware | Optical sampling of the visible TV image | Potential hardware path; pairing/model support must be checked |

Android's [MediaProjection documentation](https://developer.android.com/media/grow/media-projection) requires user-approved sessions and lifecycle handling. [`FLAG_SECURE`](https://developer.android.com/reference/android/view/WindowManager.LayoutParams#FLAG_SECURE) prevents secure windows appearing in screenshots or nonsecure displays. An Android permission prompt does not grant access to protected movie pixels. Fire OS feature availability also needs checking on the particular device; no privileged capture grant or DRM/HDCP bypass is part of this project.

Govee [documents this topology restriction](https://us.govee.com/blogs/tv-lighting/how-to-setup-govee-ai-sync-box-2-to-tv) and the [camera-led DreamView option](https://us.govee.com/support/faqs/can-other-govee-lights-sync-with-this-backlight). A television running its **built-in Fire TV apps** is not outputting those app frames as an external HDMI video source for a sync box. HDMI ARC/eARC carries return audio, not those video frames. An HDMI sync box would need the movie to come from a compatible external player routed through it. A camera-based product samples the physical screen and follows a different path. Neither approach is implemented by this Python harness, and existing bulb compatibility with any DreamView group must be verified in Govee Home before buying equipment.

The official [Govee cloud control API](https://developer.govee.com/reference/control-you-devices) documents device and account request limits (currently 2 control requests/second/device and 12/second/account). Network latency and rate limits make it a poor substitute for frequent local movie-color output. No cloud adapter is included; do not route high-frequency frame output through it. Older Developer API versions document different limits, so a future cloud adapter must use the limits of its exact endpoint and obey 429/backoff headers.

No scenes inferred from audio, playback metadata or a title should be described as actual frame synchronization. Such a mode could be useful as deliberately labeled ambience, but it is a different source.
