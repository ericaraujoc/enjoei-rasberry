# enjoei-rasberry 🍓

Telegram bot that automatically clicks **Megafonar** on your Enjoei listings 24/7, running on a Raspberry Pi 3.

Manage multiple stores, set custom run intervals per store, and receive daily reports — all from Telegram.

---

## Features

- Automatically boosts all available listings every N minutes
- Manage multiple stores with independent intervals (e.g. store A every 5 min, store B every 20 min)
- Add, rename, or remove stores via Telegram
- Daily summary sent at 23:55
- Cookie expiry alerts via Telegram
- Runs as a systemd service (auto-starts on boot, auto-restarts on crash)

---

## Requirements

- Raspberry Pi 3 with **Raspberry Pi OS 64-bit** (required for Playwright/Chromium)
- Internet connection
- A Telegram bot token (from [@BotFather](https://t.me/BotFather))
- Your Telegram user ID (from [@userinfobot](https://t.me/userinfobot))

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/ericaraujoc/enjoei-rasberry.git
cd enjoei-rasberry
```

### 2. Configure environment variables

```bash
cp .env.example .env
nano .env
```

Fill in your values:

```
TELEGRAM_TOKEN=your_bot_token_here
TELEGRAM_USER_ID=your_telegram_user_id_here
```

- **TELEGRAM_TOKEN** — get it from [@BotFather](https://t.me/BotFather) → `/newbot`
- **TELEGRAM_USER_ID** — get it from [@userinfobot](https://t.me/userinfobot)

Save and exit: `Ctrl+X` → `Y` → `Enter`

### 3. Run the install script

```bash
bash install.sh
```

This will:
- Check that you are on a 64-bit OS
- Create a Python virtual environment
- Install all dependencies
- Install Playwright and Chromium
- Register and start the systemd service

---

## Telegram Bot Commands

| Command | Description |
|---|---|
| `/start` | Show command list |
| `/addcookie` | Add a new store (cookie → interval → name → URL) |
| `/status` | View all stores, intervals, and today's stats |
| `/rename` | Rename a store |
| `/remove` | Remove a store |
| `/resume` | Show today's boost summary |
| `/setinterval` | Change the run interval for a store |
| `/cancel` | Cancel any active operation |

### Adding a store — step by step

When you send `/addcookie`, the bot will guide you through 4 steps:

```
1/4 — Paste the _website_session_7 cookie value
2/4 — Run interval in minutes? (e.g. 20)
3/4 — Custom name for this store? (e.g. Loja Érica)
4/4 — Store handle on Enjoei? (e.g. @ericshop)
```

### How to get the Enjoei cookie

1. Open [enjoei.com.br](https://www.enjoei.com.br) in your browser and log in
2. Open DevTools: `F12` → **Application** tab → **Cookies** → `www.enjoei.com.br`
3. Find the cookie named `_website_session_7`
4. Copy its **Value** and paste it in the bot when prompted

> The cookie usually lasts 7–30 days. The bot will notify you on Telegram when it expires.

---

## Service Management

```bash
# Check if the bot is running
sudo systemctl status enjoei

# View live logs
sudo journalctl -u enjoei -f

# Restart the bot
sudo systemctl restart enjoei

# Stop the bot
sudo systemctl stop enjoei
```

---

## Updating

```bash
cd enjoei-rasberry
git pull
sudo systemctl restart enjoei
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| "Cookie expired" alert on Telegram | Get a new `_website_session_7` cookie and use `/addcookie` |
| Bot not responding | Check logs: `sudo journalctl -u enjoei -f` |
| Playwright install fails | Make sure you are using **64-bit Raspberry Pi OS** (`uname -m` should show `aarch64`) |
| 0 boosts every round | Enjoei may have changed its HTML — open an issue on GitHub |

---

## Project Structure

```
enjoei-rasberry/
├── bot.py          — Telegram bot + scheduler
├── runner.py       — Playwright automation
├── stores.py       — Store & stats persistence
├── data/
│   └── stores.json — Runtime data (auto-created)
├── .env.example    — Environment variable template
├── requirements.txt
├── enjoei.service  — systemd unit file
└── install.sh      — Setup script
```

---

## License

MIT
