# NovaOS

**Your universe. Your system.** · Synthwave Linux Experience

NovaOS 0.1.0-alpha é uma primeira implementação Linux real, com prioridade no
**Android sem root: Termux → Debian 13 em PRoot → Termux:X11 → XFCE**.
Não é uma ROM Android, VM, nem substitui o kernel do celular. Não exige PC.

## Começar no Android

Instalação automática no Termux, depois de instalar os aplicativos Android
Termux e Termux:X11 oficiais:

```bash
curl -fL --fail-early --proto '=https' --proto-redir '=https' --remote-name-all 'https://github.com/Hhhaofuqoc/novaos/releases/download/v0.1.0-mobile-lite/{install-novaos.sh,install-novaos.sh.sha256}' && sha256sum -c install-novaos.sh.sha256 && bash install-novaos.sh
novaos-mobile start
```

O script verifica o pacote completo por SHA-256 antes de extrair e instalar.
Os [artefatos desta edição](https://github.com/Hhhaofuqoc/novaos/releases/tag/v0.1.0-mobile-lite)
e a branch `mobile-lite-0.1.0` contêm a implementação descrita aqui.

Leia [o guia de instalação Mobile](docs/MOBILE.md). O instalador exige ARM64 ou
x86_64, Termux oficial, Termux:X11 e pelo menos 6 GiB livres durante a instalação.
Com os aproximadamente 15 GB disponíveis informados para este projeto, a edição
Lite é a opção inicial; o uso final depende dos pacotes e arquivos adicionados.
A primeira instalação baixa dependências; arquivos, notas, editor e músicas
funcionam localmente depois. Navegação e novas instalações precisam de rede.

No projeto extraído em uma pasta privada do Termux:

```bash
bash mobile/install-termux.sh
novaos-mobile start
```

O arquivo de release contém `SHA256SUMS`. Para desenvolver a partir de um checkout
local revisado, use `bash mobile/install-termux.sh --development`.
Não use `curl | bash`. O guia explica verificação, transferência pelo próprio
Android, atualização, encerramento, backup, restauração e desinstalação.

## Implementado

- Sessão XFCE real: janelas, desktops, dock, menu, relógio, notificações e volume.
- Tema neon escuro e claro, ícones e wallpapers originais desktop/mobile.
- Perfis Lite/Balanced/Ultra; início Lite no Android, economia manual e redução
  de efeitos com pressão de memória/bateria quando essas leituras estão acessíveis.
- NovaFiles/Thunar, NovaTerminal/XFCE Terminal, Firefox ESR, NovaEditor/Mousepad.
- NovaSettings, NovaMonitor, NovaNotes e NovaWelcome em Python/GTK3.
- NovaStore e NovaUpdater sobre APT, com confirmação em terminal e helper limitado.
- NovaMusic GTK/GStreamer: biblioteca local, playlist, controles, repeat/shuffle,
  mini-player e Ambient Desktop. Doze faixas originais FLAC, 72 s cada.
- Instaladores locais, pacotes `.deb`, arquivos Mobile, checksums, testes e CI.
- Receita real de ISO Debian live x86_64; não há ISO ou APK NovaOS compilado nesta entrega.

## Verificação e limites

Veja [VALIDATION.md](docs/VALIDATION.md) para resultados executados e comandos.
Os testes gráficos usam Linux x86_64 com Xvfb e um gerenciador XFWM real;
áudio é decodificado até EOS, com saída virtual no teste. **Android físico,
touchscreen, saída física de áudio e boot de ISO ainda exigem validação.**
Não há garantia de consumo de RAM ou velocidade no seu celular.

Esta alpha não implementa wallpaper animado, visualizador de áudio, blur, APK
próprio ou integração visual completa de Plasma. Não há screenshots de referência
disponíveis no projeto; a arte segue a descrição fornecida. Wi-Fi, Bluetooth,
permissões e suspensão continuam geridos pelo Android na edição Mobile.

## Desenvolvimento

```bash
python3 -m unittest discover -s tests -v
bash scripts/build-deb.sh
bash scripts/release.sh
# Debian com dependências gráficas instaladas:
bash tests/integration/run.sh
```

Diretórios: `desktop/`, `mobile/`, `themes/`, `wallpapers/`, `music/`,
`applications/`, `installers/`, `scripts/`, `tests/`, `docs/`, `.github/workflows/`.

Documentação: [arquitetura](docs/ARCHITECTURE.md), [Mobile](docs/MOBILE.md),
[Desktop](docs/DESKTOP.md), [build](docs/BUILD.md), [música](docs/MUSIC.md),
[visual](docs/VISUAL.md), [validação](docs/VALIDATION.md).

Código e arte: MIT; gravações originais: CC0. Dependências mantêm suas licenças.
