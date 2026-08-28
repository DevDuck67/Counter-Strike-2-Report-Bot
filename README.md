# 🎯 CS2 Report Bot [Internal Tool]

> **"The project is an automation based on a network of Steam users against abusive practices. The application makes use of internal APIs to automate mass reporting towards the target account."**

---

## 🎨 Features & Interface Architecture

- **Compact Vertical Tactical Form Factor (`500x860 px`)**:
  - **Unified Panel Headers**:
    - `TARGET SUSPECT & LICENSE`
    - `REPORT CATEGORIES`
    - `REPORT CONSOLE`
  - **Available Mass Report Tiers**:
    - `15 Reports - Standard FREE use` (Always unlocked)
    - `50 Reports - Join Telegram Channel` (Unlocked via License Key)
    - `MAX REPORTS AVAILABLE ({N}) - PREMIUM TIER KEY NEEDED` (Unlocked via License Key, dynamically allocated from botnet pool)
  - **Official CS2 Violation Categories**:
    - *Aim Hacking* (Auto-Aim / Silent Aim)
    - *Vision Hacking* (Wallhack / Radar / ESP)
    - *Other Hacking* (Spinbot / Anti-Aim / Speed)
    - *Griefing (Trust factor)*
  - **Dynamic VACnet Priority Weight Calculator**: Real-time inspection queue multiplier.
  - **Action Button**: **`[ LETS FUCKING GO ]`** (transitions immediately to locked gray state **`[ REPORTS SENT ]`** upon dispatch).
  - **CS2 Tactical Progress Bar & Syntax Terminal**:
    - Real-time Steam vanity URL & SteamID64 target resolution.
    - Distributed Node routing across EU/US regions (`FRA`, `STO`, `VIE`, `WAW`, `LDN`, `AMS`, `HEL`, `MAD`).
    - CS2 Game Coordinator handshake & simulated ticket confirmations (`Ticket #CS2-REP-... -> ACK 200 OK`).
    - Post-report forensics audit summary with estimated Trust Score impact and VACnet Case ID.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- Dependencies:

```bash
pip install -r requirements.txt
```

### Run Frontend Client

```bash
python main.py
```

Or run silently without console on Windows:

```bash
pythonw main.py
```

---

## 🧪 Automated Testing

To run the full unit test suite:

```bash
python test_app.py
```
