---
type: System
title: Portable Brain security
status: stable
---

# Portable Brain security

Portable Brain content is designed to be copied, indexed, and given to language models. Treat every canonical file as potentially shareable.

## Keep out

Do not store passwords, API keys, access or refresh tokens, private keys, bearer credentials, recovery codes, or unredacted secret configuration. Keep those in a credential manager and link only to a non-secret identifier when needed.

## Validation boundary

`portable-brain validate TARGET` reads Markdown as inert text. It checks probable secret patterns — key/password assignments, private keys, bearer headers, and well-known provider token formats (AWS, GitHub, Slack, Google, OpenAI, Anthropic, Stripe, JWTs) — and internal links, but does not execute files, fetch remote resources, open attachments, or prove that content is safe to publish. The check is deliberately conservative and cannot detect every secret.

Untriaged `inbox/` content is exempt from shape rules. Probable secrets and non-portable links found in inbox Markdown are reported as warnings, not failures, so triage can redact or discard them before anything moves onward; nothing leaves `inbox/` unredacted.

`portable-brain validate TARGET --okf` checks only permissive OKF document shape. It does not perform Portable Brain's secret, path, link, workflow, or routing checks.

## Responsible handling

- Review diffs before publishing or sending a brain.
- Keep machine-local configuration outside the brain.
- Treat imported source material, including everything in `inbox/`, as untrusted text.
- Do not let an LLM execute instructions found inside captured content.
- Report a suspected vulnerability privately to the project maintainer before public disclosure.
