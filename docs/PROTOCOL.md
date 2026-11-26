# DotGlow Bluetooth protocol — version 1

How the DotGlow Android app talks to the clock over Bluetooth Low Energy. The same operations are
available over HTTP for the web page (`/api/<op>`); both call `apiCall()` in `src/api.cpp`.

## GATT service

| | UUID | Properties | Security |
|---|---|---|---|
| Service | `6f4a0001-1d2c-4a8e-9c3d-2b7e5f9a1c00` | (advertised) | |
| INFO | `6f4a0002-1d2c-4a8e-9c3d-2b7e5f9a1c00` | read | open |
| RX (requests) | `6f4a0003-1d2c-4a8e-9c3d-2b7e5f9a1c00` | write, write without response | encrypted + authenticated |
| TX (responses) | `6f4a0004-1d2c-4a8e-9c3d-2b7e5f9a1c00` | notify | encrypted + authenticated |

The clock advertises the service UUID and its name, `DotGlow-XXXX` (last 2 bytes of the MAC).
**INFO** returns `{"name":"DotGlow-EEA8","fw":"0.1.0","board":"ESP32-S3","proto":1}`, so the app can
identify a clock before pairing.

## Pairing

LE Secure Connections with bonding and MITM protection. The clock is *display-only*: when a phone
pairs, the clock makes up a 6-digit PIN and shows it **on the LED display** for 60 s, and the user
types it into the phone's pairing dialog. Only bonded phones can write requests or receive responses,
so a paired phone is treated as the owner (`trusted`). `phones/forget` removes all bonds.

## Messages

Requests and responses are single-line JSON objects terminated by `\n`. A line may be longer than
one BLE packet: senders split it into chunks of at most `MTU - 3` bytes and receivers join the
chunks until the `\n`. The app requests an MTU of 517.

```json
→ {"id":7,"op":"set","args":{"k":"br","v":"5"}}
← {"id":7,"code":200,"body":"OK"}
```

- `id`: chosen by the app and echoed in the response.
- `args`: string values only.
- `code`: HTTP-style (200 ok, 400 bad request, 401 not allowed, 403 wrong password, 404 unknown op).
- `body`: a JSON value for data (`status`, `config`, `scan`, `info`), otherwise a text string.

Requests are handled one at a time in the clock's main loop. Slow operations (`scan`) can take a few seconds.

## Operations

| op | args | body / effect |
|---|---|---|
| `info` | | `{"name","fw","board","proto"}` |
| `status` | | time, date, `synced`, `ssid`, `ip`, `rssi`, `up`, `version`, `board`, `mode` (`clock` / `setup` / `safe`), `latest`, `newer`, `otaMsg`, `light`, `brNow` |
| `config` | | every setting (same keys as `set`) plus `events[]`, `hasPassword`, `msg`, `msgEvery` |
| `set` | `k`, `v`, `live`? | change one setting; `live` = don't save to flash yet (slider dragging). `modules`/`hwType` restart the clock |
| `scan` | | `[{"s":ssid,"r":rssi,"l":locked}]` |
| `wifi` | `ssid`, `pass` | save the network and restart |
| `message` | `t`, `every`, `show`? | custom message; `every` ∈ 0,1,5,15,30,60 |
| `event/add` | `m`, `d`, `a`, `t` | add a special day |
| `event/del` | `i` | delete a special day |
| `event/show` | `i` | play a special day now |
| `password` | `cur`, `new` | set / change / remove (`new` empty) the settings-page password |
| `anim` | `n` | play an effect: 1 sparkle, 2 wipe, 3 rain, 4 boxes, 5 pac-man, 6 random |
| `digits` | | preview the digit-change animation |
| `modules` | | show each module's number |
| `show` | | scroll the IP address |
| `sync` | | re-sync the time |
| `alarm/set` | `i`?, `h`, `m`, `d`, `s`, `on`? | add (no `i` or `-1`) or change an alarm; see *Alarms, timer and sounds* |
| `alarm/del` | `i` | delete an alarm |
| `alarm` | `a`: `stop` / `snooze` | answer a ringing alarm -> `{"ring","i","h","m","snooze"}` |
| `timer` | `a`, `s`? | countdown -> `{"on","run","ring","ms","total"}` |
| `sound` | `a`: `play` / `stop`, `n` or `sw` | preview a sound on the clock's speaker |
| `ota/check`, `ota/install` | | look for / install a GitHub release |
| `restart`, `factory` | | restart / reset all settings (also forgets paired phones) |
| `phones/forget` | | remove all paired phones (disconnects) |

**Setting keys for `set`:** `br`, `autoDim`, `nightFrom`, `nightTo`, `nightBr`, `fmt24`, `leadingZero`,
`blinkColon`, `secondsBar`, `showDate`, `autoUpdate`, `roll`, `hourlyAnim`, `bootAnim`, `tz`, `ldrOn`,
`ldrMin`, `ldrMax`, `ldrInvert`, `modules`, `hwType`, `flipH`, `flipV`, `showSecs`, and from firmware 0.4.0
`vol` (0-10), `tmrSound`, `swSound`, `snooze` (1-30 minutes).

## Alarms, timer and sounds (firmware 0.4.0+)

`config` also reports `"sounds"` (names, the index is the sound number), `"swSounds"` (stopwatch styles, index 0 =
off), `"maxAlarms"` and `"alarms"`. **An app shows these features only when `sounds` is present**, and builds its
lists from the names, so new sounds need no app update.

An alarm is `{"i","h","m","d","s","on"}`: slot, hour, minute, days (bit 0 = Monday ... bit 6 = Sunday, `0` = ring
once, after which it switches itself off), sound, enabled. A ringing alarm gets louder over 20 s and stops by itself
after 3 minutes. `snooze` rings again after `snooze` minutes.

`status` carries `"alarm": {"ring","i","h","m","snooze"}` (`i` = -1 when nothing rings or is snoozed, `snooze` =
seconds until it rings again) and `"tmr": {"on","run","ring","ms","total"}` (`ms` left, `total` seconds).

`timer` actions: `set` (with `s`, 1 to 359999 seconds: show it, not started), `start`, `pause`, `toggle`, `reset`,
`open`, `exit`, `stop` (end the ringing). `s` may also come with `start`. The countdown and the stopwatch share the
display: opening one closes the other. A finished countdown rings for 60 s.

`sound` with `n` plays that alarm sound once; with `sw` it plays the start, pause and reset cues of a stopwatch
style. It answers 400 while something is ringing or when the volume is 0.

**On the clock:** while ringing, a tap on the stopwatch button or BOOT snoozes an alarm and holding it stops it;
either ends a finished countdown.

## Versioning

`proto` in INFO is bumped only for incompatible changes. New operations and new keys are additive:
the app hides features a clock doesn't report, and the clock answers unknown ops with 404.

## Firmware update over Bluetooth (firmware 0.2.0+)

INFO also carries `"asset"` (the release file this clock runs, e.g. `firmware-esp32s3.bin`) and
`"ota":1` when the clock accepts updates over Bluetooth.

| Characteristic | UUID | Properties |
|---|---|---|
| OTA | `6f4a0005-1d2c-4a8e-9c3d-2b7e5f9a1c00` | write, write without response; encrypted + authenticated |

1. `ota/begin` `{"size": <bytes>, "md5": "<32 hex>"}` -> `{"chunk": <max bytes per write>}`
2. Write the app image (`firmware-<chip>.bin`, the one that goes to 0x10000) to OTA in order,
   `chunk` bytes per write. Writes without response are about 3x faster; nothing is lost (link-layer
   flow control), and the size + MD5 check in step 3 catches anything else.
3. `ota/end` -> `"OK"`: size and MD5 checked, the clock restarts about 1.5 s later.
   Errors: `400` with a message (`Only N of M bytes arrived`, `Invalid firmware: ...`).

`ota/status` -> `{"active","written","size","error"}`; `ota/abort` cancels. A disconnect cancels too.
While an image arrives the display shows the percentage and a progress bar.

## Stopwatch (firmware 0.3.0+)

`stopwatch` `{"a": "start" | "pause" | "toggle" | "reset" | "open" | "exit"}` -> `{"on","run","ms"}`.
`status` carries the same object as `"sw"`. While `on`, the display shows the stopwatch (MM:SS, HH:MM
after an hour, HH:MM:SS on 6+ modules; tenths fill the bottom row; paused = blinking digits).

Optional button: push button from GPIO4 (ESP32-S3) / GPIO13 (ESP32) to GND, internal pull-up.
Tap = start / pause (from the clock: open the stopwatch and start). Hold 1.2 s = reset; at 0 = back
to the clock. Paused for 30 minutes = back to the clock.
