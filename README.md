# wifiwalk

[![CI](https://github.com/Tjabooo/wifiwalk/actions/workflows/ci.yml/badge.svg)](https://github.com/Tjabooo/wifiwalk/actions/workflows/ci.yml) [![Release](https://img.shields.io/github/v/release/Tjabooo/wifiwalk?include_prereleases&sort=semver)](https://github.com/Tjabooo/wifiwalk/releases) [![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Walk your home with a Linux laptop, measure Wi-Fi in every room, and compare router positions until the worst room is good enough.

A no-dependency Python script built on `iw` and `ping`. It answers three questions:

- **How good is the signal in each room?** `walk` measures each spot you stand in.
- **What actually happens when it "keeps disconnecting"?** `watch` logs dropouts, band switches and lost pings at one spot, overnight if you like.
- **What do the other devices see?** `router` reads every wireless client's signal from an ASUS router (phones, TVs) and logs when they drop.

## Features

- Per spot: median/min signal, noise floor and SNR, link rate, channel width, Wi-Fi retry rate, beacon loss, ping loss and p95 latency to the router
- How strongly each of the router's bands (2.4 / 5 / 6 GHz) reaches that spot, from a fresh scan
- Same-channel neighbour networks (congestion)
- Plain verdicts: great / good / fair / weak / bad
- Compare surveys side by side, one per router position, ranked by the weakest room
- Dropout log with disconnects, band/BSSID switches and ping outages
- ASUSWRT client poller (app API): RSSI per device over time, joins, drops and band changes
- Everything is saved as JSON lines in `~/.local/state/wifiwalk/`

## Install

Requirements: Linux, Python 3.11+, `iw`, `ping` (iputils). `nmcli` is optional; it triggers a fresh scan.

```sh
git clone https://github.com/Tjabooo/wifiwalk
install -Dm755 wifiwalk/wifiwalk ~/.local/bin/wifiwalk
```

## Usage

### 1. Survey the current setup

```sh
wifiwalk walk --name router-hall
spot> kitchen
  kitchen              -52 dBm  great  on 5 GHz    1201 Mb/s  loss 0%  p95 3 ms   [router: 2.4G -41  5G -52]
spot> parents bedroom
  parents bedroom      -76 dBm  weak   on 5 GHz      86 Mb/s  loss 4%  p95 61 ms  [router: 2.4G -63  5G -76]
spot>            (empty line finishes and prints the report)
```

Each spot takes 15 s (`--seconds`). Stand where the devices are actually used: the bed, the desk, the sofa.

### 2. Find out what the drops are

```sh
wifiwalk watch            # leave the laptop in the problem room; Ctrl-C prints the summary
wifiwalk router           # or from any machine: poll the router's view of every wireless device
wifiwalk router --once    # current table, weakest device first
```

### 3. Move the router and compare

Survey again after each move, using the **same spot names**:

```sh
wifiwalk walk --name router-living-shelf
wifiwalk report ~/.local/state/wifiwalk/router-hall-*.jsonl ~/.local/state/wifiwalk/router-living-shelf-*.jsonl
```

```
  spot                 router-hall  router-living-s
  kitchen                -52 great        -58 great
  parents bedroom         -76 weak         -66 good
  Best placement: router-living-s (weakest spot -66 dBm, median -60 dBm).
```

### Reading the numbers

| Signal | Verdict | In practice |
| --- | --- | --- |
| ≥ −60 dBm | great | anything works |
| −60 … −67 | good | video calls and streaming are fine |
| −67 … −72 | fair | browsing ok, calls may stutter |
| −72 … −78 | weak | slow, drops likely |
| < −78 | bad | expect disconnects |

A good link also needs SNR above ~25 dB, ping loss under 1 % and a retry rate under ~10 %.

## Configuration

Only `router` needs configuration. Copy `config.example.toml` to `~/.config/wifiwalk/config.toml`, put the admin password in the file it points to (`chmod 600`), or set `WIFIWALK_ROUTER_PASSWORD`. Without a URL it uses `http://<default gateway>`.

ASUS routers turn on a login captcha after failed logins; log in once in the browser to clear it.

## How it works

- `iw dev IF link` once a second for signal, link rate and band; `iw station dump` before and after for retry, packet and beacon-loss deltas; `iw survey dump` for the noise floor
- `ping -i 0.2` to the gateway in parallel with the sampling
- `nmcli device wifi rescan`, then `iw scan dump` (no root needed) for the router's per-band signal and neighbouring networks
- `router` logs in to ASUSWRT's `login.cgi` the way the ASUS app does and polls `appGet.cgi?hook=get_clientlist()`

## License

MIT
