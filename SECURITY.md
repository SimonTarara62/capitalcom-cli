# Security Policy

## Supported versions

This project is pre-1.0; only the latest release on `main` receives security
fixes.

## Reporting a vulnerability

Please report suspected vulnerabilities privately using GitHub's
[private vulnerability reporting](https://github.com/SimonTarara62/capitalcom-cli/security/advisories/new)
(Security tab → "Report a vulnerability"). Do not open a public issue for
security problems.

Include a description, reproduction steps, and the impact you observed. You can
expect an initial response within a few days.

## Handling credentials

`capctl` reads Capital.com credentials from a local `.env` file (or environment
variables) that is never committed — `.env` is in `.gitignore`. Never paste
credentials into issues, logs, or pull requests. Command output does not include
your API key, password, or session tokens; if you ever observe a secret in
output, treat it as a vulnerability and report it as above.

## Operating safely

- **Your API key is trading-capable.** Capital.com API keys can place and close
  real trades. Treat the key like a password.
- **Start with demo.** `capctl` defaults to the demo environment; keep `CAP_ENV=demo`
  until you fully trust your setup. Live trading requires explicit `--live` / `CAP_ENV=live`.
- **Never share `.env`.** It is gitignored; do not paste its contents into issues,
  logs, screenshots, or chats.
- **State file.** Trade previews and the daily order counter live in
  `~/.config/capital-cli/state.json`, written with `0600` permissions. Deleting it is safe.
- **Logs/output.** Command output and logs do not include your API key, password,
  or session tokens (they are redacted). If you ever see a secret in output, report it.
- **No financial advice.** This is an unofficial tool; nothing it outputs is advice.
  CFD trading carries a high risk of losing money. Use at your own risk.
