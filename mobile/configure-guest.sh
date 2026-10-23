#!/bin/bash
# Invoked as the emulated root of the Debian PRoot, never on Android root.
set -euo pipefail
ROOT=/opt/novaos-source
[[ -f /etc/novaos-mobile-owner && -f $ROOT/desktop/packages-lite.txt ]] || {
  echo 'Execute via mobile/install-termux.sh.' >&2; exit 1;
}
. /etc/os-release
[[ ${ID:-} == debian && ${VERSION_CODENAME:-} == trixie ]] || {
  echo 'O rootfs deve ser Debian 13 trixie. Atualização entre versões exige migração manual.' >&2; exit 1;
}
export DEBIAN_FRONTEND=noninteractive
# PRoot has no init manager. Suppress service starts during apt operations,
# and restore any pre-existing policy file after completion/failure.
POLICY_SAVED=''
if [[ -e /usr/sbin/policy-rc.d ]]; then
  POLICY_SAVED=$(mktemp /tmp/novaos-policy.XXXXXX)
  cp -a /usr/sbin/policy-rc.d "$POLICY_SAVED"
fi
restore_policy() {
  if [[ -n $POLICY_SAVED ]]; then
    cp -a "$POLICY_SAVED" /usr/sbin/policy-rc.d
    rm -f "$POLICY_SAVED"
  else
    rm -f /usr/sbin/policy-rc.d
  fi
}
trap restore_policy EXIT
printf '#!/bin/sh\nexit 101\n' > /usr/sbin/policy-rc.d
chmod 755 /usr/sbin/policy-rc.d
apt-get update
mapfile -t PACKAGES < <(sed -e 's/#.*//' -e '/^[[:space:]]*$/d' "$ROOT/desktop/packages-lite.txt")
apt-get install -y --no-install-recommends "${PACKAGES[@]}" sudo dbus-x11 procps xauth ca-certificates
if ! id nova >/dev/null 2>&1; then
  useradd --create-home --shell /bin/bash nova
  passwd --lock nova
fi
bash "$ROOT/installers/install-system.sh"
install -d -m 755 /usr/local/libexec
install -m 755 "$ROOT/mobile/guest-session.sh" /usr/local/libexec/novaos-mobile-session
# Only the validated helper is authorized. Android itself remains unprivileged.
printf 'nova ALL=(root) NOPASSWD: /usr/lib/novaos/apt-helper\n' > /etc/sudoers.d/novaos-packages
chmod 440 /etc/sudoers.d/novaos-packages
visudo --check --file /etc/sudoers.d/novaos-packages
printf 'mobile-lite\n' > /etc/novaos-edition
install -d -o nova -g nova -m 700 /home/nova/.config/novaos
if [[ ! -f /home/nova/.config/novaos/mobile-initialized ]]; then
  # Actual xfconf/panel initialization occurs in a running D-Bus session.
  touch /home/nova/.config/novaos/mobile-initialized
  chown nova:nova /home/nova/.config/novaos/mobile-initialized
fi
apt-get clean
printf 'NovaOS Mobile Lite configurado em Debian %s.\n' "$VERSION_ID"
