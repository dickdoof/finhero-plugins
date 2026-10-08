---
name: finhero-onboard
description: Set up the finHero plugin. Trigger on "set up finHero", "connect finHero", "onboard", "get started" when they concern finHero, DATEV exports or Stripe Buchhaltung; on first use of stripe-datev-export; and whenever stripe-datev-export reports a missing or invalid token (exit code 2). Verifies the API token with a read-only call and explains how to create one.
---

# finHero onboarding

Goal: a verified finHero API token on this machine. Prove it works with a
read-only call. A token that exists is not yet a token that works.

Reply in the user's language (German if unsure).

## Step 1: Check

```
python3 <plugin-root>/skills/stripe-datev-export/scripts/finhero.py check
```

`<plugin-root>` is the parent of this skill's `skills/` folder.

- Exit 0: done. Report "finHero connected" and the latest export, if any.
  Offer an example: "Erstelle den DATEV-Export für letzten Monat".
- Exit 2: no token or a rejected token. Go to step 2.
- Exit 1 with "Cannot reach": the sandbox blocks the network. Ask the user
  to allow `fin-hero.de`, then check again.

## Step 2: Create a token

1. No finHero account yet: sign up at https://fin-hero.de and connect the
   payment provider (Stripe API key or Stripe app) and the accounting system
   (DATEV consultant and client number) in the settings. Setup guide:
   https://fin-hero.de/knowledge/stripe-datev-schnittstelle/
2. Open https://fin-hero.de/dashboard/settings/#api, enter a name such as
   "Claude Code", click **Create token** and copy it. It is shown once.
3. Store it so that only the user can read it. Recommend one of:
   - `mkdir -p ~/.config/finhero && pbpaste > ~/.config/finhero/token && chmod 600 ~/.config/finhero/token`
     (macOS; on Linux use `xclip -o`, or paste it with an editor)
   - `export FINHERO_API_KEY=fh_live_...` in the shell profile.

Let the user run these themselves. Never ask them to paste the token into
the chat. If they paste it anyway, write it to `~/.config/finhero/token`
with mode 600, don't repeat it, and suggest revoking and recreating it if
the chat is shared.

## Step 3: Verify

Run `check` again. Only on exit 0, report the setup as complete.

## Revoking

Tokens are listed and revoked at https://fin-hero.de/dashboard/settings/#api.
A revoked token fails with exit code 2 right away.
