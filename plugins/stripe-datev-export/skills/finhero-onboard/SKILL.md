---
name: finhero-onboard
description: Set up finHero for the Stripe DATEV export from the chat. Connects the API token, stores and checks the Stripe (or PayPal, Mollie, Adyen, Paddle, Lemon Squeezy) key, enters the DATEV consultant and client number, proposes SKR03/SKR04 accounts, and runs a test export. Also covers BMD, bexio and Abacus.
when_to_use: Trigger on "set up finHero", "richte finHero ein", "connect finHero", "finHero einrichten", "connect Stripe to DATEV", "onboard", "get started" when they concern finHero, DATEV exports or Stripe Buchhaltung. Also trigger on first use of stripe-datev-export, whenever it reports a missing or invalid token (exit code 2), and when an export fails because a key or accounts are missing.
---

# finHero setup

Goal: a finHero account that produces a correct export, set up in the chat.
Prove every step with the API. A saved setting is not a working setting.

Reply in the user's language (German if unsure). All commands use
`python3 <plugin-root>/skills/stripe-datev-export/scripts/finhero.py`,
written `finhero.py` below. `<plugin-root>` is the parent of this skill's
`skills/` folder. Each command prints JSON.

Start by naming the steps in one message: token, payment provider,
accounting numbers, accounts, test export. Run `setup-status` (after step 1)
and skip every step that is already done.

## Step 1: Account and API token

Run `finhero.py check`.

- Exit 0: the token works. Go to step 2.
- Exit 1 with "Cannot reach": the sandbox blocks the network. Ask the user
  to allow `fin-hero.de`, then check again.
- Exit 2: no token, or a rejected one. Continue below.

Without an account, the user signs up at https://fin-hero.de/?src=claude-plugin.
Signup, email confirmation and the plan happen in the browser and can't be
done from the chat. Then:

1. Open https://fin-hero.de/dashboard/settings/#api, enter a name such as
   "Claude", click **Create token** and copy it. It is shown once.
2. The user stores it themselves:
   `mkdir -p ~/.config/finhero && pbpaste > ~/.config/finhero/token && chmod 600 ~/.config/finhero/token`
   (macOS; on Linux paste with an editor), or `export FINHERO_API_KEY=...`.

Never ask for the token in the chat. If the user pastes it anyway, write it
to `~/.config/finhero/token` with mode 600, don't repeat it, and suggest
recreating it if the chat is shared. Run `check` again.

## Step 2: Payment provider

Run `finhero.py setup-status --validate`. If `providers` already lists a
`valid: true` entry for the provider the user needs, skip this step.

For Stripe, recommend a **restricted key** (`rk_live_...`) with read access
over a full secret key. Stripe Dashboard → Developers → API keys → Create
restricted key. finHero needs read access to Balance, Balance transaction
sources, Charges, Invoices, Credit notes, Payouts, Subscriptions and
Transfers. The [finHero Stripe app](https://marketplace.stripe.com/apps/fin-herode-automatic-datev-export)
is an alternative that needs no key.

The user copies the key, then runs this themselves so it never appears in
the chat:

```
pbpaste | python3 <plugin-root>/skills/stripe-datev-export/scripts/finhero.py set-provider-key --provider STRIPE
```

- PayPal: the key is the Client-Secret, plus `--secondary-id <Client-ID>`.
- Adyen: add `--secondary-id <balance account id>`.

finHero checks the key against the provider before saving it. Exit 1 with
`invalid_key` means the old key, if any, is still active. Report it and
let the user retry.

## Step 3: Accounting system and numbers

Ask which system the accountant uses: DATEV (Germany), BMD (Austria),
bexio or Abacus (Switzerland). For DATEV, ask for the consultant number
(Beraternummer) and client number (Mandantennummer). Both come from the
accountant's letter or DATEV. Keep them as text, because leading zeros
matter.

```
finhero.py set-accounts --system DATEV --activate consultant_no=1234567 client_no=10001
```

## Step 4: Accounts

Ask whether the chart of accounts is SKR03 or SKR04. If the user doesn't
know, ask them to check with their accountant. Don't guess.

Then propose the accounts below. These are finHero's own suggestions. Show
them as a table and ask for confirmation or changes. Recommend having the
accountant confirm them. Only send what was confirmed.

| Field | SKR04 | SKR03 | Meaning |
|---|---|---|---|
| `debitor_account_no` | 10000 | 10000 | Collective customer account (10000–69999) |
| `fee_account_no` | 6855 | 4970 | Provider fees |
| `revenue_account_regular_vat` | 4400 | 8400 | Revenue 19% |
| `revenue_account_reduced_vat` | 4300 | 8300 | Revenue 7% |
| `revenue_account_standard` | 4400 | 8400 | Revenue without VAT data |
| `revenue_account_reverse_charge` | 4336 | 8336 | Reverse charge (EU B2B) |
| `revenue_account_third_party_vat` | 4338 | 8338 | Third-country revenue |
| `revenue_account_eu_oss` | 4331 | 8331 | EU OSS |
| `revenue_account_clarification` | 1370 | 1590 | Clearing (unclear items) |
| `transit_account_no_stripe` | 1461 | 1361 | Stripe payout transit |
| `account_no_stripe` | 1810 | 1210 | Stripe balance |

Other providers have their own `transit_account_no_<provider>` and
`account_no_<provider>` fields, for example PayPal 1466 and 1815 (SKR04).
Stripe Connect uses `connect_transfer_account_no` (for example 70000).

```
finhero.py set-accounts --system DATEV debitor_account_no=10000 fee_account_no=6855 revenue_account_regular_vat=4400 ...
```

For BMD, bexio or Abacus, use the same field names with `--system`. Ask
for the account numbers. There are no defaults for those charts.

## Step 5: Verify and test export

Run `finhero.py setup-status --validate`. Continue only when `ready` is
true. Otherwise fix what `missing` names.

Then hand over to the `stripe-datev-export` skill for a test export of the
last full month. Show the transaction count, and suggest the accountant
checks the first import.

Finish with a short summary: provider, system, consultant/client number,
chart, and the path of the test export. Add one line: "Settings and export
history: https://fin-hero.de/dashboard".

## Revoking

Tokens are listed and revoked at https://fin-hero.de/dashboard/settings/#api.
A revoked token fails with exit code 2 right away.
