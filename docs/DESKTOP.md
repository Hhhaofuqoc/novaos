# NovaOS Desktop 0.1.0 alpha

A edição Plasma usa Debian 13 (trixie), kernel Linux, systemd, APT, Xorg e
KDE Plasma 6. O tema, dock, widgets e aplicativos são instalados como arquivos e pacotes
Linux reais. A instalação em Debian existente é o caminho mais curto para testar
esta versão. A configuração `plasma` adiciona KDE Plasma; a integração visual
Night Room já está implementada e foi testada nativamente com X11. A edição Lite
com XFCE continua disponível como alternativa.

## Gerar no GitHub

O workflow [NovaOS Plasma ISO and SHA256](https://github.com/Hhhaofuqoc/novaos/actions/workflows/novaos-plasma-release.yml)
na branch `main` usa uma revisão explícita da implementação Plasma da branch
`mobile-lite-0.1.0`. Ele compila em Debian 13, verifica o hash, faz boot BIOS e
UEFI da ISO real em QEMU e publica uma prerelease após esses testes passarem.
O workflow foi acrescentado sem substituir os outros arquivos da branch `main`.

Arquivos de saída: `novaos-0.1.0-plasma-amd64.iso` e
`novaos-0.1.0-plasma-amd64.iso.sha256`. As execuções e seus artefatos mostram o
resultado real de cada tentativa; a existência da automação não comprova sucesso.
Se o arquivo exceder o limite de 2 GiB de uma release, a página de release aponta
para o artefato GitHub Actions contendo a ISO inteira e seu hash.

## Instalar os pacotes em Debian 13

Use os artefatos gerados localmente por `bash scripts/release.sh`, ou uma release
publicada pelo mantenedor. Confira `SHA256SUMS` comparando o arquivo de hashes com
uma fonte confiável. Os hashes detectam corrupção, mas não substituem assinatura
ou verificação da origem. Os downloads Desktop publicados ficam nas Releases
e nos artefatos da automação do repositório.

```sh
cd dist
sha256sum -c SHA256SUMS
sudo apt install ./novaos-desktop_0.1.0_all.deb ./novaos-music_0.1.0_all.deb
```

O pacote declara dependências Python/GTK/GStreamer e recomenda a sessão XFCE.
Caso APT esteja configurado para não instalar recomendações, instale a lista
`desktop/packages-lite.txt`. O pacote de aplicativos não instala sozinho kernel,
bootloader ou gerenciador de login: o Debian existente fornece esses componentes.

Saia da sessão e selecione **Xfce Session** na tela de login. `novaos session-init`
aplica a configuração inicial do usuário. Em uma sessão existente, a integração
preserva arquivos pessoais; consulte `docs/VISUAL.md` sobre backups do tema.

## Construir uma ISO real

É necessário um host/VM Debian 13 amd64 descartável, acesso a repositórios Debian,
root para mounts/chroot, aproximadamente 15–25 GB livres e paciência. O tamanho,
RAM necessária para build e duração variam. Build dentro de PRoot não é suportado.

```sh
sudo apt update
sudo apt install live-build debootstrap xorriso squashfs-tools dosfstools mtools \
  grub-pc-bin grub-efi-amd64-bin isolinux syslinux-common dpkg-dev \
  python3 python3-numpy ffmpeg ca-certificates
python3 music/generate.py
sudo bash desktop/build-iso.sh --edition lite
```

O script chama `lb config`, inclui os `.deb` locais, faz `lb build` e só copia uma
ISO se o live-build produzir `live-image-amd64.hybrid.iso` não vazia. O resultado
é `dist/novaos-0.1.0-lite-amd64.iso`, acompanhado de hash e log. Não existe um
arquivo `.iso` de demonstração. `--configure-only` prepara a configuração e os
pacotes, sem debootstrap/build; isso não prova que a ISO inicializa.

`--edition plasma` seleciona a edição experimental mais pesada, SDDM e KDE X11.
Use diretórios diferentes para cada edição. Para refazer um build existente,
execute `sudo lb clean` dentro do workdir ou escolha um diretório vazio com
`--workdir`. O script nunca apaga um diretório arbitrário automaticamente.

A receita solicita BIOS/UEFI por syslinux e grub-efi e usa componentes Debian para
boot. Secure Boot não é declarado validado. Suporte a Wi-Fi/GPU depende do kernel,
firmware distribuível Debian e hardware; o repositório `non-free-firmware` é
habilitado na ISO. Firmware é instalado no sistema Live, sem duplicar todos os
pacotes de firmware na área externa do instalador. Nenhum benchmark de 3 GB está
implícito na receita. O instalador e Secure Boot precisam de validação separada.

## Modo Live, instalação e persistência

O menu de boot gerado pelo Debian live-build inclui a sessão Live e o instalador
Debian, quando `--debian-installer live` está disponível para a distribuição.
O instalador pode ter interface gráfica; **o particionamento modifica discos** e
a confirmação deve ser feita conscientemente pelo usuário. O projeto não tem um
instalador gráfico NovaOS próprio. `--no-debian-installer` omite esse componente.

O Live usa usuário `nova`; a credencial Live padrão do Debian live-config é
`live`. Isso não define a senha de uma instalação permanente: crie seu usuário e
senha no instalador. Não use a sessão Live como serviço exposto à rede.

Sem mídia persistente, mudanças feitas na sessão Live são temporárias. A receita
inclui `persistence` na linha de boot. Para persistência, use uma partição ext4
**separada**, com label `persistence`, e um arquivo `/persistence.conf` na raiz
contendo `/ union`. A criação/formatação dessa partição apaga dados; ela deve ser
feita manualmente no dispositivo correto. A ISO não particiona discos por conta
própria. Consulte o [manual Debian Live](https://live-team.pages.debian.net/live-manual/html/live-manual/customizing-run-time-behaviours.en.html#556).

## Teste de boot reproduzível

Com QEMU instalado, inicie primeiro sem expor um disco real:

```sh
qemu-system-x86_64 -m 3072 -smp 2 \
  -cdrom dist/novaos-0.1.0-lite-amd64.iso -boot d -nic user,model=virtio-net-pci
```

Para UEFI, adicione a configuração OVMF apropriada da distribuição. Para testar o
instalador, crie um disco qcow2 descartável com `qemu-img create -f qcow2 teste.qcow2
20G` e passe `-drive file=teste.qcow2,format=qcow2,if=virtio`. Confirme boot, login,
abertura de terminal/arquivos/NovaMusic, áudio, rede, persistência após reboot e
instalação no disco virtual. Registre ISO hash, BIOS/UEFI, CPU/RAM, data e resultados
em `docs/VALIDATION.md`. A existência da receita ou dos jobs CI não prova boot.

A automação usa `tests/integration/iso_boot.py` com 4 GiB de RAM, QMP e QEMU Guest
Agent para verificar a sessão Live, KWin X11, quatro desktops, tema, widgets e
abertura de Konsole/Dolphin. Capturas vêm do framebuffer real do QEMU. Nenhum
disco físico é anexado. O agente QEMU usa um canal virtio local; não abre porta
de rede e seu serviço depende do dispositivo virtual correspondente.

## Atualização e remoção

Atualizações Debian: Synaptic/NovaUpdater executam ações reais do sistema. Revise
as alterações do APT antes de confirmar. Atualizações do código NovaOS: gere nova
versão do pacote e instale com `apt install ./pacote.deb`. O dpkg preserva arquivos
marcados como configuração e os dados do usuário ficam no diretório pessoal.

```sh
sudo apt remove novaos-desktop novaos-music
```

A remoção não apaga notas, biblioteca musical ou configurações do usuário. Para
restaurar aparência anterior, use o backup descrito em `docs/VISUAL.md`. Não rode
`apt autoremove` sem revisar a lista de pacotes.
