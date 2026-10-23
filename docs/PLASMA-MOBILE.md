# Plasma experimental e NovaFetch

Atualização para um **NovaOS Mobile já instalado**. O XFCE permanece disponível.
O Plasma usa o mesmo Debian e os mesmos arquivos, com KWin X11, Konsole, Dolphin,
painéis flutuantes, dock, tema roxo/ciano e wallpaper original NovaOS.
O atualizador v2 aplica o [visual Night Room](NIGHT-ROOM.md) inspirado na imagem
fornecida: quarto noturno, barra superior escura e widgets à direita.
Continua sendo PRoot no Android, sem root e sem systemd de usuário.

## Instalar pelo Termux

Salve os arquivos abertos. Execute **fora do Debian**, no Termux:

```bash
novaos-mobile stop
curl -fL --fail-early --proto '=https' --proto-redir '=https' --remote-name-all 'https://raw.githubusercontent.com/Hhhaofuqoc/novaos/novaos-visual-v2/{install-novaos-visual.sh,install-novaos-visual.sh.sha256}' && sha256sum -c install-novaos-visual.sh.sha256 && bash install-novaos-visual.sh --plasma
novaos-mobile start
```

O atualizador baixa um arquivo pequeno de código/temas; o APT baixa separadamente
as dependências. Exige pelo menos 3 GiB livres como margem de instalação.
No teste Debian x86_64, o conjunto principal baixou cerca de 260 MB e acrescentou
920 MB. O total em ARM64 pode diferir. Não reinstala músicas nem apaga documentos.
Os arquivos e o instalador são verificados com SHA-256 antes da execução.
Checksums detectam corrupção; a confiança na origem GitHub continua necessária.

Para instalar apenas o fetch, execute o mesmo comando curl substituindo o último
argumento `--plasma` por `--fetch-only`. Não precisa instalar Plasma para usar o fetch.

## Usar o fetch

No terminal **dentro do NovaOS**:

```bash
novafetch
novafetch --wide
novafetch --compact
fastfetch
novaos fetch
```

`novafetch` escolhe o formato pela largura do terminal. O comando `fastfetch`
também recebe configuração NovaOS, compacta por padrão. Há uma identidade própria:
monograma N roxo/azul e blocos de sistema/desktop/hardware.
Não usa logo ou arquivos do CachyOS.

As leituras são do Fastfetch instalado pelo Debian. A base continua identificada
como Debian; o kernel pertence ao Android em PRoot. RAM representa o host quando
acessível, não o consumo exclusivo do NovaOS. GPU/bateria podem ser omitidas quando
Android bloqueia essas informações. Nenhum módulo consulta IP público ou geolocalização.

Personalização: `~/.config/fastfetch/config.jsonc`. A atualização guarda os arquivos
anteriores em `~/.config/novaos/backups/fetch-*`. O wrapper `novafetch` usa os modelos
em `/usr/share/novaos/fetch/`; alterações no config pessoal afetam `fastfetch`.

## Voltar ao XFCE

No Termux, após salvar os arquivos:

```bash
novaos-mobile stop
novaos-mobile desktop xfce
novaos-mobile start
```

Para retornar ao Plasma, use `novaos-mobile desktop plasma` com a sessão parada.
O desktop selecionado fica em `~/.local/state/novaos-mobile/preferences.json`.
Arquivos e preferências XFCE permanecem no mesmo ambiente.

## Desempenho e limites

Plasma é uma opção experimental de maior consumo. Inicia com renderização Qt
por software; o perfil Lite desliga composição e blur. Balanced/Ultra podem
custar mais CPU, especialmente sem aceleração no PRoot. O Android continua
responsável por Wi-Fi, Bluetooth, suspensão e permissões.

Não instalamos SDDM, NetworkManager ou um serviço de energia para controlar o Android.
O bloqueio automático do Plasma é desativado: a conta Linux não substitui a tela
de bloqueio Android. Não use o bloqueio manual KDE para proteger o aparelho.

Validação executada: 80 testes unitários/lifecycle, shellcheck, Fastfetch 2.40.4
real e boot Plasma 6.3.6 em Debian x86_64/Xvfb. O teste verifica KWin, configuração
dos painéis/wallpaper e abre Konsole com NovaFetch. A captura é de uma sessão real.
Na integração inicial v1, uma amostra de 4 segundos mediu cerca de 0,25% de um núcleo para os processos
monitorados no ambiente cloud. Isso não prevê desempenho no Moto G34. RSS por
processo pode contar bibliotecas compartilhadas mais de uma vez.

Limites observados nesse ambiente sem serviços de sistema: avisos UDisks2 e
monitor de mídia PipeWire indisponível. O áudio Mobile continua pelo PulseAudio
privado existente; áudio físico, toque, orientação e estabilidade ARM64/PRoot
precisam de teste no aparelho. Consulte `novaos-mobile doctor` e o log indicado
pelo launcher se a sessão não abrir. Voltar ao XFCE não exige desinstalação.

Para reproduzir o teste gráfico em Debian com dependências instaladas:

```bash
# Instalação existente NovaOS de teste, usuário nova, Plasma instalado:
runuser -u nova -- env NOVAOS_PLASMA_SCREENSHOT=/tmp/plasma.png xvfb-run -a -s '-screen 0 1600x900x24' /usr/bin/python3 tests/integration/plasma_boot.py
```

O teste inicia e encerra sua própria sessão gráfica e grava
`/tmp/novaos-plasma-report.json`. Nunca execute contra uma sessão gráfica pessoal.
