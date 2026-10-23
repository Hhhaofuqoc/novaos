# Sourced by pfetch via PF_SOURCE. Replaces only its logo-rendering function.
# System info still comes from the original pfetch; /etc/os-release remains Debian.
get_ascii() {
    ascii=$(cat /opt/novaos/app/assets/logos/nova-ascii.txt)
    ascii_height=9
    ascii_width=24
    {
        esc_p SGR 35
        printf '%s\n' "$ascii"
        esc_p SGR 0
        esc_p CUU "$ascii_height"
    } >&6
}
