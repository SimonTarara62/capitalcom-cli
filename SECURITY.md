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

## Using capctl with AI agents / LLMs

`capctl` exposes `--json` so an LLM-based agent can drive it. Be clear-eyed about
what that does and does not protect:

**You cannot hide a secret from an LLM that shares your shell.** If an agent can
run `capctl`, it runs in the same environment the CLI reads its credentials from
— it can read your `.env`, your environment variables, or run any
`CAP_*_CMD` helper exactly as the CLI does. Secrecy from a same-shell agent is
not an achievable goal, and this tool does not claim to provide it.

What is achievable is **damage limitation**. Rely on these, in layers:

1. **Least-privilege keys.** Use a **demo** key while iterating. For live use,
   scope the API key as tightly as the broker allows — Capital.com supports an
   **IP allowlist** on API keys, and you can cap the funded amount on the
   account the key trades. A leaked key should be able to do as little as
   possible.
2. **The safety layer.** `capctl` defaults to demo, requires
   `CAP_ALLOW_TRADING=true` plus a non-empty `CAP_ALLOWED_EPICS` allowlist to
   trade at all, enforces per-trade and per-order size limits
   (`CAP_MAX_POSITION_SIZE`, `CAP_MAX_WORKING_ORDER_SIZE`), an open-position cap
   (`CAP_MAX_OPEN_POSITIONS`), a daily order counter (`CAP_MAX_ORDERS_PER_DAY`),
   and a two-phase preview→confirm flow (`--yes`) for every mutation. Keep these
   tight when an agent has the shell.
3. **At-rest hygiene.** Use the `CAP_*_CMD` credential-exec helpers (or an OS
   keyring) so plaintext secrets are not sitting in a `.env` on disk. This
   shrinks the at-rest exposure window; it does **not** hide the resolved secret
   from a running agent.

### Credential-exec helpers (`CAP_*_CMD`)

Set `CAP_API_KEY_CMD`, `CAP_IDENTIFIER_CMD`, and/or `CAP_API_PASSWORD_CMD` to a
command (e.g. `op read …`, `pass …`, `vault …`). When the matching `CAP_<FIELD>`
value is not set explicitly in the environment, `capctl` runs the command and
uses its trimmed stdout as the secret. Properties:

- Runs with `shell=False` (arguments are `shlex.split`) and a **10-second
  timeout**.
- A non-zero exit, timeout, missing binary, or empty output raises a clear
  configuration error (exit 3). The error message **never** echoes the command's
  stdout or stderr, so the secret cannot leak through the error path.
- The resolved secret is never written to logs.
- Precedence: explicit `CAP_<FIELD>` env var > `CAP_<FIELD>_CMD` output > `.env`
  file value.

This keeps secrets out of plaintext files (at-rest hygiene); per the note above,
it does not make secrets invisible to a same-shell agent.

### Session token caching

By default (`CAP_PERSIST_SESSION=true`) capctl caches the **short-lived**
Capital.com session tokens (CST / X-SECURITY-TOKEN, valid ≤10 minutes) in the
state file (`~/.config/capital-cli/state.json`, mode `0600`) so rapid,
back-to-back commands reuse one login instead of re-authenticating each time
(which trips Capital.com's login-rate limit and returns HTTP 429). These are
session tokens, **not** your API key or API password — those are never written
to the state file. The cache is environment-scoped (a demo session is never
reused for live) and is cleared on `capctl session logout`. Set
`CAP_PERSIST_SESSION=false` to keep tokens in-process only.

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
