#!/usr/bin/env bash
# Initialize an empty project from a BRD, then install the kit and Spec Kit layer.
set -euo pipefail

KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

die() { echo "error: $*" >&2; exit 1; }

TARGET="" BRD="" INTEGRATION=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --brd) [[ $# -ge 2 ]] || die "--brd needs a file"; BRD="$2"; shift 2 ;;
    --integration) [[ $# -ge 2 ]] || die "--integration needs a value"; INTEGRATION="$2"; shift 2 ;;
    -h|--help)
      echo "usage: init-project.sh <empty-target-dir> --brd <file> --integration <claude|codex|agy>"
      exit 0 ;;
    -*) die "unknown option $1" ;;
    *) [[ -z "$TARGET" ]] || die "only one target directory is allowed"; TARGET="$1"; shift ;;
  esac
done
[[ -n "$TARGET" && -n "$BRD" && -n "$INTEGRATION" ]] || die "usage: init-project.sh <empty-target-dir> --brd <file> --integration <claude|codex|agy>"
case "$INTEGRATION" in claude|codex|agy) ;; *) die "unsupported integration: $INTEGRATION" ;; esac
[[ -f "$BRD" && -r "$BRD" ]] || die "BRD must be a readable file: $BRD"
BRD="$(cd "$(dirname "$BRD")" && pwd)/$(basename "$BRD")"
[[ ! -L "$TARGET" ]] || die "target must not be a symlink"
if [[ -e "$TARGET" ]]; then
  [[ -d "$TARGET" ]] || die "target is not a directory: $TARGET"
  [[ -z "$(ls -A "$TARGET")" ]] || die "target must be empty: $TARGET"
fi
command -v specify >/dev/null || die "specify is required on PATH"
for capability in extension preset workflow; do
  specify "$capability" add --help >/dev/null 2>&1 || die "specify lacks $capability add"
done

mkdir -p "$TARGET"
TARGET="$(cd "$TARGET" && pwd)"
[[ "$TARGET" != "$KIT_DIR" ]] || die "refusing to initialize the kit into itself"

(
  cd "$TARGET"
  specify init --here --integration "$INTEGRATION" --ignore-agent-tools --non-interactive
)
bash "$KIT_DIR/scripts/install.sh" "$TARGET" --harness "$INTEGRATION" --speckit
mkdir -p "$TARGET/docs/inputs"
cp "$BRD" "$TARGET/docs/inputs/$(basename "$BRD")"
echo "Project ready: $TARGET"
echo "BRD: docs/inputs/$(basename "$BRD")"
echo "Next: run the shaping-project skill, then Spec Kit constitution and speckit.aiek.project-roadmap."
