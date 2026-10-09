# Netgear Orbi: fixing the "wan lan conflict" (stuck panel, magenta satellites, slow mesh)

**English** · [Italiano](README.it.md) · [Español](README.es.md)

A field guide for Netgear Orbi routers (tested on **RBR760 / RBK760, firmware V6.3.8.13_1.4.84**) placed behind an ISP modem that uses the same subnet as the Orbi. The same firmware family is used by other Orbi models, so this likely applies to them too.

## Symptoms

You probably have this problem if several of these are true:

- The Orbi web panel (`orbilogin.com` / `http://10.0.0.1`) shows a blank page, a 404, or a page that says *"Important Update … IP address was updated to 10.0.0.1"* without a working **CONTINUE** button.
- The Orbi LAN suddenly moved from `192.168.1.x` to `10.0.0.x`.
- Every API call of the panel returns `{"code":8,"msg":"wan lan conflict"}` (visible in the browser dev tools, Network tab).
- Satellites show a **magenta** LED, or the panel lists them as plain "wired devices" with *Number of satellites: 0*.
- The 5 GHz radio shows **"Channel 0"**, *5G WLAN: Link down*, and all clients sit on 2.4 GHz.
- Backhaul speed in *Advanced → Show Statistics* is about **573 Mbps** (2.4 GHz) instead of **~2400 Mbps** (5 GHz). Rooms served by a satellite get ~90 Mbps instead of several hundred.
- The problem **comes back after every reboot** of the Orbi.

## Cause

The ISP modem and the Orbi both use `192.168.1.0/24` (very common: TIM Hub / Technicolor in Italy and many others use `192.168.1.1`). The Orbi's WAN gets a `192.168.1.x` address from the modem, which overlaps with its own LAN.

The firmware detects the overlap ("wan lan conflict") and:

1. moves its LAN to `10.0.0.1` as an emergency measure;
2. redirects the web panel to the `/conflict` page, so you can confirm with **CONTINUE**;
3. blocks the API (`code 8`) until you confirm.

**The bug:** the router's web server does not serve `/conflict` (HTTP 404), so the confirmation page never loads and the panel is unusable. Because the old LAN setting is still stored, the conflict comes back at every reboot. While the router is in this state the mesh runs degraded (5 GHz radio down, satellites not synced, backhaul on 2.4 GHz).

## Quick fix

You need two things: (A) get past the broken `/conflict` page once, and (B) remove the subnet overlap so it never comes back.

### A. Unlock the panel

Pick one of these:

**Option 1, Playwright script (tested).** Needs Node.js.

```bash
cd tools
npm install playwright
npx playwright install chromium
node unlock-conflict.mjs            # or: node unlock-conflict.mjs http://<orbi-ip>
```

A browser window opens. Log in with your Orbi admin password; the script presses CONTINUE for you and prints the router's reply (expect `{"code":0,...}`). Keep the window open and continue with part B.

**Option 2, caching proxy.** Needs Python 3, no extra packages.

```bash
python tools/orbi_proxy.py          # ORBI_HOST=<orbi-ip> if not 10.0.0.1
```

Open `http://127.0.0.1:8088/index.html`, log in, and press CONTINUE. The proxy answers `/conflict` with `index.html`, so the confirmation page can load. It also caches the 5-6 MB JavaScript bundle, which makes the panel usable even over a weak Wi-Fi link (see [Tips](#tips)). The panel unlocking part of this option was not tested while the router was in the conflict state; if it does not work, use option 1.

Notes:

- Use `http://10.0.0.1` rather than `orbilogin.com`: browsers with secure DNS (DoH) enabled often fail to resolve `orbilogin.com`. `https://` shows a certificate error.
- Calling `/dniapi/conflict` by hand (curl, fetch) does not work: the API requires a token and a request signature computed by the panel's JavaScript.

### B. Remove the subnet overlap

Do at least one of these, in this order of preference:

1. **Change the ISP modem's LAN** to another subnet, e.g. `192.168.10.1/24` (DHCP `192.168.10.2-254`). Some modems refuse certain ranges; for example the TIM Hub rejects `192.168.2.x` with *"Gateway IP should not be in sfp IP Range"*, while `192.168.10.x` is accepted. Update any DHCP reservation and DMZ / port-forward entry that points to the Orbi.
2. **Make the Orbi's LAN permanent:** *Advanced → Setup → LAN Setup*, keep or set a subnet different from the modem (e.g. `10.0.0.1/24`) and press **APPLY**. The router reboots and the setting is now saved, instead of being only the emergency fallback.
3. Alternatively, if you do not need the Orbi's routing features, put the Orbi in **AP mode** (*Advanced → Advanced Setup → Router / AP Mode*), so it has no LAN subnet of its own.

### C. Refresh the Orbi's WAN address

After changing the modem's subnet, the Orbi keeps its old WAN lease (`192.168.1.x`) for hours, even across reboots, and Internet stops working. Fix it with:

*Advanced → Home → **Connection Status*** (opens a new tab) → **Release** → **Renew**.

The WAN should now show an address in the new subnet (e.g. `192.168.10.x`) with the modem as gateway and DNS.

### D. Reboot once, then wait

Reboot the Orbi router once (*Advanced → Home → Reboot*, or from the Orbi app). Then check *Advanced → Home → Show Statistics* and *Attached Devices*:

- 5G WLAN should show ~2400M and a real channel (e.g. *36+40+…+64, up to 2401 Mbps*), not *Channel 0*.
- The satellites should appear under **Connected Satellites**, not as wired clients.
- **Be patient:** for the first ~15 minutes after the reboot the satellites may stay on the 2.4 GHz backhaul (573M). They moved to 5 GHz (2401M) on their own after that in our case.

Saving the wireless settings without changes, or changing the 5 GHz channel, did **not** bring the 5 GHz radio back; only a reboot after removing the conflict did.

## Results (one real case)

| | Before | After |
|---|---|---|
| Orbi panel | stuck on `/conflict` 404 | works |
| 5 GHz radio | Channel 0, link down | 36-64, 2401 Mbps |
| Satellites | magenta / "wired devices", 0 synced | 2 connected, backhaul "good" |
| Backhaul | 573 Mbps (2.4 GHz) | 2401 Mbps (5 GHz) |
| Download in a satellite room (wired) | ~90 Mbps | ~200-300 Mbps (foreign test servers) |

## Tips

- **Satellite still magenta?** Do not keep forcing *Add Orbi Satellite* over and over: repeated syncs reshuffle the mesh and make everything worse. Press the **Sync** button on the satellite first, then *SYNC* in the panel within 2 minutes, ideally with the satellite near the router.
- **Panel never finishes loading on Wi-Fi?** The panel's JavaScript bundle is 5-6 MB and fails on lossy links. `tools/orbi_proxy.py` caches it after the first load, then the panel opens in 1-3 s. You can run one proxy per device, e.g. `ORBI_HOST=10.0.0.11 PROXY_PORT=8089` for a satellite.
- **DFS channels.** With 160 MHz, the 5 GHz fronthaul uses channels 52-64 (DFS); radar detection can cause sudden channel changes and drops. If you see random disconnects, try 80 MHz on a fixed channel (36 or 44).
- **Windows client stuck at 11 Mbps on 2.4 GHz?** Check the Wi-Fi adapter's advanced property *"2.4G Wireless Mode"*: a value of `IEEE 802.11b` forces legacy rates. It should be `IEEE 802.11b/g/n/ax`.
- **Speed tests:** use a server in your own country; distant servers cap the result well below a gigabit line.

## Repository contents

| File | Purpose |
|---|---|
| `tools/unlock-conflict.mjs` | Playwright script that bypasses the broken `/conflict` page and presses CONTINUE |
| `tools/orbi_proxy.py` | Local caching proxy for the Orbi panel (Python 3 standard library only) |

## Disclaimer

Not affiliated with Netgear. Changing router settings can interrupt your connection; make sure you can reach the ISP modem with a cable before changing its LAN, and write down the old values. Use at your own risk.

## License

[MIT](LICENSE) © lambdagw
