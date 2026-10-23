# NovaOS Mobile Lite no Android — sem PC e sem root

Esta versão foi preparada para **Moto G34 5G (ARM64)** com aproximadamente 15 GB
livres. O padrão é Lite. O modelo existe com diferentes quantidades de RAM;
nenhuma medição deste projeto foi feita num Moto G34 físico. Os testes executados
são Linux x86_64, e os testes do supervisor substituem serviços Android por
processos controlados: veja [VALIDATION.md](VALIDATION.md).

## 1. Instale os dois aplicativos Android oficiais

- **Termux:** [F-Droid](https://f-droid.org/packages/com.termux/) ou
  [releases oficiais](https://github.com/termux/termux-app/releases).
- **Termux:X11:** [releases oficiais nightly](https://github.com/termux/termux-x11/releases/tag/nightly).
  Selecione o APK `arm64-v8a` ou universal. Não é um APK NovaOS.

Use as fontes oficiais. Se instalar o opcional Termux:Widget, ele deve vir da
mesma fonte/assinatura que o Termux. Não é necessário instalar Widget para usar
NovaOS. Não troque a origem do Termux desinstalando sua instalação atual sem
backup: a desinstalação Android apaga o armazenamento interno do aplicativo.

O Termux:X11 requer Android 8 ou posterior; o Moto G34 é compatível com essa
base. Permita instalar o APK pelo seu navegador/gerenciador de arquivos quando
o Android solicitar. Não conceda root, acessibilidade ou acesso a contatos.

## 2. Baixe e confira o pacote no próprio celular

### Instalação automática com um comando

No Termux, este comando baixa o instalador e seu checksum da branch de downloads Mobile Lite,
confere o script e então executa. O instalador baixa o pacote completo de cerca
de 35 MiB, verifica o SHA-256 fixado no script e o manifesto interno, extrai em
uma pasta nova na home e instala as dependências:

```bash
curl -fL --fail-early --proto '=https' --proto-redir '=https' --remote-name-all 'https://raw.githubusercontent.com/Hhhaofuqoc/novaos/mobile-lite-downloads-v0.1.0-fix2/{install-novaos.sh,install-novaos.sh.sha256}' && sha256sum -c install-novaos.sh.sha256 && bash install-novaos.sh
```

Depois execute `novaos-mobile start`. O aplicativo Android Termux:X11 continua
necessário; o instalador não pode confirmar permissões Android por você.
O código-fonte desta edição fica na branch `mobile-lite-0.1.0` do repositório.
Para apenas baixar/verificar/extrair, use `bash install-novaos.sh --download-only`.

### Alternativa: baixar os arquivos manualmente

Baixe os arquivos fornecidos junto desta entrega:

- `novaos-0.1.0-mobile.tar.gz`
- `novaos-0.1.0-mobile.tar.gz.sha256`

O pacote contém fontes completas, temas, instalador e as 12 músicas já renderizadas.
Os arquivos também estão na [release Mobile Lite](https://github.com/Hhhaofuqoc/novaos/releases/tag/v0.1.0-mobile-lite).
O procedimento manual abaixo continua disponível.

No Termux, execute:

```bash
pkg update
pkg upgrade
termux-setup-storage
mkdir -p "$HOME/novaos-install"
cp "$HOME/storage/downloads/novaos-0.1.0-mobile.tar.gz" "$HOME/novaos-install/"
cp "$HOME/storage/downloads/novaos-0.1.0-mobile.tar.gz.sha256" "$HOME/novaos-install/"
cd "$HOME/novaos-install"
sha256sum -c novaos-0.1.0-mobile.tar.gz.sha256
```

Só continue se aparecer `OK`. Se o navegador mudou os nomes adicionando `(1)`,
renomeie os arquivos para os nomes acima ou ajuste os comandos. O acesso ao
armazenamento compartilhado serve para importar o arquivo e exportar backups;
a instalação real ficará na home privada do Termux. Checksums confirmam
integridade, não autenticidade por assinatura; obtenha ambos desta entrega.

```bash
tar -xzf novaos-0.1.0-mobile.tar.gz
cd novaos-0.1.0
bash mobile/install-termux.sh
```

A instalação verifica ARM64/x86_64, Termux, manifesto de arquivos e pelo menos
**6 GiB livres**. 15 GB ultrapassam esse mínimo, mas conserve espaço para cache,
seus documentos e backups. Ela baixa dependências Debian/Termux; mantenha Wi-Fi,
energia e o Termux aberto até terminar. A quantidade final de dados depende das
versões dos repositórios; 6 GiB é um limite preventivo, não uma medida de instalação.

O instalador usa a CLI OCI moderna do **proot-distro v5** e uma imagem Debian
`trixie-slim` com digest fixado em `mobile/debian-image.txt`. Os pacotes APT usam
assinaturas oficiais; não há execução de scripts remotos por `curl | sh`.
Caso o instalador peça atualização do proot-distro, siga a instrução exibida.

Se já existir um ambiente `novaos` sem a marca deste instalador, ele será
preservado. O instalador escolherá `novaos-lite` ou um sufixo livre e guardará
o nome para o launcher, backup e desinstalação. Não é necessário apagar ou
renomear o ambiente anterior. `novaos-mobile doctor` mostra o nome selecionado.

## 3. Abra a sessão

```bash
novaos-mobile start
```

Abra o aplicativo **Termux:X11** caso ele não seja trazido para frente. Gire o
celular para paisagem. Nas preferências do Termux:X11, comece com resolução
1280×720 ou nativa e ajuste a escala até ficar confortável. Mouse e teclado
Bluetooth/USB são tratados pelo Android/Termux:X11; o modo touchpad do X11 pode
facilitar clicar em menus de aplicativos tradicionais.

O dock abre arquivos, terminal, Firefox, NovaMusic, notas, configurações e monitor.
Use NovaWelcome pelo menu para ver todos os aplicativos. O usuário Debian é
`nova`; documentos ficam em `/home/nova`, e as configurações persistem entre sessões.

No Moto G34, considere configurar **Bateria → uso de bateria do aplicativo** para
permitir execução de Termux e Termux:X11 enquanto estiver usando NovaOS. Os nomes
dos menus variam por versão Android. Não há garantia de execução indefinida em
segundo plano: o Android ainda pode encerrar processos. O launcher não usa wakelock
permanente, nem muda automaticamente as restrições do Android.

## 4. Usar, parar e recuperar

No Termux, fora do Debian:

```bash
novaos-mobile status
novaos-mobile stop
novaos-mobile start
novaos-mobile restart
novaos-mobile doctor
novaos-mobile logs
```

`stop` encerra os processos identificados da sessão e preserva arquivos. Fechar
somente a janela do Termux:X11 pode deixar a sessão rodando. Após uma falha, `start`
limpa processos registrados órfãos e inicia novamente; não restaura documentos
não salvos de aplicativos terceiros. NovaNotes salva automaticamente após 800 ms.

Se houver tela preta, tente, nesta ordem:

```bash
novaos-mobile stop
novaos-mobile start --legacy-drawing
```

Se o display estiver ocupado por outra sessão, encerre essa sessão ou use
`novaos-mobile start --display 2`. Se persistir, copie `novaos-mobile doctor` e
`novaos-mobile logs`; não apague o rootfs como primeira tentativa.

Não há listeners TCP de X11/PulseAudio: X11 usa autenticação por cookie e ambos
usam sockets locais. Não use `xhost +` nem habilite áudio TCP aberto.

## 5. Pacotes, terminal e atualizações

NovaStore pesquisa o catálogo APT e abre um terminal para instalar o pacote
selecionado. NovaUpdater atualiza catálogo e pacotes. O helper exibe o comando e
exige que você digite `SIM`, seguido das confirmações normais do APT.

Para abrir um shell Linux pelo Termux:

```bash
novaos-mobile shell
exit
```

Administração Debian, quando necessária:

```bash
novaos-mobile shell --root
apt-get update
apt-get upgrade
exit
```

Esse `root` é emulado dentro do PRoot e não concede root Android. O ambiente
PRoot não é uma barreira de segurança para software desconhecido. Wi-Fi,
Bluetooth, permissões e suspensão continuam sob controle do Android.

Para atualizar o código/tema do NovaOS, encerre a sessão, faça backup, verifique
um novo pacote de fontes e execute novamente `bash mobile/install-termux.sh`
dentro dele. O instalador reutiliza apenas um ambiente marcado como pertencente
ao NovaOS e preserva a home. Não extraia versões diferentes por cima de fontes
antigas; use uma pasta nova. A migração Debian entre versões não é automática.

## 6. Backup e restauração

Encerre NovaOS e crie um backup em um destino com espaço suficiente. Um backup
completo pode ocupar vários GB adicionais. O arquivo `.sha256` é criado ao lado.

```bash
novaos-mobile stop
novaos-mobile backup "$HOME/storage/downloads/novaos-backup.tar.gz"
```

Guarde o backup e seu checksum fora do armazenamento privado do Termux.

```bash
novaos-mobile restore "$HOME/storage/downloads/novaos-backup.tar.gz"
```

A restauração verifica o checksum e os caminhos. Ela **substitui todo o ambiente**,
incluindo a home, e exige digitar `RESTAURAR` seguido do nome do ambiente exibido. Restaure apenas backups
criados por você. A instalação dos aplicativos Android e do launcher deve existir
antes da restauração. O formato usado é o backup proot-distro v5.

## 7. Desinstalar

```bash
novaos-mobile stop
novaos-mobile uninstall
```

Leia o aviso: o comando exige `EXCLUIR` seguido do nome do ambiente exibido e apaga esse Debian e `/home/nova`.
Fontes, backups, Termux e Termux:X11 permanecem. Desinstalar Termux pelo Android
é uma operação diferente que também apaga outros ambientes existentes nele.

## Escopo desta alpha

Sem PC; sem APK NovaOS próprio; sem ROM; sem kernel substituto. Perfis visuais,
app launcher Termux/atalho opcional Widget e apps Linux reais estão implementados.
O desempenho final, áudio físico, touchscreen, suspensão e instalação completa
no Moto G34 ainda precisam ser validados no aparelho. Wallpaper animado, blur,
limites cgroup e visualizador de áudio não estão implementados nesta edição.
