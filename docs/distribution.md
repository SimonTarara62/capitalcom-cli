# Distribution & registries

Where `capitalcom-cli` is published, and prepared text for directories that need
a manual/editorial submission. Curated *awesome-list* targets live separately in
[awesome-submission.md](awesome-submission.md).

## Live channels
- **PyPI** — https://pypi.org/project/capitalcom-cli/ (`pipx install capitalcom-cli`)
- **Homebrew tap** — `brew install SimonTarara62/tap/capctl`
  (repo: https://github.com/SimonTarara62/homebrew-tap)
- **Libraries.io** — passive; ingests PyPI metadata automatically.

## Terminal Trove — prepared submission (submit manually)

Terminal Trove (https://terminaltrove.com) is an editorial directory of terminal
tools. Submit via its "Submit a tool" form. **This is an outward-facing post —
done by the maintainer, not automated.** Ready-to-paste content:

- **Name:** capctl
- **Category:** CLI
- **Tagline:** Unofficial, safety-first command-line client (and async Python
  SDK) for the Capital.com Open API — market data, guarded order execution, and
  real-time streaming.
- **Homepage / repo:** https://github.com/SimonTarara62/capitalcom-cli
- **Docs:** https://github.com/SimonTarara62/capitalcom-cli#readme
- **Install:**
  - `pipx install capitalcom-cli`
  - `brew install SimonTarara62/tap/capctl`
- **License:** Apache-2.0
- **Language:** Python (3.10+)
- **Demo/screenshot:** reuse the `capctl market search "gold"` table from the
  README, or record an asciinema of `market search` → `trade preview-position`.
- **Disclaimer (include verbatim):** Unofficial. Not affiliated with, endorsed
  by, or sponsored by Capital.com.

## Deferred (per spec — revisit on demand/traction)
Homebrew-core, Docker/GHCR/Docker Hub, conda-forge, AUR, Nixpkgs, winget, Scoop,
Chocolatey, best-of-python, awesome-fintech.
