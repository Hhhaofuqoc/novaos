# NovaOS visual update v1

Small, checksummed update for existing NovaOS Mobile Lite installations.
Provides native NovaFetch/Fastfetch and optional experimental Plasma 6 X11.

Source and instructions: https://github.com/Hhhaofuqoc/novaos/blob/mobile-lite-0.1.0/docs/PLASMA-MOBILE.md

Save open files; run in Termux, outside Debian:

```bash
novaos-mobile stop
curl -fL --fail-early --proto '=https' --proto-redir '=https' --remote-name-all 'https://raw.githubusercontent.com/Hhhaofuqoc/novaos/novaos-visual-v1/{install-novaos-visual.sh,install-novaos-visual.sh.sha256}' && sha256sum -c install-novaos-visual.sh.sha256 && bash install-novaos-visual.sh --plasma
novaos-mobile start
```

For fetch without Plasma use `--fetch-only`. Verification without installing:
`bash install-novaos-visual.sh --download-only`.

Native Debian x86_64/X11 validation passed; Android ARM64/PRoot Plasma needs
validation on device. Package downloads are from signed Debian APT repositories.
The existing XFCE session remains available for rollback.

Source commit: e2cc745. No ISO/APK is included.
