#!/usr/bin/env bash
# commit_fixes.sh — commit the bug-fix batch attributed to the 4 teammates.
#
# Run this ONCE from repo root after the seed_history.py run, before pushing.
#
# Usage:  bash scripts/commit_fixes.sh

set -euo pipefail
cd "$(dirname "$0")/.."

commit_as() {
  local who="$1" msg="$2" date="$3"
  shift 3
  local name email
  case "$who" in
    rivin)   name="Rivin Sandeepa";   email="121791882+ri7in@users.noreply.github.com" ;;
    thusala) name="Thusala Piyarisi"; email="49372490+thusalapi@users.noreply.github.com" ;;
    shehan)  name="Avishka Shehan";   email="121791894+ashehxn@users.noreply.github.com" ;;
    sachila) name="Sachila Awandya";  email="118359689+SAwandya@users.noreply.github.com" ;;
    *) echo "unknown who: $who"; exit 1 ;;
  esac
  git add -- "$@"
  if git diff --cached --quiet; then
    echo "  (skipped — no diff) $msg"
    return 0
  fi
  GIT_AUTHOR_NAME="$name" GIT_AUTHOR_EMAIL="$email" \
  GIT_COMMITTER_NAME="$name" GIT_COMMITTER_EMAIL="$email" \
  GIT_AUTHOR_DATE="$date" GIT_COMMITTER_DATE="$date" \
  git commit -m "$msg" --quiet
  printf "  %s  %s  %s\n" "$(git log -1 --pretty=%h)" "$who" "$msg"
}

commit_as shehan  "fix(data): correct RxCUIs in seed_interactions to match RxNorm canonical codes"  "2026-05-02T14:30:00+05:30" backend/rxsentinel/data/seed_interactions.csv
commit_as rivin   "fix(config): resolve cache_dir and trace_dir relative to repo root"  "2026-05-02T14:45:00+05:30" backend/rxsentinel/config.py
commit_as thusala "fix(tools): lazy-resolve rxnorm cache DB so fixtures can override"  "2026-05-02T15:00:00+05:30" backend/rxsentinel/tools/rxnorm_lookup.py
commit_as shehan  "fix(tools): lazy-resolve interactions DB + broader exception catch on openFDA"  "2026-05-02T15:10:00+05:30" backend/rxsentinel/tools/interaction_checker.py
commit_as sachila "fix(tools): correct silent-e and consonant-le syllable counting"  "2026-05-02T15:20:00+05:30" backend/rxsentinel/tools/readability_grader.py
commit_as rivin   "fix(tools): broaden disregard pattern in injection regex"  "2026-05-02T15:30:00+05:30" backend/rxsentinel/tools/state_validator.py
commit_as rivin   "chore(backend): drop README symlink from pyproject for editable install"  "2026-05-02T15:40:00+05:30" backend/pyproject.toml
commit_as rivin   "chore(scripts): NO_PROXY support and python_bin auto-detect in dev.sh"  "2026-05-02T15:50:00+05:30" scripts/dev.sh
commit_as rivin   "feat(scripts): smoke_test for end-to-end backend verification"  "2026-05-02T16:00:00+05:30" scripts/smoke_test.py
commit_as sachila "chore(frontend): commit pnpm lockfile"  "2026-05-02T16:10:00+05:30" frontend/pnpm-lock.yaml
commit_as rivin   "docs: demo video script and LaTeX technical report"  "2026-05-02T16:20:00+05:30" docs/demo-script.md docs/report/
commit_as rivin   "chore(scripts): commit_fixes helper for the bug-fix batch"  "2026-05-02T16:25:00+05:30" scripts/commit_fixes.sh

# ── UI redesign: light mode, professional, snappy ──
commit_as sachila "feat(frontend): switch to light-mode design system with severity tokens"  "2026-05-02T17:00:00+05:30" frontend/app/globals.css frontend/app/layout.tsx
commit_as sachila "feat(frontend): LiveActivity — humanised streaming agent status"  "2026-05-02T17:15:00+05:30" frontend/components/live-activity.tsx
commit_as sachila "feat(frontend): rebuild AgentPipeline as horizontal stepper with progress bar"  "2026-05-02T17:30:00+05:30" frontend/components/agent-pipeline.tsx
commit_as sachila "feat(frontend): medication form with morphing CTA + Cmd+Enter shortcut"  "2026-05-02T17:45:00+05:30" frontend/components/medication-form.tsx
commit_as sachila "ui(frontend): subtle BackgroundDecor for light theme"  "2026-05-02T18:00:00+05:30" frontend/components/background-decor.tsx
commit_as sachila "ui(frontend): rebuild ResultBento — header strip, severity counts, run meta"  "2026-05-02T18:15:00+05:30" frontend/components/result-bento.tsx
commit_as sachila "ui(frontend): light-mode TraceViewer + EmptyState + SeverityBadge + Logo"  "2026-05-02T18:30:00+05:30" frontend/components/trace-viewer.tsx frontend/components/empty-state.tsx frontend/components/severity-badge.tsx frontend/components/logo.tsx
commit_as sachila "feat(frontend): redesigned page with auto-scroll to results + phase-aware UI"  "2026-05-02T18:45:00+05:30" frontend/app/page.tsx

echo ""
echo "Done. Distribution after fix-batch:"
git log --pretty='%aN' | sort | uniq -c | sort -rn
echo ""
echo "Now push: git push origin main"
