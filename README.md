# NovaOS — NovaShell v1.0 (entrega executável inicial)

**Estado:** base instalável e interface GTK inicial implementadas; **não é** uma distribuição autônoma nem uma versão final já validada no Android. A experiência usa Termux + PRoot-Distro (Debian/Ubuntu aarch64 existente ou Debian novo) + Termux:X11 + Openbox + Python3/GTK3. **Não usa XFCE, Plasma, GNOME Shell nem systemd como PID 1.**

## O que foi implementado

- Instalador Termux automatizado com detecção de ARM64, espaço, contêiner existente, fallback entre versões de PRoot-Distro e logs.
- Novo contêiner Debian somente se o alias `novaos` não existir. Usuário `nova` reaproveitado, quando presente.
- Cópia gerenciada em `/opt/novaos/app` e backup de versões gerenciadas anteriores. Não apaga arquivos pessoais ou reconfigura shells existentes.
- NovaShell GTK3: barra superior, relógio, 4 áreas de trabalho Openbox, calendário GTK, ajuste PulseAudio via pactl quando disponível, menu XDG com busca e favoritos, dock de aplicativos instalados, NovaCenter com preferências persistentes e seleção de wallpaper.
- NovaMonitor: CPU e tráfego de rede reportados pelo Termux *apenas se legíveis*, memória Android via `/proc/meminfo`, armazenamento real e controle MPRIS caso exista player compatível.
- Perfis Lite (sem sidebar) e Full (com sidebar), scripts de iniciar/encerrar/reiniciar, diagnósticos e tema GTK NovaDark.
- Papel de parede **original** otimizado em WebP 1920×1080 e 20 SVGs originais em `assets/icons/`. Ícones oficiais XDG dos aplicativos de terceiros permanecem intactos.

## Identidade NovaOS em ferramentas de terminal — atualização de branding

O SVG original `assets/logos/NovaOS.svg` continua sendo a marca visual do desktop; a atualização acrescenta **um N ASCII multicolorido** consistente para:

- **Fastfetch**: substitui a chave `logo` do `~/.config/fastfetch/config.jsonc`, preservando `modules`, `display` e as demais configurações existentes. Instala Fastfetch pelo APT quando disponível.
- **Neofetch**: configura o arquivo ASCII original em `~/.config/neofetch/config.conf`. Não instala o projeto Neofetch descontinuado; se já instalado, usa a marca.
- **Screenfetch**: o Bash do usuário `nova` chama o Screenfetch verdadeiro com seu argumento oficial `-a`, carregando o N do arquivo `config/fetch/screenfetch-logo.sh`.
- **pfetch**: se presente e executado pelo Bash do `nova`, usa `PF_SOURCE` para alterar apenas a renderização do logo.
- **fetch** (cliente areofyl/fetch): novo arquivo `~/.config/fetch/logo.txt`, somente se não houver um personalizado.
- **nova-logo**: mostra apenas o N; **nova-info**: mostra a identidade e o sistema subjacente; **nova-fetch**: chama o fetch disponível com logo original ou recorre ao `nova-info`.

As alterações de configuração existentes são preservadas em arquivos `.backup-AAAA...` na mesma pasta. Não se muda `/etc/os-release` (a base continua Debian/Ubuntu) nem se simula métricas do Android. O novo layout dos fetchers aplica-se aos usuários `nova` e `root` **dentro do PRoot**; não altera a identidade do Termux fora da NovaOS.

Depois de instalar/atualizar o ZIP, abra **um novo terminal** e execute:

```bash
fastfetch           # se o pacote estiver disponível
neofetch            # se já estiver instalado
screenfetch         # se já estiver instalado, no Bash
pfetch              # se já estiver instalado, no Bash
nova-logo           # sempre disponível dentro da NovaOS
nova-info           # sempre disponível dentro da NovaOS
nova-fetch          # sempre disponível, com fallback
```

Nenhum mecanismo pode obrigar **todo programa de terceiros** a usar uma imagem própria: programas sem suporte a logos configuráveis continuarão com sua identidade nativa. Não substituímos executáveis de terceiros por versões falsas.

## Ainda não concluído (não presumir funcional)

- Integração MPRIS com MPV exige um serviço/plugin MPRIS compatível: MPV puro não é MPRIS. Mini-player mostra corretamente `Sem player MPRIS` e não controla MPV comum.
- Indicadores de janelas em execução dependem da classe X11 informada pelo programa, podem não corresponder a todos os aplicativos.
- Dock: rearranjo e desfixação via clique direito, fixação também pelo botão `+` nos aplicativos do NovaMenu. Ainda faltam gesto dedicado de toque longo/arrastar e reordenação direta por toque.
- Há gráfico histórico de CPU e download (somente dados reais); faltam o gráfico de RAM, capas de álbuns, seek interativo da música, mudanças de escala de tela e controles Bluetooth.
- Ainda não há tema GTK claro, animações, status exato do Android Wi-Fi, modo de janela ajustável avançado ou painel de gestão de pacotes próprio.
- Firefox ESR/LibreOffice/VS Code não são instalados na base leve. Navegador pode ser adicionado manualmente se houver espaço.
- As três cores de destaque são persistentes e passam a ser aplicadas aos botões ativos e barras de progresso após reiniciar a NovaShell; outros elementos continuam na paleta roxa.
- Não testado dentro de Termux:X11 real; startup e áudio podem exigir ajustes específicos do dispositivo.

## Instalação NO CELULAR (Termux, fora de um contêiner)

1. Instale o **aplicativo Android** Termux:X11 das fontes oficiais: https://github.com/termux/termux-x11/releases/tag/nightly — é **separado** do pacote Termux `termux-x11-nightly`.
2. Baixe o ZIP desta entrega pelo ChatGPT, coloque-o na pasta **Downloads** e autorize armazenamento no Termux (`termux-setup-storage`, apenas uma vez).
3. Execute no Termux:

   ```bash
   pkg install -y unzip
   cd ~/storage/downloads
   unzip NovaOS-v1.0-inicial.zip
   cd NovaOS
   bash install.sh
   novaos
   ```

   Se o arquivo do ZIP estiver em outra pasta, troque só o caminho. **Não execute o `install.sh` dentro do PRoot.**

4. Abra o aplicativo Termux:X11. Opcionalmente verifique logs se nada aparecer:

   ```bash
   novaos status
   novaos logs
   novaos repair
   ```

### Comandos do Termux

```bash
novaos                 # começa sessão
novaos stop            # encerra APENAS sessão gerenciada, não o servidor X11 compartilhado
novaos restart         # reinicia sessão
novaos lite            # salva perfil Lite e reinicia se ativo
novaos full            # salva perfil Full e reinicia se ativo
novaos repair          # verifica ambiente e reaplica dependências/configuração
novaos update          # atualiza clone Git válido ou reaplica ZIP instalado
novaos status
novaos logs
```

Para atualizar de um ZIP mais novo, extraia o novo ZIP e execute `bash install.sh` nele. Sem remoto Git configurado, `novaos update` não baixa versões inexistentes.

### Tela preta do Termux:X11

Na ordem:

```bash
novaos status
novaos logs
# Abra o APK Termux:X11 manualmente e confira a notificação de sessão.
novaos stop
NOVAOS_X11_FLAGS=-legacy-drawing novaos
```

**Atenção**: as flags de renderização só têm efeito quando um NOVO servidor Termux:X11 for iniciado. Como este projeto não encerra automaticamente servidores que podem estar compartilhados, use a ação `Exit` do próprio aplicativo Termux:X11 **após fechar outras sessões** e repita `NOVAOS_X11_FLAGS=-legacy-drawing novaos`. Troca de cores erradas: `-force-bgra`; ambas: `NOVAOS_X11_FLAGS='-legacy-drawing -force-bgra' novaos`. Se houver lock órfão, o script **se recusa a removê-lo automaticamente**, para evitar atingir X11 de terceiros. `NOVAOS_DISPLAY=:2 novaos` pode contornar `:1` ocupado.

Mais logs: `~/.local/state/novaos/logs/` no Termux; `$HOME/.local/state/novaos/logs` dentro do PRoot como usuário `nova`.

### Espaço e desempenho

O instalador verifica o espaço livre no início e recusa executar com menos de 9 GiB (estimativa de até 5 GiB + reserva desejada de 4 GiB). A estimativa de 2–5 GiB é indicativa, varia conforme base existente, caches e pacote da distribuição; **não é uma medição nem garantia de limite**. Não instala apps de escritório pesados. Evita animações e composição GPU no perfil Lite.

### O que o instalador não faz

- **Não** chama `proot-distro remove`/`reset`, não apaga contêiner `novaos` e não redefine senha ou sudo.
- **Não** apaga cookies, arquivos ou dados do usuário `nova`.
- **Não** limpa locks X11 nem mata outros servidores/sessões PRoot.
- **Não** faz downgrade nem remove outros ambientes gráficos já presentes dentro de `novaos`.

### Recuperação sem perdas

Se a instalação existente usa uma base **sem APT**, `install.sh` interrompe antes de configurar guest; escolha outra base/contêiner de forma manual. Se Debian/Ubuntu tiver pacotes quebrados, use `novaos repair` e consulte logs. O backup de instalações NovaOS anteriormente gerenciadas fica em `/var/backups/novaos/` **dentro do contêiner**. Configurações novas ficam em `/home/nova/.config/novaos/`. Para remover somente arquivos gerenciados e preservar o contêiner: `bash uninstall.sh` a partir do projeto, confirmando `DESINSTALAR`.

### Testes (offline, no computador de desenvolvimento)

`bash scripts/check-project.sh` verifica sintaxe Bash, Python, XML e persistência JSON. Eles **não** comprovam que X11, PulseAudio, app Firefox, bateria ou touchscreen estejam funcionais no dispositivo Android.

## Estrutura principal

- `install.sh`, `start.sh`, `stop.sh`, `repair.sh`, `update.sh`, `uninstall.sh`: comandos reais.
- `scripts/host-control.sh`: ciclo de vida da sessão com PIDs verificados.
- `scripts/setup-guest.sh`: configuração de pacotes via APT, preservando existente.
- `scripts/guest-session.sh`: Openbox e NovaShell, logs isolados.
- `scripts/host-metrics.py`: métricas reais se o Android permitir.
- `scripts/enable-branding.py`, `assets/logos/nova-*.txt`, `config/fetch/*`: N oficial para utilitários de terminal.
- `nova-shell/main.py`, `panel.py`, `launcher.py`, `dock.py`, `sidebar.py`: desktop GTK.
- `nova-shell/settings/app.py`: NovaCenter.
- `nova-shell/services/*`: XDG, JSON, MPRIS, armazenamento.
- `config/openbox/rc.xml`: quatro desktops reais e margens.
- `themes/NovaDark/gtk.css`: tema.
- `assets/wallpapers/nova-night.webp`, `assets/icons/*.svg`: arte original.

## Referências técnicas

- [Termux:X11 oficial](https://github.com/termux/termux-x11): APK, `termux-x11-nightly`, flags, `--shared-tmp`.
- [PRoot-Distro oficial](https://github.com/termux/proot-distro): `list`, `install --name`, `login --shared-tmp`, sessões.

## Publicação e atualizações pelo GitHub (Termux)

Este projeto inclui `publish-github.sh` para criar o repositório público **Hhhaofuqoc/NovaOS** e enviar os fontes pelo GitHub CLI oficial. Não usa token colado no chat, não dá `force push`, recusa um `origin` diferente e **não** modifica o contêiner existente. É necessário fazer login interativo no GitHub CLI no celular uma vez, pois a conexão do ChatGPT não autentica o terminal Termux.

Depois de extrair o ZIP atualizado:

```bash
pkg install -y unzip
termux-setup-storage
mkdir -p ~/novaos-publish && cd ~/novaos-publish
unzip -oq ~/storage/downloads/NovaOS-v1.0-github.zip
bash NovaOS/publish-github.sh
```

No primeiro uso, siga o código de login informado pelo `gh auth login` no navegador. Ao fim, a saída deve trazer o URL real do GitHub. **Somente considere publicado quando o comando confirmar sucesso.**

Depois execute `bash install.sh` a partir da pasta Git para instalar sua cópia gerenciada com `.git`. A partir daí, `novaos update` buscará atualizações via `git pull --ff-only` na cópia gerenciada, se o remoto continuar acessível. Fazer o push da versão inicial não cria automaticamente novos commits; atualizações futuras precisam ser publicadas no repositório.

## NovaOS Full ISO para VM x86_64

A versão **NovaOS Full** é uma ISO Live real baseada em Debian 13 amd64,
com kernel Linux e sessão gráfica própria (LightDM + Openbox + NovaShell GTK3).
É independente de Termux e PRoot.

**Construir pelo celular:** acesse [Actions — NovaOS Full ISO](https://github.com/Hhhaofuqoc/novaos/actions/workflows/novaos-full-iso.yml)
e use **Run workflow**. Uma execução bem-sucedida anexará o artefato
`NovaOS-v1.0-Full-amd64`, contendo a ISO e o SHA256. Se o build falhar,
nenhuma ISO deve ser considerada pronta. Há também um teste QEMU que gera
uma captura real da VM.

**Limitações:** a ISO é Live (não instala automaticamente em disco) e os
runners do GitHub Actions são temporários — não oferecem uma VM interativa
permanente. Consulte [o guia ISO Full](iso/full/README.md).
