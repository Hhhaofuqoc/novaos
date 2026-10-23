# NovaOS Mobile Lite downloads

Public, checksum-verified installation files for NovaOS Mobile Lite 0.1.0 alpha.

Source and Android guide: https://github.com/Hhhaofuqoc/novaos/tree/mobile-lite-0.1.0

Run in Termux, with the official Termux:X11 Android app installed:

```bash
curl -fL --fail-early --proto '=https' --proto-redir '=https' --remote-name-all 'https://raw.githubusercontent.com/Hhhaofuqoc/novaos/mobile-lite-downloads-v0.1.0/{install-novaos.sh,install-novaos.sh.sha256}' && sha256sum -c install-novaos.sh.sha256 && bash install-novaos.sh
```

Then: `novaos-mobile start`.

The installer checks the script, the exact archive hash, and its internal source manifest. The default installation stays inside Termux and uses no Android root. Physical Android installation, touch and audio remain device validation steps; see the source validation guide. For download verification without installation, pass `--download-only` to the downloaded script.
