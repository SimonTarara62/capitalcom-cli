# Getting started (from zero)

This guide assumes nothing: no Capital.com account, no Python experience.
At the end you'll have run your first commands and (optionally) placed a
practice trade on a **demo** account with virtual money.

## 1. What you need

- A computer with **Python 3.10 or newer**. Check with:
  ```bash
  python3 --version
  ```
  If that fails, install Python from <https://www.python.org/downloads/>
  (macOS users can also `brew install python`; Windows users: tick
  "Add python.exe to PATH" in the installer).
- A free **Capital.com** account: <https://capital.com>

## 2. Create your API key

1. Sign up at capital.com and log in to the web platform.
2. Make sure **two-factor authentication (2FA)** is enabled — Capital.com
   requires it before it lets you generate API keys.
3. Go to **Settings → API integrations → Generate API key**.
4. Give the key a label and set a **custom password** for it. This is a
   *new* password just for the API key — it is NOT your account password.
5. Copy the generated key immediately. **It is shown only once.**

You now have the three values the CLI needs:

| Value | Goes into |
|-------|-----------|
| The generated API key | `CAP_API_KEY` |
| Your login email | `CAP_IDENTIFIER` |
| The custom API-key password from step 4 | `CAP_API_PASSWORD` |

## 3. Install capctl

**Recommended — one line** (needs [pipx](https://pipx.pypa.io/)):

```bash
pipx install capitalcom-cli
```

Using [uv](https://docs.astral.sh/uv/) instead:

```bash
uv tool install capitalcom-cli
```

(To install the latest unreleased code instead, use
`git+https://github.com/SimonTarara62/capitalcom-cli.git` in place of the package name.)

**Windows** (PowerShell): install Python 3.10+ from python.org (tick "Add
python.exe to PATH"), then either of the commands above works in PowerShell. If
`pipx` isn't found, run `python -m pip install --user pipx` then
`python -m pipx ensurepath` and reopen the terminal.

**For development** (clone + editable install):

```bash
git clone https://github.com/SimonTarara62/capitalcom-cli.git
cd capitalcom-cli
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Check it worked:

```bash
capctl --version
```

## 4. Configure your credentials

```bash
cp .env.example .env
```

Open `.env` in any text editor and fill in the three values from step 2.
Leave everything else at its default — the defaults are the safe ones:
**demo environment, trading disabled**.

> Treat `.env` like a password. Never commit it, never share it, never
> paste its contents anywhere. The repository's `.gitignore` already
> excludes it.

## 5. First commands

```bash
capctl session login        # should print your account id
capctl account list         # your demo account & virtual balance
capctl market search "gold" # find markets
capctl market get GOLD      # details, dealing rules, current price
capctl trade positions      # open positions (empty at first)
```

Every command also has `--help`:

```bash
capctl trade --help
capctl trade preview-position --help
```

## 6. Your first practice trade (demo, virtual money)

Trading is off by default. To enable it **on the demo account**, edit `.env`:

```dotenv
CAP_ALLOW_TRADING=true
CAP_ALLOWED_EPICS=GOLD        # only the markets you list here are tradeable
```

Trades are a two-step *preview → execute* flow. The preview validates
everything and creates nothing:

```bash
capctl trade preview-position GOLD BUY 0.1
```

You get back a table of risk checks and a `preview_id`. Execute it within
2 minutes (previews expire), confirming with `--yes`:

```bash
capctl trade execute-position <preview_id> --yes
```

See the position, then close it:

```bash
capctl trade positions
capctl trade close <dealId> --yes
```

## 7. Glossary

| Term | Meaning |
|------|---------|
| **EPIC** | Capital.com's identifier for a market, e.g. `GOLD`, `BTCUSD`, `EURUSD` |
| **Position** | An open trade |
| **Working order** | An instruction to open a trade when price reaches a level (LIMIT/STOP) |
| **Deal ID** | The identifier of an open position/order — used to close or cancel it |
| **Deal reference** | A receipt id returned when you submit a trade — used to check its confirmation |
| **Bid / Offer** | The sell price / buy price; the difference is the spread |
| **Demo vs Live** | Demo = virtual money sandbox. Live = real money. The CLI defaults to demo. |

## 8. Next steps

- The full command reference is in the [README](../README.md).
- Ideas for what to do with it: [practical use cases](use-cases.md) — alerts, data exports, monitoring, automation.
- Something not working? See [troubleshooting](troubleshooting.md).
- Automate things with `--json` — every command can emit machine-readable JSON.
