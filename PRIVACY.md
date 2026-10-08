# Privacy

The finHero plugins run locally in your Claude or Codex client.

- **Token:** your finHero API token is read from `FINHERO_API_KEY` or
  `~/.config/finhero/token`. It is sent only to `https://fin-hero.de` in the
  `Authorization` header.
- **Requests:** the plugin creates exports, reads their status and downloads
  the finished files. It doesn't read or upload anything else.
- **Files:** downloaded exports are saved in the folder you choose (default
  `./finhero-exports`). Nothing is uploaded to third parties.
- **finHero:** the processing of your payment data by finHero is covered by
  the finHero privacy policy at https://fin-hero.de and your data processing
  agreement.

Questions: support@fin-hero.de
