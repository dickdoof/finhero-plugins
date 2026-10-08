# finHero Plugins for Claude & Codex

Plugins and agent skills by [finHero](https://fin-hero.de), the automatic
[Stripe to DATEV export](https://fin-hero.de/knowledge/stripe-datev-export/).

**Stripe DATEV Export** lets Claude create and download your accounting
export for any period from a single sentence:

> Erstelle den DATEV-Export für September.
>
> Export Stripe and PayPal to DATEV for Q3 and save it in ./buchhaltung.

Claude works out the period, orders the export from finHero, waits until it
is ready and saves the ZIP. The ZIP contains the DATEV Buchungsstapel (fees,
refunds, payouts as Geldtransit), the receipts and the PRAP list for
subscriptions. Claude then tells you how to import it.

It works in Claude Code (CLI and desktop app), Claude Cowork and the Codex
app and CLI.

## Install

**Claude Code (CLI)**

```bash
claude plugin marketplace add dickdoof/finhero-plugins
claude plugin install stripe-datev-export@finhero --scope user
```

**Claude Code (desktop app)**

```
/plugin marketplace add dickdoof/finhero-plugins
/plugin install stripe-datev-export@finhero
```

Pick **User scope** when asked.

**Claude Cowork**: Customize → Plugins → add
`https://github.com/dickdoof/finhero-plugins`, then install
**Stripe DATEV Export by finHero**. Allow network access to `fin-hero.de`.

**Codex**

```bash
codex plugin marketplace add dickdoof/finhero-plugins
codex plugin add stripe-datev-export@finhero
```

## Set up

1. Create a free account at [fin-hero.de](https://fin-hero.de). Connect
   Stripe (API key or [Stripe app](https://marketplace.stripe.com/apps/fin-herode-automatic-datev-export))
   and enter your DATEV consultant and client number.
2. Create an API token under
   [Settings → API & Claude](https://fin-hero.de/dashboard/settings/#api).
3. Save it locally, then say **"Set up finHero"** to Claude:

```bash
mkdir -p ~/.config/finhero && chmod 700 ~/.config/finhero
printf '%s\n' 'fh_live_…' > ~/.config/finhero/token && chmod 600 ~/.config/finhero/token
# or: export FINHERO_API_KEY=fh_live_…
```

## Skills

| Skill | What it does |
|---|---|
| `finhero-onboard` | Checks the token with a read-only call and walks you through setup. |
| `datev-export` | Turns "last month", "Q3 2026" or "September" into a date range. Creates the export (DATEV, BMD, bexio or Abacus) for Stripe, PayPal, Mollie, Adyen, Paddle or Lemon Squeezy, waits and downloads it. It can also list and re-download earlier exports. |

The skills call a small Python script (standard library only):

```bash
python3 plugins/stripe-datev-export/skills/datev-export/scripts/finhero.py \
  create --start 2026-09-01 --end 2026-09-30 --format DATEV --wait
```

## Stripe Buchhaltung in Germany

New to booking Stripe? These finHero guides explain what Claude exports:

- [Stripe Buchhaltung in Deutschland: Was muss in DATEV landen?](https://fin-hero.de/knowledge/stripe-buchhaltung-deutschland-datev/)
- [Stripe-Gebühren in DATEV buchen](https://fin-hero.de/knowledge/stripe-gebuehren-datev-buchen/)
- [Stripe zu DATEV exportieren](https://fin-hero.de/knowledge/stripe-zu-datev-exportieren/)
- [Stripe DATEV Schnittstelle](https://fin-hero.de/knowledge/stripe-datev-schnittstelle/)
- [PRAP für SaaS-Abos mit Stripe](https://fin-hero.de/knowledge/prap-saas-abos-stripe/)

## Data handling

The plugin talks only to `fin-hero.de` with your token. It doesn't send
your Stripe keys, bookings or files anywhere else. Exports are processed by
finHero as in the dashboard. See [PRIVACY.md](PRIVACY.md).

## Structure

```
.claude-plugin/marketplace.json        Claude Code catalog
.agents/plugins/marketplace.json       Codex catalog
plugins/stripe-datev-export/
  .claude-plugin/plugin.json           Claude Code manifest
  .codex-plugin/plugin.json            Codex manifest
  skills/finhero-onboard/SKILL.md
  skills/datev-export/SKILL.md
  skills/datev-export/scripts/finhero.py
scripts/validate_repo.py               CI checks
```

## Support

[support@fin-hero.de](mailto:support@fin-hero.de) ·
[fin-hero.de](https://fin-hero.de) · finHero is a product of d-automation
GmbH, Germany. Stripe and DATEV are trademarks of their owners. This
plugin is not affiliated with them.
