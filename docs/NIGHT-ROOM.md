# NovaOS Night Room — atualização visual v2

Implementação nativa sobre KDE Plasma 6 X11. O desktop segue a composição da
referência fornecida: quarto noturno, cidade, lua roxa, barra superior escura,
menu de aplicativos, dock central e cartões à direita. O wallpaper é uma arte
original gerada a partir da descrição; a captura do usuário não é usada como fundo.

O layout não é uma reprodução pixel a pixel. Aplicativos e indicadores refletem
o software e os dados realmente disponíveis; não há números pré-gravados.

## Instalar no NovaOS existente

Salve seus documentos e, no **Termux, fora do Debian**, execute:

```bash
novaos-mobile stop
curl -fL --fail-early --proto '=https' --proto-redir '=https' --remote-name-all 'https://raw.githubusercontent.com/Hhhaofuqoc/novaos/novaos-visual-v2/{install-novaos-visual.sh,install-novaos-visual.sh.sha256}' && sha256sum -c install-novaos-visual.sh.sha256 && bash install-novaos-visual.sh --plasma && novaos-mobile start
```

O pacote de código/arte tem aproximadamente 2,2 MB. Dependências KDE são obtidas
separadamente pelo APT. A atualização preserva documentos, música e XFCE; guarda
backup dos painéis anteriores antes de migrar o layout para v2. Favoritos próprios
do usuário são mantidos e os aplicativos NovaOS são adicionados pela API Activities.

Inclui configuração pt_BR.UTF-8 e recuperação das traduções portuguesas do Plasma
que as imagens Debian slim costumam excluir. `NOVAOS_LANG` pode escolher outro
locale disponível. O menu contém os aplicativos instalados; VS Code e LibreOffice
da referência não são acrescentados apenas para preencher ícones.

## Componentes reais

- Plasma/KWin: quatro desktops virtuais, alternância de janelas, menu, bandeja e dock.
- `novafetch`: Fastfetch real com monograma N roxo/azul e informações Debian/host.
- `novaos widgets`: aplicação GTK3 com CPU, RAM do host, disco, tráfego e gráfico
  medidos a cada dois segundos. Sem renderização contínua. Leituras bloqueadas
  mostram N/D. Utilização da GPU não é monitorada.
- NovaMusic publica título, artista, duração, posição e estado em arquivo privado
  no diretório de runtime. O leitor verifica PID e instante de criação do processo
  para não exibir um player encerrado como ativo. Não há servidor HTTP ou porta TCP.
- Anterior, reproduzir/pausar e próxima controlam o pipeline GStreamer existente.
  `--background` permite comandar o player sem levantar a janela. A biblioteca é local.
- Os cartões ficam abaixo das janelas comuns e não ocupam Alt+Tab. Em telas baixas,
  uma área rolável mantém os controles acessíveis.

Para abrir o player completo: `novaos music`. Para ocultar os cartões até o próximo
login: `novaos widgets --quit`. Para abrir novamente: `novaos widgets`.
É possível desativar o autostart em Configurações do Sistema → Inicialização Automática.

## Execução e limites

O projeto foi executado em terminal no ambiente de desenvolvimento Debian x86_64,
com Plasma, KWin e Xvfb reais. A integração abre Konsole com NovaFetch, verifica
os quatro desktops e executa reprodução, pausa e troca de faixa com metadados
consumidos pelo widget. Áudio usa `fakesink` no teste, sem saída física.

Capturas reais: [desktop](validation/room-desktop.png) e
[menu aberto](validation/room-desktop-menu.png). Evidência: [relatório](validation/room-report.json).
As medidas representam o host cloud; não são medidas do Moto G34.
O layout também passou em 1280×720 com cartões roláveis, quando necessário:
[relatório compacto](validation/room-compact-report.json). A suíte de áudio possui
[21 verificações reais](validation/room-music.json).

Não houve acesso remoto ao celular. Android/ARM64/PRoot, toque e saída física de
áudio continuam exigindo validação no aparelho. Wi-Fi, Bluetooth, bateria e
suspensão pertencem ao Android; não são simulados pelos cartões. Use o bloqueio
do Android, e não os comandos de energia/bloqueio herdados do KDE, no Mobile.

Rollback pelo Termux:

```bash
novaos-mobile stop && novaos-mobile desktop xfce && novaos-mobile start
```
