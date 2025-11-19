---
last_updated: 2025-11-19 21:30, cc55a25
---
# I just want working RCS messaging

**URL:** https://wt.gd/i-just-want-my-rcs-messaging-to-work

**Model:** gpt-5

**Reasoning Effort:** low

**Time:** 195.01s

---

Bottom line: RCS on my iPhone 15 Pro has been dead for a month; Apple blames carriers, carriers shrug, but my lines instantly activate on other iPhones. Logs point to a Google Jibe provisioning hang Apple won’t acknowledge. I want Apple to own and fix it—instead they’re swapping my logic board “as a courtesy.”

# TL;DR: RCS On iPhone Is Broken And Nobody Owns It
- Problem: On iOS 26, both my dual-SIM lines (T-Mobile, US Mobile/AT&T; even tested Verizon) are stuck on “Waiting for activation.” The same eSIMs activate within seconds on multiple other iPhones (14 Pro Max, SE3). This is device-specific, not carrier-specific.
- Evidence: Live CommCenter logs flag Jibe config as not ready due to an unexpired “UserInteractionRequired.xml” with “Infinite validity,” blocking provisioning. IMS flips to kCellular; entitlement shows “Allowed” and “kSupported.” The phone never surfaces a needed user action.
- Apple support: Underinformed and not empowered. Triage script is to deflect to carriers. Refuse in-store eSIM swaps to identical test hardware “for privacy,” so they can’t reproduce. Final move: logic board swap with new IMEIs, framed as a favor, not a diagnosis.
> “Do not take accountability, blame the carrier.”
- My creds: OS-agnostic power user; maintain my own LineageOS builds. Previously helped surface and fix Verizon MMS UAProf breakage ([change review](https://review.lineageos.org/c/LineageOS/android_device_oneplus_sm8250-common/%2B/333379)); understand carrier interop failures and how they manifest.
- Context: Apple added baseline RCS (v2.4) in iOS 18; E2E promised “later.” Carriers in the US largely handed RCS to Google’s Jibe ([docs](https://docs.jibemobile.com/) are gated). Apple support never mentions Jibe, but my logs do. Customers can’t contact Jibe.
- Google angle: Google deliberately blocked RCS on rooted/custom ROMs, admitted later ([Android Authority](https://www.androidauthority.com/google-silently-blocking-rcs-rooted-android-phones-custom-roms-3421652/)), while touting 911 over RCS ([blog](https://blog.google/products/messages/google-messages-rcs-911-emergency/)). I bypassed with Pixel fingerprint spoofing—so “anti-spam” rationale rings hollow.
- Exhaustive troubleshooting already done: every flavor of resets, toggles, eSIM reissues, IMEI swap between slots, Wi‑Fi Calling, 5G off, iOS betas, full device recoveries (iTunes/iCloud/new), VPN/DNS removed, waited days before reattempting, cross-device activation tests, and deep log captures via libimobiledevice.
- Likely root cause: Apple-Jibe tokenized RCS provisioning path stuck behind a never-cleared “user interaction required” state the UI never exposes—possibly triggered by dual-SIM behavior, data-carrier hopping, or policy gating in Jibe’s per-carrier config.
- What I want: Accountability and proper debugging. Let engineering pull device logs and file a Radar; confirm where provisioning fails (token, entitlement, IMS gating, Jibe policy). If it’s Jibe, escalate through carrier channels rather than pushing me back to retail scripts.
- What Apple’s doing instead: Board swap tomorrow. Might work because of fresh IMEIs, but it’s punting—not root-causing. If it’s a generational/software+Jibe issue, I could hit it again, and others will too.
- Bottom ask: I didn’t change my setup from iOS 18 to 26; Apple stopped signing 18 so I can’t revert. I just want working RCS messaging—own the failure path and fix it.