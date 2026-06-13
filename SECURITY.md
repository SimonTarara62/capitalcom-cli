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
