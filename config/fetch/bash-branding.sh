# NovaOS fetch branding, sourced by the user's Bash login shell only.
# screenfetch has no XDG config for logos; use its supported -a option.
if command -v screenfetch >/dev/null 2>&1 && ! declare -F screenfetch >/dev/null 2>&1; then
  screenfetch() {
    command screenfetch -a /opt/novaos/app/config/fetch/screenfetch-logo.sh "$@"
  }
fi
# pfetch offers PF_SOURCE, which can replace its ASCII rendering without spoofing OS data.
if command -v pfetch >/dev/null 2>&1 && ! declare -F pfetch >/dev/null 2>&1; then
  pfetch() {
    PF_SOURCE=/opt/novaos/app/config/fetch/pfetch-source.sh command pfetch "$@"
  }
fi
