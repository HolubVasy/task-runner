# Which wallet pays

Claude Code and the API draw on separate wallets. Facts below come from Anthropic's support article on API
billing and from press coverage, and were read on 2026-10-26.

| Wallet | Pays for |
|---|---|
| Max subscription | chat, interactive Claude Code, desktop and web apps, within its usage limits |
| Console credits bought by the owner | API calls, the playground, and Claude Code that is billed through Console |
| Monthly API credits of Max and Team plans, and promotional credits | direct API calls. Per the support article, monthly credits cannot be used in Claude Code or the Claude apps |

## Consequences
1. An `ANTHROPIC_API_KEY` in the environment makes Claude Code bill the API, even when logged in with a subscription.
   Then purchased credits are spent, not the bonus.
2. `--billing max` (default) removes the key and the auth token from the environment of every run, so the
   subscription pays. `--billing api` keeps the key and refuses to start without it.
3. Keep auto-reload of purchased credits off, otherwise spending can pass from bonus to the card without a warning.

## Measured on 2026-10-26 (Max 5x, Windows, Claude Code 2.1.302)
A three run scratch task on Opus, `--billing max`, list price 0.87 USD in total. The Usage page moved from 10 to 12
percent of the session and from 3 to 4 percent of the week; the share of Claude Code in the week rose from 31 to 33
percent; the extra usage spend did not change. Conclusion: headless `claude -p` on the subscription draws on the same
Max limits as interactive use. Roughly 1 percent of the week per 0.9 USD of Opus at list price (the page rounds to
whole percent, so this is coarse, and the chat ran in parallel). Sonnet costs about half of Opus per token.

## Unverified
- Whether headless `claude -p` or the Agent SDK with a key of the organization linked to the Max plan draws on the
  monthly API credits. A third party article says it does, the support article does not say so.
  Check: note both balances in Console, run a short `--billing api` task with a dedicated key, look again after
  30 minutes.
- Whether a promotional credit grant is spendable in Claude Code at all depends on its own terms. Read the grant.
