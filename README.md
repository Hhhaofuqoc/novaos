# NovaOS Night Room visual update v2

Native KDE Plasma X11, original nighttime bedroom/city wallpaper, purple/blue
NovaFetch, four desktops, dark panels and native GTK system/network/music cards.
This is an update for an existing NovaOS Mobile installation, not a ROM or APK.

Source commit: 5807718 on the mobile-lite-0.1.0 branch.
Guide and real screenshots:
https://github.com/Hhhaofuqoc/novaos/blob/mobile-lite-0.1.0/docs/NIGHT-ROOM.md

Save open files and run in Termux, outside Debian:

```bash
novaos-mobile stop
curl -fL --fail-early --proto '=https' --proto-redir '=https' --remote-name-all 'https://raw.githubusercontent.com/Hhhaofuqoc/novaos/novaos-visual-v2/{install-novaos-visual.sh,install-novaos-visual.sh.sha256}' && sha256sum -c install-novaos-visual.sh.sha256 && bash install-novaos-visual.sh --plasma && novaos-mobile start
```

For fetch only use --fetch-only. To verify the complete download without installing:
`bash install-novaos-visual.sh --download-only`.

80 unit/lifecycle tests, 21 native GTK/GStreamer checks and native Plasma sessions
at 1600x900 and 1280x720 passed. Android/ARM64/PRoot, touch and hardware audio still
need on-device validation. No access to the user's phone was used.

The archive is approximately 2.2 MB. KDE dependencies come separately from signed
Debian APT repositories. The existing XFCE session and documents remain available.
