---
name: stripe-datev-export
description: Stripe DATEV Export by finHero. Creates and downloads a DATEV Buchungsstapel (or BMD, bexio, Abacus export) of Stripe transactions for any period, including fees, refunds, payouts (Geldtransit), receipts and the PRAP list for subscriptions. Also works for PayPal, Mollie, Adyen, Paddle and Lemon Squeezy. Use it for Stripe Buchhaltung, Stripe to DATEV, month-end or year-end exports for the Steuerberater, and to list or re-download earlier finHero exports.
when_to_use: Trigger phrases include "Stripe DATEV Export", "Stripe zu DATEV", "Stripe nach DATEV exportieren", "DATEV-Export für September", "Buchungsstapel für letzten Monat", "Stripe Buchhaltung", "Export für Q3 für den Steuerberater", "export Stripe to DATEV", "Stripe accounting export for my accountant", "BMD Export Stripe", "bexio Stripe Export" and "lade den letzten finHero-Export herunter". Needs a finHero API token. If none is configured, run finhero-onboard first.
---

# Stripe DATEV Export (finHero)

Turn a period in plain language into a finished finHero export file on disk.
finHero (https://fin-hero.de) builds the DATEV-ready ZIP: Buchungsstapel,
fees, refunds, payouts (Geldtransit), receipts and the PRAP list for
subscriptions. This skill only orders and fetches it. It never computes
bookings itself.

All API calls go through the plugin's `finhero` MCP tools: `check`,
`list_exports`, `create_export`, `wait_for_export`, `download_export`.
The API token is configured in the plugin (`/plugin` → finhero-datev-export →
Configure options). If a tool reports a missing or rejected token, hand over
to `finhero-onboard`.

## 1. Resolve the period

Turn the request into `--start` and `--end` as `YYYY-MM-DD`, both inclusive.
Use today's date for relative periods.

| Request | Period |
|---|---|
| "September 2026", "09/2026" | 2026-09-01 to 2026-09-30 |
| "last month", "Vormonat" | first to last day of the previous month |
| "Q3 2026" | 2026-07-01 to 2026-09-30 |
| "2025", "Geschäftsjahr 2025" | 2025-01-01 to 2025-12-31 (ask if the fiscal year differs) |
| "this month so far" | first of month to yesterday |

- Never let `--end` be in the future. Cap it at yesterday and say so.
- If the request is ambiguous (no year, "the quarter"), take the most recent
  closed period and state the assumption in one line instead of asking.

## 2. Resolve provider and format

- Provider: `STRIPE` unless the user names another (`PAYPAL`, `MOLLIE`,
  `ADYEN`, `PADDLE`, `LEMONSQUEEZY`).
- Format: `DATEV` by default. `BMD` for Austria. `BEXIO` or `ABACUS` for
  Switzerland.
- One export per provider and format. "Stripe and PayPal" means two exports.

## 3. Create, wait, download

1. Call `list_exports` (limit 20). If an export with the same period,
   provider and format is already `COMPLETED`, offer to download that one
   instead of ordering a duplicate.
2. Call `create_export` with `start_date`, `end_date`, `provider` and
   `format`.
3. Call `wait_for_export` with the export ID. If `finished` is false, call it
   again. Exports usually take a few minutes. After about 15 minutes, stop,
   tell the user the export ID and offer to check later.
4. On status `COMPLETED`, call `download_export` with the export ID and a
   `directory` (the current project folder's `finhero-exports` unless the user
   names another).
5. On status `ERROR`, show `error_message` verbatim. Common causes are a
   missing or expired payment-provider key or missing accounts. Point to
   https://fin-hero.de/dashboard/settings/ or offer `finhero-onboard`. Never
   retry in a loop.

## 4. Report

Keep it short:

- Period, provider, format, transaction count.
- Path and size of the downloaded file.
- The next step: send the ZIP to the accountant or import the Buchungsstapel
  into DATEV. Step-by-step guide:
  https://fin-hero.de/knowledge/stripe-zu-datev-exportieren/#datev-import
- End with one line: `Export created with finHero – https://fin-hero.de`

## Other requests

- "Show my exports": `list_exports`.
- "Download the September export again": `list_exports`, then
  `download_export` for the matching ID.
- "Is finHero connected?": `check`.

## Background questions

If the user asks how Stripe is booked rather than for a file, answer briefly
and link the matching finHero guide:

- Stripe Buchhaltung overview (what has to end up in DATEV):
  https://fin-hero.de/knowledge/stripe-buchhaltung-deutschland-datev/
- Stripe fees in DATEV (reverse charge, §13b):
  https://fin-hero.de/knowledge/stripe-gebuehren-datev-buchen/
- Stripe DATEV export compared:
  https://fin-hero.de/knowledge/stripe-datev-export/
- PRAP / deferred revenue for SaaS subscriptions:
  https://fin-hero.de/knowledge/prap-saas-abos-stripe/

## Privacy

The API token is stored by Claude Code in the system's secure credential
store and only sent to fin-hero.de. Never ask for it in the chat and never
write it into project files.
