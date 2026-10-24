#!/usr/bin/env bash
# Install the AI Engineering Kit into a target project.
#
# Usage: scripts/install.sh <target-dir> [options]    (run with --help for details)
#
# Options: --harness, --adapter, --profile, --only, --skip, --prefix, --speckit, --link,
#          --force, --dry-run. Defaults: all harnesses, adapter "default", all 15 skills
#          installed as "aiek-<name>" (pass --prefix none for bare names), no Spec Kit changes.
set -euo pipefail

KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# This full inventory is read by scripts/check.py; keep it first and keep the profile
# arrays below from being confused with it (they are named differently on purpose).
SKILLS=(exploring-idea shaping-feature intaking-ticket shaping-project executing-task
        shipping-infrastructure verifying-change accepting-change reviewing-change authoring-pr
        systematic-debugging using-worktrees parallel-development test-driven-development
        finishing-branch)
CORE_PROFILE=(executing-task verifying-change accepting-change reviewing-change
              systematic-debugging shipping-infrastructure using-worktrees parallel-development
              test-driven-development finishing-branch authoring-pr)
DISCOVERY_PROFILE=(exploring-idea shaping-feature intaking-ticket shaping-project)
SCRIPTS=(resolve_adapter.py verify.py worktree.py traceability.py _adapter_yaml.py)
MARK_BEGIN="<!-- ai-engineering-kit:begin -->"
MARK_END="<!-- ai-engineering-kit:end -->"

die() { echo "error: $*" >&2; exit 1; }
say() { echo "  $*"; }

usage() {
  cat <<'EOF'
AI Engineering Kit installer

Usage:
  scripts/install.sh <target-dir> [options]

Options:
  --harness <list>    Comma-separated harnesses (default: all)
                        claude       -> .claude/skills/
                        codex, agy   -> .agents/skills/
  --adapter <name|path>
                      Adapter under adapters/ or a path to an adapter directory
                      (default: default)
  --profile <name>    Skill set to install (default: full)
                        core       11 execution/verification/integration skills
                        discovery  4 discovery skills
                        full       all 15 skills
  --only <a,b>        Install only these skills; overrides --profile
  --skip <a,b>        Remove these skills from the selection (combines with --profile)
  --prefix <p|none>   Install skills as "<p>-<name>" so they cannot collide with the
                      project's own skills (default: aiek-). Applies to the directory,
                      the SKILL.md name and every skill reference in the installed
                      copies. "none" installs bare names. Not compatible with --link.
  --speckit           Also register the Spec Kit extension, preset and workflows
                      (needs `specify` on PATH and an initialized .specify/ in the target)
  --link              Symlink skills instead of copying them (for kit development)
  --force             Overwrite existing kit files, skills and helper scripts
  --dry-run           Print what would happen, write nothing, execute nothing
  -h, --help          Show this help

Always installed: core policies, the adapter, and the helper scripts
(.aiek/scripts/resolve_adapter.py, verify.py, worktree.py, traceability.py,
_adapter_yaml.py). Adapter references/ and scripts/ directories are copied to
.aiek/adapter/ when the adapter has them. .aiek/adapter.md is project-owned and is
never overwritten without --force.

Exit codes: 0 = success, 1 = invalid usage or target, 2 = internal failure.

Examples:
  scripts/install.sh ~/code/app --harness codex                    # aiek-* names, all skills
  scripts/install.sh ~/code/app --profile core --harness codex     # execution only
  scripts/install.sh ~/code/app --prefix none --harness codex      # bare names
  scripts/install.sh /tmp/aiek-fixture --profile discovery --dry-run
  scripts/install.sh /tmp/aiek-fixture --only executing-task,verifying-change
EOF
}

# contains <needle> <item...>
contains() {
  local needle="$1" item
  shift
  for item in "$@"; do
    [[ "$item" == "$needle" ]] && return 0
  done
  return 1
}

# parse_skill_list <value> <option-name>: validates and appends to PARSED_SKILLS.
PARSED_SKILLS=()
parse_skill_list() {
  local raw="$1" option="$2" item
  local -a items=()
  [[ -n "${raw// /}" ]] || die "--$option needs at least one skill name"
  IFS=',' read -ra items <<< "$raw"
  for item in "${items[@]}"; do
    item="${item#"${item%%[![:space:]]*}"}"
    item="${item%"${item##*[![:space:]]}"}"
    [[ -n "$item" ]] || die "--$option has an empty entry (got '$raw')"
    contains "$item" "${SKILLS[@]}" || die "unknown skill '$item' in --$option (valid: ${SKILLS[*]})"
    contains "$item" "${PARSED_SKILLS[@]-}" && die "duplicate skill '$item' in --$option"
    PARSED_SKILLS+=("$item")
  done
}

TARGET="" HARNESS="all" ADAPTER="default" PROFILE="full"
ONLY="" SKIP="" ONLY_SET=0 SKIP_SET=0 SPECKIT=0 LINK=0 FORCE=0 DRY=0
PREFIX="aiek-"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --harness) [[ $# -ge 2 ]] || die "--harness needs a value"; HARNESS="$2"; shift 2 ;;
    --adapter) [[ $# -ge 2 ]] || die "--adapter needs a value"; ADAPTER="$2"; shift 2 ;;
    --profile) [[ $# -ge 2 ]] || die "--profile needs a value"; PROFILE="$2"; shift 2 ;;
    --only) [[ $# -ge 2 ]] || die "--only needs a value"; ONLY="$2"; ONLY_SET=1; shift 2 ;;
    --skip) [[ $# -ge 2 ]] || die "--skip needs a value"; SKIP="$2"; SKIP_SET=1; shift 2 ;;
    --prefix) [[ $# -ge 2 ]] || die "--prefix needs a value (a name or 'none')"; PREFIX="$2"; PREFIX_SET=1; shift 2 ;;
    --speckit) SPECKIT=1; shift ;;
    --link) LINK=1; shift ;;
    --force) FORCE=1; shift ;;
    --dry-run) DRY=1; shift ;;
    -h|--help) usage; exit 0 ;;
    -*) die "unknown option $1 (see --help)" ;;
    *) [[ -z "$TARGET" ]] || die "only one target dir"; TARGET="$1"; shift ;;
  esac
done
[[ -n "$TARGET" ]] || die "usage: install.sh <target-dir> [options]  (see --help)"
[[ -d "$TARGET" ]] || die "target dir not found: $TARGET"
TARGET="$(cd "$TARGET" && pwd)"
[[ "$TARGET" != "$KIT_DIR" ]] || die "refusing to install the kit into itself"

# --prefix: normalize to "<ns>-" (or empty for none) and validate before touching anything.
PREFIX_RAW="$PREFIX"
case "$PREFIX" in
  none|"") PREFIX="" ;;
  *)
    PREFIX="$(printf '%s' "$PREFIX" | tr '[:upper:]' '[:lower:]')"
    PREFIX="${PREFIX%-}-"
    [[ "$PREFIX" =~ ^[a-z0-9]+(-[a-z0-9]+)*-$ ]] \
      || die "invalid --prefix '$PREFIX_RAW' (use lowercase letters, digits and hyphens, e.g. aiek-)"
    ;;
esac
if [[ -n "$PREFIX" && $LINK -eq 1 ]]; then
  die "--link cannot be combined with --prefix: a symlink cannot carry a renamed skill (use --prefix none)"
fi

# Validate the skill selection before touching anything.
case "$PROFILE" in
  core|discovery|full) ;;
  *) die "unknown profile '$PROFILE' (use core, discovery or full)" ;;
esac
ONLY_SKILLS=()
SKIP_SKILLS=()
if [[ $ONLY_SET -eq 1 ]]; then
  [[ -n "${ONLY// /}" ]] || die "--only needs at least one skill name"
  PARSED_SKILLS=()
  parse_skill_list "$ONLY" only
  ONLY_SKILLS=("${PARSED_SKILLS[@]}")
fi
if [[ $SKIP_SET -eq 1 ]]; then
  [[ -n "${SKIP// /}" ]] || die "--skip needs at least one skill name"
  PARSED_SKILLS=()
  parse_skill_list "$SKIP" skip
  SKIP_SKILLS=("${PARSED_SKILLS[@]}")
fi

SELECTED=()
for s in "${SKILLS[@]}"; do
  if [[ ${#ONLY_SKILLS[@]} -gt 0 ]]; then
    contains "$s" "${ONLY_SKILLS[@]}" || continue
  else
    case "$PROFILE" in
      core) contains "$s" "${CORE_PROFILE[@]}" || continue ;;
      discovery) contains "$s" "${DISCOVERY_PROFILE[@]}" || continue ;;
      full) ;;
    esac
  fi
  if [[ ${#SKIP_SKILLS[@]} -gt 0 ]] && contains "$s" "${SKIP_SKILLS[@]}"; then
    continue
  fi
  SELECTED+=("$s")
done
[[ ${#SELECTED[@]} -gt 0 ]] || die "no skills selected (profile '$PROFILE' with the given --only/--skip)"
if [[ -n "$PREFIX" ]]; then
  for s in "${SELECTED[@]}"; do
    [[ $(( ${#PREFIX} + ${#s} )) -le 64 ]] \
      || die "prefixed skill name '${PREFIX}${s}' exceeds the 64-character skill-name limit"
  done
fi

if [[ "$HARNESS" == "all" ]]; then HARNESS="claude,codex,agy"; fi
declare -a SKILL_ROOTS=()
IFS=',' read -ra HS <<< "$HARNESS"
[[ -n "$HARNESS" && "$HARNESS" != ,* && "$HARNESS" != *, && "$HARNESS" != *,,* ]] || die "empty harness"
for h in "${HS[@]}"; do
  case "$h" in
    claude) root=".claude/skills" ;;
    codex|agy|antigravity) root=".agents/skills" ;;
    *) die "unknown harness '$h' (use claude, codex or agy)" ;;
  esac
  [[ " ${SKILL_ROOTS[*]-} " == *" $root "* ]] || SKILL_ROOTS+=("$root")
done

if [[ -d "$ADAPTER" ]]; then ADAPTER_DIR="$(cd "$ADAPTER" && pwd)"
else ADAPTER_DIR="$KIT_DIR/adapters/$ADAPTER"; fi
[[ -f "$ADAPTER_DIR/adapter.md" ]] || die "adapter.md not found in $ADAPTER_DIR"

# Validate optional capabilities before changing any project files.
command -v python3 >/dev/null || die "Python 3 is required"
for script in "${SCRIPTS[@]}"; do
  [[ -f "$KIT_DIR/scripts/$script" ]] || die "missing helper script: scripts/$script"
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
  if [[ $DRY -eq 1 ]]; then
    say "would install: ${dest#"$TARGET"/}"
  else
    say "installed: ${dest#"$TARGET"/}"
  fi
}

# installed_name <skill>: directory / frontmatter name the skill gets under --prefix.
installed_name() { printf '%s%s' "$PREFIX" "$1"; }

# remap_skill_names <names-csv> <path...>: rewrite bare skill names to "<prefix><name>" in
# the installed copies only (directories are walked, single files are edited in place).
remap_skill_names() {
  [[ -n "$PREFIX" ]] || return 0
  local names_csv="$1"; shift
  [[ $# -gt 0 ]] || return 0
  local dry=0; [[ $DRY -eq 1 ]] && dry=1
  python3 - "$PREFIX" "$names_csv" "$dry" "$@" <<'PY'
import pathlib
import re
import sys

prefix, names_csv, dry, roots = sys.argv[1], sys.argv[2], sys.argv[3] == "1", sys.argv[4:]
names = [name for name in names_csv.split(",") if name]
pattern = re.compile(
    r"(?<![a-z0-9-])("
    + "|".join(re.escape(name) for name in sorted(names, key=len, reverse=True))
    + r")(?![a-z0-9-])")
suffixes = {".md", ".json", ".yml", ".yaml", ".txt"}

def rewrite(path):
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return False
    new = pattern.sub(lambda match: prefix + match.group(1), text)
    if new == text:
        return False
    if not dry:
        path.write_text(new, encoding="utf-8")
    return True

changed = 0
for root in roots:
    base = pathlib.Path(root)
    if base.is_file():
        candidates = [base]
    elif base.is_dir():
        candidates = sorted(p for p in base.rglob("*") if p.is_file() and p.suffix in suffixes)
    else:
        continue
    for path in candidates:
        if rewrite(path):
            changed += 1
if changed:
    verb = "[dry-run] would rewrite" if dry else "rewrote"
    print(f"  {verb} {changed} file(s) to {prefix}* names")
PY
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
if [[ $ONLY_SET -eq 1 ]]; then
  echo "   skills: --only $ONLY (${#SELECTED[@]} selected)"
else
  echo "   skills: profile $PROFILE (${#SELECTED[@]}/${#SKILLS[@]} selected)"
fi
[[ $SKIP_SET -eq 1 ]] && echo "   skipped: $SKIP"
if [[ $DRY -eq 1 ]]; then echo "   mode: dry-run (nothing will be written)"; fi

echo "1. Core policies and adapter (.aiek/)"
if [[ $DRY -eq 1 ]]; then say "would create .aiek/core/, .aiek/NOTICE.md and .aiek/adapter.md"; fi
for f in "$KIT_DIR"/core/*.md; do
  [[ "$(basename "$f")" == "router.md" ]] && continue   # inserted into AGENTS.md instead
  copy_one "$f" "$TARGET/.aiek/core/$(basename "$f")"
done
copy_one "$KIT_DIR/NOTICE.md" "$TARGET/.aiek/NOTICE.md"
# The adapter is project-owned once installed: never overwritten without --force.
LINK_SAVED=$LINK; LINK=0
copy_one "$ADAPTER_DIR/adapter.md" "$TARGET/.aiek/adapter.md"
if [[ -d "$ADAPTER_DIR/references" ]]; then
  copy_one "$ADAPTER_DIR/references" "$TARGET/.aiek/adapter/references"
  say "adapter references: $(ls "$ADAPTER_DIR/references" | tr '\n' ' ' | sed 's/ *$//')"
fi
if [[ -d "$ADAPTER_DIR/scripts" ]]; then
  copy_one "$ADAPTER_DIR/scripts" "$TARGET/.aiek/adapter/scripts"
  say "adapter scripts: $(ls "$ADAPTER_DIR/scripts" | tr '\n' ' ' | sed 's/ *$//')"
fi
LINK=$LINK_SAVED

echo "2. Helper scripts (.aiek/scripts/)"
for script in "${SCRIPTS[@]}"; do
  copy_one "$KIT_DIR/scripts/$script" "$TARGET/.aiek/scripts/$script"
done

echo "3. Skills (${#SELECTED[@]} selected)"
SKILL_NAMES_CSV="$(IFS=,; echo "${SKILLS[*]}")"  # all names: refs must stay stable across profiles
for root in "${SKILL_ROOTS[@]}"; do
  for s in "${SELECTED[@]}"; do
    copy_one "$KIT_DIR/skills/$s" "$TARGET/$root/$(installed_name "$s")"
  done
done
if [[ -n "$PREFIX" ]]; then
  REMAP_ROOTS=("$TARGET/.aiek")
  for root in "${SKILL_ROOTS[@]}"; do
    for s in "${SELECTED[@]}"; do REMAP_ROOTS+=("$TARGET/$root/$(installed_name "$s")"); done
  done
  remap_skill_names "$SKILL_NAMES_CSV" "${REMAP_ROOTS[@]}"
fi

echo "4. Agent instructions"
ROUTER_BODY="$KIT_DIR/core/router.md"
if [[ -n "$PREFIX" && $DRY -eq 0 ]]; then
  # The router text names skills, so the installed block must use the prefixed names too.
  ROUTER_BODY="$(mktemp "$TARGET/.aiek-router.XXXXXX")"
  trap 'rm -f "$ROUTER_BODY"' EXIT
  cp "$KIT_DIR/core/router.md" "$ROUTER_BODY"
  remap_skill_names "$SKILL_NAMES_CSV" "$ROUTER_BODY"
fi
upsert_block "$TARGET/AGENTS.md" "$ROUTER_BODY"
if [[ ",$HARNESS," == *",claude,"* ]]; then
  CLAUDE_MD="$TARGET/CLAUDE.md"
  if [[ ! -f "$CLAUDE_MD" ]]; then
    if [[ $DRY -eq 1 ]]; then echo "  [dry-run] create CLAUDE.md importing AGENTS.md"
    else printf '@AGENTS.md\n' > "$CLAUDE_MD"; say "created: CLAUDE.md (imports AGENTS.md)"; fi
  elif ! grep -qE '^@AGENTS\.md' "$CLAUDE_MD"; then
    upsert_block "$CLAUDE_MD" "$ROUTER_BODY"
  else
    say "CLAUDE.md already imports AGENTS.md"
  fi
fi

echo "5. Spec Kit"
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
if [[ $DRY -eq 1 ]]; then
  echo "Dry-run: nothing was written. Re-run without --dry-run to install."
fi
