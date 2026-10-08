# Changelog

## 2026.10.4

- The finHero API token is now a sensitive plugin option (`userConfig.api_token`),
  stored by Claude Code in the secure credential store, instead of an environment
  variable or a file in the home directory (Claude plugin directory policy).
- The skills use a bundled `finhero` MCP server (`mcp/finhero_mcp.py`) with the
  tools check, list_exports, create_export, wait_for_export, download_export,
  setup_status and set_accounts. The old `finhero.py` script is gone.
- Payment provider keys are entered on fin-hero.de; the plugin never handles them.

## 2026.10.3

- Plugin renamed to `finhero-datev-export` for the Claude plugin directory
  (brand names are not allowed in plugin names). Install with
  `finhero-datev-export@finhero`. The skill is still called `stripe-datev-export`.
- Added MIT license, plugin README and directory listing fields (icon,
  documentation, support, privacy policy and terms URLs).

## 2026.10.2

- `finhero-onboard` now runs the whole setup in the chat: provider key
  (piped in, never shown in the chat), DATEV consultant and client number,
  SKR03/SKR04 account suggestions, and a test export.
- New script commands: `setup-status`, `set-provider-key`, `set-accounts`.

## 2026.10.1

- Renamed the export skill to `stripe-datev-export`. Its description now
  leads with "Stripe DATEV Export" and a `when_to_use` lists trigger phrases.
- Added discovery `keywords` and a `relevance` block (Stripe SDK, Stripe CLI,
  DATEV CSV files) to the catalog, and a version for strict validation.

## 2026.10.0

- First release: `stripe-datev-export` plugin with the `finhero-onboard` and
  `stripe-datev-export` skills.
