# NovaOS Full 1.0 — amd64 Live ISO

This is a **real Linux Live ISO** for x86_64 VMs, built on **Debian 13 Trixie** with its own Linux kernel, systemd, X.Org, LightDM, Openbox, and NovaShell (custom GTK3 panel, app menu, dock, system widgets). This edition does **not** use Termux or PRoot. The live session is ephemeral; installed files are read-only on the ISO unless a separate persistence/installation method is configured.

## Included

- Bootable BIOS/UEFI-compatible hybrid ISO (Debian `live-build`).
- NovaShell GTK3 user interface and original NovaOS wallpaper and SVG icons.
- LightDM automatic login (`nova` live user) to the custom `novaos` X session.
- Firefox ESR, LibreOffice Writer/Calc, Geany, VLC/MPV, PCManFM, LXTerminal, Fastfetch/NovaFetch.
- NetworkManager, audio control, user sessions, desktop logs, QEMU/Spice guest integrations.

## Build in GitHub Actions (no PC)

Visit **Actions → NovaOS Full ISO (amd64) → Run workflow** on GitHub. The workflow uses Debian 13 `live-build` inside a privileged Docker container on an ephemeral GitHub-hosted Ubuntu runner. On success, download the `NovaOS-v1.0-Full-amd64` Actions artifact, unzip it, and attach `NovaOS-v1.0-Full-amd64.iso` to a VM as optical media.

The workflow also runs a headless QEMU boot smoke and uploads a **real** framebuffer screenshot as a separate artifact. A framebuffer capture verifies execution inside QEMU, not necessarily that the GTK UI displayed correctly — examine the screenshot.

If the build fails, review the live-build logs in the job. A file called `.iso` is **not** created or published by the workflow unless `live-build` completes.

## Building manually on Debian 13 x86_64

From the repository root, run `sudo bash iso/full/build.sh` and ensure you have plenty of free disk space (we recommend 25 GiB for intermediate files). The ISO appears in `dist/` only on successful completion.

## VM testing locally

Boot `dist/NovaOS-v1.0-Full-amd64.iso` in VirtualBox, QEMU, or another x86_64 VM with at least 3 GiB RAM. For a headless test where QEMU and socat are installed, run `bash iso/full/boot-smoke.sh`. GitHub Actions runners are temporary and do not expose a permanent interactive desktop to Android browsers.

## Notes

- This Live ISO is **bootable but not a full disk installer**. To install persistently in a VM disk, a dedicated installation mechanism must be built and tested.
- No XFCE, GNOME Shell or KDE Plasma installed. LightDM and Openbox are lightweight dependencies, not a prepackaged desktop environment.
- `nova-info` distinguishes the Linux VM kernel from the Android kernel shown by the Termux edition.
- The Full edition includes more applications than the mobile Lite edition and may exceed the Android space budget; its build runs in CI, not on your phone.
