#!/usr/bin/env bash
# Install the AI Engineering Kit into a target project.
#
#   scripts/install.sh <target-dir> [--harness claude,codex,agy|all] [--adapter <name|path>]
#                      [--speckit] [--link] [--force] [--dry-run]
#
#   --harness   where to install skills (default: all)
#                 claude → .claude/skills/   codex, agy → .agents/skills/
#   --adapter   adapter name under adapters/ or a path to an adapter directory (default: default)
#   --speckit   also register the Spec Kit extension, preset and workflows (needs `specify`
#               on PATH and an initialized .specify/ in the target)
#   --link      symlink skills instead of copying them (for kit development)
#   --force     overwrite existing kit files and skills
#   --dry-run   print what would happen, change nothing
set -euo pipefail

KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS=(exploring-idea shaping-feature intaking-ticket shaping-project executing-task
        shipping-infrastructure verifying-change accepting-change reviewing-change authoring-pr
        systematic-debugging using-worktrees parallel-development test-driven-development
        finishing-branch)
MARK_BEGIN="<!-- ai-engineering-kit:begin -->"
MARK_END="<!-- ai-engineering-kit:end -->"

die() { echo "error: $*" >&2; exit 1; }
say() { echo "  $*"; }

TARGET="" HARNESS="all" ADAPTER="default" SPECKIT=0 LINK=0 FORCE=0 DRY=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --harness) HARNESS="${2:?}"; shift 2 ;;
    --adapter) ADAPTER="${2:?}"; shift 2 ;;
    --speckit) SPECKIT=1; shift ;;
    --link) LINK=1; shift ;;
    --force) FORCE=1; shift ;;
    --dry-run) DRY=1; shift ;;
    -h|--help) sed -n '2,17p' "$0"; exit 0 ;;
    -*) die "unknown option $1" ;;
    *) [[ -z "$TARGET" ]] || die "only one target dir"; TARGET="$1"; shift ;;
  esac
done
[[ -n "$TARGET" ]] || die "usage: install.sh <target-dir> [options]  (see --help)"
[[ -d "$TARGET" ]] || die "target dir not found: $TARGET"
TARGET="$(cd "$TARGET" && pwd)"
[[ "$TARGET" != "$KIT_DIR" ]] || die "refusing to install the kit into itself"

if [[ -d "$ADAPTER" ]]; then ADAPTER_DIR="$(cd "$ADAPTER" && pwd)"
else ADAPTER_DIR="$KIT_DIR/adapters/$ADAPTER"; fi
[[ -f "$ADAPTER_DIR/adapter.md" ]] || die "adapter.md not found in $ADAPTER_DIR"

# Validate inputs and optional capabilities before changing any project files.
command -v python3 >/dev/null || die "Python 3 is required"
[[ "$HARNESS" == "all" ]] && HARNESS="claude,codex,agy"
declare -a SKILL_ROOTS=()
IFS=',' read -ra HS <<< "$HARNESS"
[[ -n "$HARNESS" && "$HARNESS" != ,* && "$HARNESS" != *, && "$HARNESS" != *,,* ]] || die "empty harness"
for h in "${HS[@]}"; do
  case "$h" in
    claude) root=".claude/skills" ;;
    codex|agy|antigravity) root=".agents/skills" ;;
    *) die "unknown harness '$h' (use claude, codex, agy)" ;;
  esac
  [[ " ${SKILL_ROOTS[*]-} " == *" $root "* ]] || SKILL_ROOTS+=("$root")
done
if [[ $SPECKIT -eq 1 ]]; then
  command -v specify >/dev/null || die "--speckit requires specify on PATH"
  [[ -d "$TARGET/.specify" ]] || die "run specify init in the target before --speckit"
  for capability in extension preset workflow; do
    specify "$capability" add --help >/dev/null 2>&1 || die "specify lacks $capability add; upgrade to a compatible version"
  done
fi
# A malformed marker must never consume project instructions after an unmatched begin.
python3 - "$TARGET/AGENTS.md" "$TARGET/CLAUDE.md" "$MARK_BEGIN" "$MARK_END" <<'PY'
import pathlib, sys
for name in sys.argv[1:3]:
    p = pathlib.Path(name)
    if not p.exists():
        continue
    text = p.read_text()
    begin, end = sys.argv[3:]
    if begin not in text and end not in text:
        continue
    lines = text.splitlines()
    if (text.count(begin) != 1 or text.count(end) != 1 or
            begin not in lines or end not in lines or lines.index(begin) >= lines.index(end)):
        sys.exit(f"error: malformed kit markers in {p}; repair before installing")
PY

run() { if [[ $DRY -eq 1 ]]; then echo "  [dry-run] $*"; else "$@"; fi; }

# copy_one <src> <dest>: copy or symlink, respecting --force
copy_one() {
  local src="$1" dest="$2"
  if [[ -e "$dest" || -L "$dest" ]]; then
    if [[ $FORCE -eq 0 ]]; then say "skip (exists): ${dest#"$TARGET"/}"; return; fi
    run rm -rf "$dest"
  fi
  run mkdir -p "$(dirname "$dest")"
  if [[ $LINK -eq 1 ]]; then run ln -s "$src" "$dest"; else run cp -R "$src" "$dest"; fi
  say "installed: ${dest#"$TARGET"/}"
}

# upsert_block <file> <content-file>: insert or replace the marked kit block
upsert_block() {
  local file="$1" body="$2"
  if [[ $DRY -eq 1 ]]; then echo "  [dry-run] update kit block in ${file#"$TARGET"/}"; return; fi
  local tmp; tmp="$(mktemp "$TARGET/.aiek-kit.XXXXXX")"
  { echo "$MARK_BEGIN"; cat "$body"; echo "$MARK_END"; } > "$tmp.block"
  if [[ -f "$file" ]] && grep -qF "$MARK_BEGIN" "$file"; then
    awk -v b="$MARK_BEGIN" -v e="$MARK_END" -v blk="$tmp.block" '
      $0==b {while ((getline l < blk) > 0) print l; skip=1; next}
      $0==e {skip=0; next}
      !skip {print}' "$file" > "$tmp" && mv "$tmp" "$file"
  else
    [[ -f "$file" && -s "$file" ]] && printf '\n' >> "$file"
    cat "$tmp.block" >> "$file"
  fi
  rm -f "$tmp" "$tmp.block"
  say "updated kit block: ${file#"$TARGET"/}"
}

echo "AI Engineering Kit → $TARGET"

echo "1. Core policies and adapter (.aiek/)"
for f in "$KIT_DIR"/core/*.md; do
  [[ "$(basename "$f")" == "router.md" ]] && continue   # inserted into AGENTS.md instead
  copy_one "$f" "$TARGET/.aiek/core/$(basename "$f")"
done
copy_one "$KIT_DIR/NOTICE.md" "$TARGET/.aiek/NOTICE.md"
# The adapter is project-owned once installed: never overwritten without --force.
LINK_SAVED=$LINK; LINK=0
copy_one "$ADAPTER_DIR/adapter.md" "$TARGET/.aiek/adapter.md"
LINK=$LINK_SAVED

echo "2. Skills"
for root in "${SKILL_ROOTS[@]}"; do
  for s in "${SKILLS[@]}"; do copy_one "$KIT_DIR/skills/$s" "$TARGET/$root/$s"; done
done

echo "3. Agent instructions"
upsert_block "$TARGET/AGENTS.md" "$KIT_DIR/core/router.md"
if [[ ",$HARNESS," == *",claude,"* ]]; then
  CLAUDE_MD="$TARGET/CLAUDE.md"
  if [[ ! -f "$CLAUDE_MD" ]]; then
    if [[ $DRY -eq 1 ]]; then echo "  [dry-run] create CLAUDE.md importing AGENTS.md"
    else printf '@AGENTS.md\n' > "$CLAUDE_MD"; say "created: CLAUDE.md (imports AGENTS.md)"; fi
  elif ! grep -qE '^@AGENTS\.md' "$CLAUDE_MD"; then
    upsert_block "$CLAUDE_MD" "$KIT_DIR/core/router.md"
  else
    say "CLAUDE.md already imports AGENTS.md"
  fi
fi

echo "4. Spec Kit"
if [[ $SPECKIT -eq 0 ]]; then
  say "skipped (pass --speckit to register the extension, preset and workflows)"
else
  (
    cd "$TARGET"
    run specify extension add --dev "$KIT_DIR/speckit/extensions/aiek"
    run specify preset add --dev "$KIT_DIR/speckit/presets/aiek-core" --priority 10
    if [[ -f "$ADAPTER_DIR/speckit-preset/preset.yml" ]]; then
      run specify preset add --dev "$ADAPTER_DIR/speckit-preset" --priority 5
    fi
    run specify workflow add --dev "$KIT_DIR/speckit/workflows/aiek-normal"
    run specify workflow add --dev "$KIT_DIR/speckit/workflows/aiek-large"
    run specify workflow add --dev "$KIT_DIR/speckit/workflows/aiek-project"
  )
fi

echo "Done. Next: review .aiek/adapter.md and fill in project commands (see .aiek/core/adapter-contract.md)."
