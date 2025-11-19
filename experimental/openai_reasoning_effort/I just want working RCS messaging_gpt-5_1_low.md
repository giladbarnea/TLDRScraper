# I just want working RCS messaging

**URL:** https://wt.gd/i-just-want-my-rcs-messaging-to-work

**Model:** gpt-5.1

**Reasoning Effort:** low

**Time:** 297.45s

---

**Bottom line: RCS on the author’s iPhone 15 Pro has been broken for over a month; Apple blames carriers, carriers blame Apple/Google Jibe, nobody takes ownership, and Apple support is procedurally incapable of actually debugging it.**

---

# RCS Is Broken, Everyone’s Finger-Pointing

- **Symptom:** On an iPhone 15 Pro, RCS is stuck on **“Waiting for activation…”** for over a month across **three major US carriers** (T-Mobile, AT&T via US Mobile, Verizon).
- Same eSIMs **activate instantly** on other iPhones (two 14 Pro Maxes, one SE3).  
- **Conclusion:** Not a line/carrier issue; something **device-specific** (or device-class-specific) tied to RCS provisioning and Google Jibe.

> “In short, it’s probably Apple or Google and there’s zero accountability from Apple.”

---

# Author’s Cred & Past Carrier Interop War Stories

- Long-time **multi-OS power user** (Android + iOS, ex‑BlackBerry, Harmattan, would still run Windows Phone).
- Builds own **LineageOS**; previously helped fix a **Verizon MMS** bug caused by Verizon killing their UAProf domain, breaking MMS on non‑iPhone devices.  
  - Context: Verizon required UAProf; they nuked `vtext.com` UAProf hosting; Apple/BlackBerry weren’t affected because they self-host.  
  - Example UAProfs: [Apple](https://www.apple.com/mms/uaprof.rdf), [BlackBerry](https://www.blackberry.com/go/mobile/profiles/uaprof/9700/5.0.0.rdf).
- Point: **This is not my first rodeo** with carrier/vendor messaging failures.

---

# Google’s Track Record: Intentionally Breaking RCS

- Late 2023: Google **silently blocked RCS** on rooted/custom Android ROMs; RCS pretended to work but didn’t.  
  - They later admitted it: [Android Authority](https://www.androidauthority.com/google-silently-blocking-rcs-rooted-android-phones-custom-roms-3421652/).
- Author bypassed it by **spoofing Pixel fingerprints**, proving that:
  - Blocking was **not about spam**—spammers can spoof too.
  - It mainly punishes users who want device control.

---

# Apple’s RCS Rollout and the Failure on iOS 26

- Apple finally shipped **baseline RCS (v2.4)** in iOS 18; no E2E yet (maybe years out).
- **RCS worked fine on this phone on iOS 18**, broke only after upgrading to **iOS 26**.
- Configuration:  
  - Dual‑SIM: **T-Mobile + US Mobile (AT&T)**.  
  - Mildly unusual: **Mullvad DNS** adblock, but family uses same with no issues.

---

# Exhaustive Local Troubleshooting, No Fix

- Author has done **basically everything**:
  - Reboots, Airplane Mode, RCS toggles.
  - Network resets; “Reset All”; full device erase; **recovery restore as new**.
  - iTunes + iCloud restores (even paid iCloud trial just to test).
  - Removed VPNs/DNS profiles (Mullvad, Orbot, WireGuard).
  - Reissued eSIMs, moved them between IMEIs.
  - Toggled iMessage, 5G, Wi‑Fi Calling, updated e911 info.
  - Tried iOS **beta** builds.
  - Transferred same eSIMs to other iPhones: RCS activates instantly.
  - Used **libimobiledevice** on Gentoo to pull CommCenter logs.

- Logs show RCS/IMS provisioning blocked by a **“UserInteractionRequired.xml”** file from **Google Jibe** config:

> `Provisioning not possible`  
> `Infinite validity of UserInteractionRequired.xml xml`  
> `[config.rcs.mnc260.mcc310.jibecloud.net] Declaring IMS not ready. Unexpired : UserInteractionRequired.xml`

- Hypothesis: Jibe has flagged this device state as needing some user interaction that **iOS never surfaces**, so provisioning is permanently blocked.

---

# Structural Problem: Apple Support Process Is Broken for This

- Apple frontline guidance boils down to:  
  > **“Do not take accountability, blame the carrier.”**
- In-store support:
  - Repeatedly blames “software” even after **multiple complete reloads**.
  - Refuses to **test the user’s eSIM on an in-store 15 Pro** “for privacy reasons”, blocking proper A/B testing.
  - No one mentions **Google Jibe** even once; employees seem **unaware** US RCS is actually hosted by Google, not the carriers.
- Author has **no channel to Google Jibe**: docs are carrier-only ([docs.jibemobile.com](https://docs.jibemobile.com/)). Walking into a store saying “I think this is a Jibe failure” is practically absurd.

---

# Apple’s “Solution”: Swap the Board, Shrug, Move On

- Since the user **won’t accept “go bug T‑Mobile/US Mobile”**, Apple will:
  - **Replace the logic board**, changing IMEIs—hoping Jibe provisioning resets.
  - Frame it as a **“courtesy”**, insist they don’t believe it’s their issue.
- Critique:
  - Costs the user **time, fuel**, and doesn’t address the underlying bug.
  - No one is actually **analyzing logs**, so the bug could recur or affect others.
  - Author bought **AppleCare+** expecting real troubleshooting, not parts roulette.

---

# What the Author Actually Wants

- Not a new board; a **real root-cause fix** and visibility:
  - Proper internal bug (Radar) filed with log analysis.
  - Clarity on where RCS provisioning failed:  
    - Dual‑SIM? Rapid carrier switching? Jibe token state?  
    - Change from iOS 18 → 26 with same config?
- Broader complaint:  
  - **Closed systems** (Apple, Google/Jibe) plus **opaque support scripts** leave technically capable users unable to **fix or even understand** failures that they used to debug themselves on open platforms.

> “I use opensource software not because it’s inherently better, but rather because I can at least triage, understand, and fix problems.”