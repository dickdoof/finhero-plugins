# Stripe DATEV Export (finHero)

Create and download your finHero accounting export from a single sentence in
Claude Code, Claude Cowork or Codex:

> Erstelle den DATEV-Export für September.

Claude works out the period, orders the export from [finHero](https://fin-hero.de),
waits until it is ready and saves the ZIP. The ZIP contains the DATEV
Buchungsstapel with fees, refunds and payouts, the receipts, and the PRAP list
for subscriptions. It works for Stripe, PayPal, Mollie, Adyen, Paddle and Lemon
Squeezy, with DATEV, BMD, bexio or Abacus as the target system.

## Skills

- `finhero-onboard`: sets up finHero in the chat. It checks the API token, stores
  and verifies the payment provider key, enters the DATEV consultant and client
  number, proposes SKR03/SKR04 accounts and runs a test export.
- `stripe-datev-export`: creates, lists and downloads exports for any period.

## Requirements

A finHero account and an API token from
[fin-hero.de → API & Claude](https://fin-hero.de/dashboard/api/). The plugin talks
only to `fin-hero.de`. See [PRIVACY.md](../../PRIVACY.md).

## Support

[GitHub issues](https://github.com/dickdoof/finhero-plugins/issues) or
support@fin-hero.de. MIT licensed.
