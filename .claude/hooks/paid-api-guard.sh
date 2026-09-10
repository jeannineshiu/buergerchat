#!/usr/bin/env bash
# PreToolUse hook (Bash): force a permission prompt before a command that
# spends OpenAI money, even when an allow rule (e.g. "Bash(conda run *)" in
# settings.local.json) would let it run silently.
#
# Why: on 2026-09-10 Claude ran ~$17-20 of golden evals without asking.
# Local evals share the OpenAI account with production, so the prepaid
# balance ran out and /chat went down for everyone.
#
# Matches (python immediately followed by the script, so "py_compile" and
# grep/edit commands that merely mention the file don't prompt):
#   - evals/run_evals.py ... --yes   (without --yes it only prints an estimate)
#   - scripts/smoke_test.py          (real /chat calls against production)
# Not covered: ad-hoc scripts that import rag.py — that stays a memory rule.

cmd=$(jq -r '.tool_input.command // ""')

reason=""
if printf '%s' "$cmd" | grep -Eq 'python[0-9.]*[[:space:]]+([^[:space:];&|]*/)?run_evals\.py[^;&|]*--yes'; then
  reason="Paid OpenAI call: golden eval with --yes. Run it without --yes first to see the cost estimate."
elif printf '%s' "$cmd" | grep -Eq 'python[0-9.]*[[:space:]]+([^[:space:];&|]*/)?smoke_test\.py'; then
  reason="Paid OpenAI call: production smoke test (~\$0.05 per question, counts against DAILY_BUDGET_USD)."
fi

if [ -n "$reason" ]; then
  jq -n --arg r "$reason" \
    '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "ask", permissionDecisionReason: $r}}'
fi
exit 0
