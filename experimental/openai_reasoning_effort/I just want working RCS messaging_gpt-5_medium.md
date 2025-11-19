---
last_updated: 2025-11-19 21:30, cc55a25
---
# I just want working RCS messaging

**URL:** https://wt.gd/i-just-want-my-rcs-messaging-to-work

**Model:** gpt-5

**Reasoning Effort:** medium

**Time:** 261.54s

---

Bottom line: RCS on my iPhone 15 Pro has been dead for a month on multiple carriers; it activates instantly on other iPhones. Apple keeps blaming “the carrier,” but the logs point to a Google Jibe provisioning block that iOS isn’t surfacing. I want Apple to own the issue, inspect the logs, and fix it—not swap hardware and punt.

# TL;DR

- Problem: RCS stuck on “Waiting for activation…” on an iPhone 15 Pro after upgrading from iOS 18 to iOS 26. Works immediately when the same eSIMs are moved to other iPhones (two 14 Pro Maxes, an SE3). Affects T‑Mobile, US Mobile (AT&T), and Verizon lines—so not carrier-specific.
- Background: I’m OS-agnostic, run my own LineageOS builds, previously helped fix Verizon MMS UAProf breakage ([context](http://uaprof.vtext.com/sam/i515/i515.xml) dead; Apple/BlackBerry hosted their own: [Apple](https://www.apple.com/mms/uaprof.rdf), [BlackBerry](https://www.blackberry.com/go/mobile/profiles/uaprof/9700/5.0.0.rdf)). This isn’t my first interoperability rodeo.
- Google precedent: Google deliberately blocked RCS on rooted/custom ROMs in 2023—first silently, later with a notice ([report](https://www.androidauthority.com/google-silently-blocking-rcs-rooted-android-phones-custom-roms-3421652/)). I could bypass via Pixel fingerprint spoofing. So “spam prevention” rings hollow if simple workarounds exist.
- Apple’s RCS: Apple finally shipped baseline RCS (v2.4) in iOS 18; E2E may land later. My RCS worked on iOS 18; broke only after iOS 26—no config changes beyond the upgrade.
- Evidence: Device logs show Jibe-related provisioning roadblock with “Infinite validity of UserInteractionRequired.xml,” IMS “not ready,” entitlement “Allowed,” token-based provisioning selected—iOS never prompts me. Looks like an unhandled Jibe “user interaction” gate blocking activation.
- Likely root cause: US carriers offloaded RCS to Google Jibe ([docs](https://docs.jibemobile.com/)). Apple support isn’t trained on Jibe, so they default to blaming “the carrier,” masking the real dependency chain (Apple iOS RCS client ↔ carrier provisioning ↔ Google Jibe).
- Repro isolation: Same lines/eSIMs immediately activate on other iPhones; my 15 Pro fails across three carriers. Strongly points to a device/OS/Jibe provisioning edge case, not carrier accounts or network.
- Exhaustive troubleshooting already done: Network resets, toggles (RCS/iMessage/5G/airplane), VPN/DNS removal, eSIM re-issues, E911/Wi‑Fi calling, SIM-to-other-IMEI, multiple full wipes and restores (iTunes/iCloud, betas), new-device setup, days-long cool-off, inbound upgrade triggers, live syslogs via libimobiledevice. No dice.
- Apple support posture: No accountability, refuses in-store eSIM transfer-to-like device for isolation “for privacy.” Now proposing a board swap (new IMEIs). That’s a time sink and doesn’t address the underlying software/Jibe provisioning issue.
- What I want: Apple to pull a proper radar, read the logs, engage with Jibe if needed, and fix the provisioning/interaction flow. Don’t make users eat time and money because RCS is now a three-party system.

> “Do not take accountability, blame the carrier.”