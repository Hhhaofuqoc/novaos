# Validação executada — NovaOS 0.1.0-alpha

Data: 23 de outubro de 2026. Ambiente cloud Linux x86_64, Debian 13, Xvfb e
XFWM reais. **Nenhum teste foi executado em Android físico ou em PRoot real.**
A entrega tem prioridade Mobile Lite; compatibilidade do Moto G34 precisa da
verificação no próprio aparelho, conforme o roteiro no fim deste documento.

Atualização visual: 77 testes unitários/lifecycle passaram; shellcheck dos novos
scripts e build real dos pacotes Debian passaram. Fastfetch 2.40.4 executou os
dois formatos. Plasma 6.3.6 iniciou sob X11/Xvfb com KWin real, tema, painéis,
wallpaper e Konsole executando NovaFetch. Evidências:
[relatório](validation/plasma-report.json), [captura](validation/plasma-desktop.png)
e [guia experimental](PLASMA-MOBILE.md). São resultados nativos x86_64; não são
medidas do Moto G34. O relatório preserva avisos de serviços indisponíveis.
O atualizador público `novaos-visual-v1` também foi baixado via HTTPS: checksum
do bootstrap, checksum fixado do arquivo e os 14 arquivos internos passaram
pela verificação real com `--download-only`. Isso não executa a instalação Android.

## Resultados

| Área | Executado | Resultado / limite |
| --- | --- | --- |
| Unidade e lifecycle | 53 testes Python | Passaram; inclui processos reais com serviços Android substituídos nos testes do supervisor |
| Instalação limpa Debian | `mobile/configure-guest.sh` no rootfs oficial fixado, container novo | Dependências assinadas, usuário nova, sudoers limitado e aplicativos instalados; não valida PRoot |
| Dependências | 71 nomes de pacotes | Todos resolvidos nos índices Debian; inclui listas Desktop/Plasma |
| Inicialização do guest | script Mobile instalado, usuário nova, Xvfb | XFCE iniciou, perfil `lite dark`, um agente de adaptação |
| Sessão gráfica | 21 verificações reais | Sete apps, tema/wallpaper/painel, mover/redimensionar/maximizar/minimizar, desktops e encerramento |
| Persistência e falha | NovaNotes + escrita por teclado X11 e SIGKILL | Conteúdo salvo reapareceu após reinício; instalação/reinstalação preservou sentinelas |
| NovaMusic | 18 verificações GTK/GStreamer | Play, pause, seek, volume, teclado, mini, shuffle/repeat, persistência, EOS e janela pequena com rolagem |
| Álbum | 12 arquivos completos | FFmpeg e GStreamer decodificaram até EOS: 72 s cada, 864 s total; saída virtual |
| Temas | GTK real, claro/escuro | Cores ativas e sem foco validadas; CSS sem erros; wallpaper e dock inspecionados na captura |
| Operação offline | Container `--network none` | Inicialização guest, testes GUI, música e contraste passaram sem acesso à rede |
| Administração APT | sudo + helper instalado em terminal real | Confirmação SIM e instalação de pacote já presente passaram; não houve download/upgrade nesta checagem offline |
| Empacotamento | dpkg-deb + extração e inspeção | Pacotes reais e arquivos de fontes; não é teste de boot de ISO |
| Backup/restauração/remoção | Validação de arquivo, checksum e confirmações | Testes automatizados; comandos proot-distro de backup/restore/remove ainda precisam do teste no Android |

A instalação limpa declarou **233 MB de downloads / 969 MB adicionais** para
as dependências principais x86_64. Não inclui a rootfs base, gravações, backups
ou futuras instalações. A edição Android baixa pacotes ARM64, cujos tamanhos
podem variar. O instalador exige 6 GiB livres como margem preventiva; isso não
é uma medição do espaço final nem promessa de desempenho.

## Métricas observadas

Na última amostra, 12 processos rastreados, com sete apps
abertos, somaram **754.0 MiB de RSS**, e consumiram
**0.25% de um núcleo** durante
4.00 segundos ociosos. A soma de RSS conta páginas
compartilhadas várias vezes; também não representa toda a memória do sistema.
É uma amostra curta cloud x86_64, não um limite de RAM nem previsão para Moto G34.
Nenhum valor de bateria, temperatura ou desempenho ARM64 foi inventado.

## Evidências incluídas

- [Relatório da sessão](validation/integration.json), com cada verificação e métricas.
- [Boot do guest](validation/guest-boot.json), com escopo e log final.
- [Controles NovaMusic](validation/music-gui.json).
- [Cores dos temas](validation/theme-contrast.json).
- [Versões Debian instaladas](validation/debian-package-versions.tsv).
- [Saída dos 53 testes](validation/unit-tests.log).
- [Captura nativa](validation/native-desktop.png), gerada do desktop real em Xvfb.

O teste original encontrou wallpaper ausente em perfis XFCE novos, temas
inativos sem contraste e dependência de notificação ausente no primeiro runtime.
As falhas foram corrigidas e a sessão foi repetida com dependências completas.
A regressão também verifica que não há diálogo de falha de plugin. O harness
Xvfb recebeu `-noreset` após uma corrida de conexão com o servidor de testes.

## Reproduzir em Debian

Instale as dependências de `desktop/packages-lite.txt` mais `xvfb`, `xauth`,
`xdotool`, `wmctrl`, `imagemagick`, `shellcheck`, `ffmpeg` e `python3-numpy`.

```bash
python3 -m unittest discover -s tests -v
bash tests/integration/run.sh
NOVAOS_AUDIO_SINK=fakesink dbus-run-session -- xvfb-run -a /usr/bin/python3 tests/integration_music.py
xvfb-run -a /usr/bin/python3 tests/integration/theme_contrast.py
python3 music/verify.py
bash scripts/release.sh
(cd dist && sha256sum -c SHA256SUMS)
```

`tests/integration/guest_boot.py` exige instalação guest, usuário `nova` e
`/usr/local/libexec/novaos-mobile-session`. Execute como `nova` em Xvfb. Ele
executa a sessão instalada num kernel Linux nativo, não emula Android.

## Roteiro pendente no Moto G34

1. Instalar Termux e Termux:X11 oficiais; verificar/extrair o bundle e executar
   o instalador. Guardar `novaos-mobile doctor` e logs.
2. Iniciar, abrir terminal, arquivos, editor, Firefox, notas e música. Confirmar
   toque, mouse/teclado, paisagem e redimensionamento.
3. Ouvir áudio físico; pausar/retomar; testar rota Bluetooth se desejado.
4. Criar documento e nota; parar/iniciar e confirmar persistência. Verificar
   comportamento ao alternar apps Android e após encerramento pelo sistema.
5. Medir RAM/CPU no aparelho sem e com Firefox; observar bateria e temperatura
   apenas quando mensuráveis. Comparar Lite e Balanced.
6. Fazer backup com sessão parada, conferir checksum e restaurar somente após
   preservar uma segunda cópia. Testar atualização e desinstalação em ambiente
   descartável, respeitando as confirmações de perda de dados.
7. Em modo avião, confirmar abertura dos apps locais, edição e reprodução.

O downloader automático também passou em seis testes adicionais: download
verificado, arquivo adulterado, manifesto interno inválido, falha de rede,
preservação de arquivos e modo de download sem executar instalação. A validação
de download HTTPS da release publicada é registrada junto dos artefatos.

Continuam pendentes: instalação ARM64 completa em Android, comportamento PRoot,
saída de áudio física, toque, suspensão/recuperação Android, restauração completa
real, boot BIOS/UEFI de ISO e instalador Desktop. GitHub Actions foi configurado;
esta matriz registra os testes locais executados, não um resultado de workflow remoto.
Não há ISO nem APK NovaOS fabricado nesta entrega.

## Correção Mobile fix1

O PRoot-Distro 5.10.2 escreve `install --help` em stderr, mesmo com saída de
sucesso. A instalação original lia apenas stdout e rejeitava incorretamente
essa versão. `mobile/check-proot.sh` agora captura ambos os canais e distingue
falha do comando de ausência da opção `--name`. Quatro testes de regressão
passaram, incluindo a reprodução do formato de saída informado no Android.
A correção não remove o rootfs nem exige atualizar um PRoot-Distro já compatível.

## Correção Mobile fix2

Uma instalação anterior já usava o nome `novaos`, sem a marca desta edição.
O instalador agora consulta `proot-distro list --quiet` e escolhe um ambiente
livre, como `novaos-lite`, sem apagar ou adotar o rootfs desconhecido. Ambientes
marcados pela edição são reutilizados. O nome salvo passa a ser usado no launcher,
backup, restauração e remoção, com confirmação correspondente ao ambiente.
Passaram 26 testes Mobile (incluindo colisões, persistência do nome, processos
reais e comportamento legado) e os seis testes do downloader. Esses testes
não substituem a instalação completa no Android físico.
