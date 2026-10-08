# Privacy

The finHero plugins run locally in your Claude or Codex client.

- **Token:** your finHero API token is entered as a plugin option and kept by
  Claude Code in your system's secure credential store. The bundled MCP server
  receives it from Claude Code and sends it only to `https://fin-hero.de` in the
  `Authorization` header.
- **Requests:** the plugin creates exports, reads their status, downloads the
  finished files, reads the setup status and saves the account numbers you
  confirm. Payment provider keys are entered on fin-hero.de, never through the
  plugin. It doesn't read or upload anything else.
- **Files:** downloaded exports are saved in the folder you choose (default
  `./finhero-exports`). They can contain personal data from your payment
  provider, such as customer names, email addresses and invoice addresses in
  booking texts and receipts. Nothing is uploaded to third parties.
- **Retention:** finHero keeps export requests, export files and your account
  settings for as long as your finHero account exists. The plugin itself keeps
  no data besides the files you download.
- **finHero:** the processing of your payment data by finHero is covered by
  the finHero privacy policy at https://fin-hero.de and your data processing
  agreement.

Questions: support@fin-hero.de
