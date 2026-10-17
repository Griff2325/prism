# Govee LAN protocol notes

Implementation source: Govee's official [LAN API guide](https://app-h5.govee.com/user-manual/wlan-guide), checked 2026-10-17. The page is client-rendered; its current published command examples were inspected directly. The guide's model search is served by its own public device-info endpoint. H6008 returned a supported RGBWW bulb entry; H600B returned an empty list. Absence from the current list is not proof that every firmware revision lacks the feature.

One scan request goes to multicast `239.255.255.250:4001`, with replies on local UDP port 4002:

```json
{"msg":{"cmd":"scan","data":{"account_topic":"reserve"}}}
```

Control goes to the selected device on UDP 4003. The RGB command uses `colorwc`, an RGB `color` object, and `colorTemInKelvin: 0` to choose RGB rather than a white-temperature value. Optional off uses `turn` with `value: 0`. No undocumented BLE, MQTT, scene or RGBIC segment packet is used.

The [cloud supported-model page](https://developer.govee.com/docs/support-product-model) includes H6008 and is distinct from the LAN list. Cloud account inventory could report capabilities of an actual selected device if a future adapter is added; it is not necessary for this LAN harness and no credentials are requested.
