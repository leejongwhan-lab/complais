# shellcheck shell=bash
# Safe KEY=VALUE loader (handles unquoted spaces). Never evals arbitrary shell.
# Usage:  # shellcheck source=scripts/_load_env.sh
#         source "$(dirname "$0")/_load_env.sh"
#         load_dotenv "$ROOT/.env"

load_dotenv() {
  local file="${1:-.env}"
  [[ -f "$file" ]] || return 0
  local line key val
  while IFS= read -r line || [[ -n "$line" ]]; do
    # trim CR
    line="${line%$'\r'}"
    # skip blank / comment
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
    # only KEY=VALUE
    if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
      key="${BASH_REMATCH[1]}"
      val="${BASH_REMATCH[2]}"
      # strip surrounding single/double quotes
      if [[ "$val" =~ ^\"(.*)\"$ ]]; then
        val="${BASH_REMATCH[1]}"
      elif [[ "$val" =~ ^\'(.*)\'$ ]]; then
        val="${BASH_REMATCH[1]}"
      fi
      export "$key=$val"
    fi
  done < "$file"
}
