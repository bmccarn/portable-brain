---
type: Change
title: Enable structured request logging
description: A planned production logging change.
status: draft
tags: [observability]
generated:
  by: human:example
  at: 2026-08-22T00:00:00+00:00
pb_work_state: active
pb_owner: human:example
---
# Enable structured request logging

## Summary
Add structured fields to request logs.

## Motivation
Make failed requests searchable by request identifier.

## Implementation
Emit the request identifier, route, and outcome as structured fields.

## Rollout
Deploy first to staging.

## Verification
Send one successful and one failed request in staging.

## Follow-ups
- [ ] Confirm the staging fields are queryable (owner: human:example).

## Log
Change opened after an incident review.

## References
No external references.
