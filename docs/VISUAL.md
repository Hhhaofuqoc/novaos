# Identidade visual NovaOS 0.1

O visual padrão usa `#08040F`, `#250044`, `#A020F0`, `#00DFFF`, `#007BFF` e
`#EDE6FF`. As capturas citadas no pedido não foram recebidas neste ambiente;
esta implementação segue a descrição textual, sem afirmar equivalência a elas.

## Arte original entregue

- `wallpapers/novaos-desktop.svg` e `.png`: 3840 × 2160.
- `wallpapers/novaos-mobile.svg` e `.png`: 1080 × 2400.
- Planeta roxo, anéis luminosos, cidade, montanhas trianguladas e grade em
  perspectiva são geometria original, gerada deterministicamente.
- Onze ícones SVG originais em `themes/icons/NovaOS/scalable/apps`.
- Temas nativos GTK3 e XFWM4 `NovaOS-Dark` e `NovaOS-Light`.

Não há imagens externas ou fontes incorporadas. O código e a arte são MIT,
como o projeto. Os temas herdam os widgets completos do Adwaita instalado;
a licença do GTK/Adwaita continua pertencendo aos respectivos autores.

Para regenerar:

```sh
python3 themes/generate-assets.py
inkscape wallpapers/novaos-desktop.svg --export-filename=wallpapers/novaos-desktop.png
inkscape wallpapers/novaos-mobile.svg --export-filename=wallpapers/novaos-mobile.png
```

Os PNGs são entregues para evitar rasterização do SVG durante o login. Um
wallpaper animado ainda não foi implementado; os três perfis usam arte estática.

## Painéis e janelas reais

`themes/apply-xfce.sh lite dark` deve rodar dentro da sessão X11 e D-Bus do XFCE.
A instalação põe temas em `/usr/share/themes`, ícones em `/usr/share/icons` e
os recursos comuns em `/usr/share/novaos`. O comando é chamado pelo
`novaos session-init`.

A barra superior inclui menu de aplicativos, lista de janelas, relógio com
calendário, área de status, volume PulseAudio, notificações, configurações e
alternância entre dois desktops. A dock abre aplicativos reais: appfinder,
terminal XFCE, Thunar, Firefox ESR, NovaMusic, NovaNotes, NovaSettings e
NovaMonitor. O XFWM4 fornece arrastar, redimensionar, minimizar, maximizar,
fechar e Alt+Tab. Os botões de janela têm 30 px e os painéis 42/54 px para
facilitar uso por toque. Eles não substituem a acessibilidade do Android.

Rede e bateria no Desktop dependem dos serviços/applet Linux instalados.
Dentro de PRoot, Wi-Fi, Bluetooth e energia pertencem ao Android: use os
controles do Android. Não mostramos controles falsos para esses recursos.
A área de status do XFCE exibe os applets que realmente estiverem executando.

A primeira aplicação salva cópia de `~/.config/xfce4` em
`~/.config/novaos/backups/`. O caminho fica em `layout-v1`. As aplicações
seguintes preservam a organização dos painéis. Para reaplicar deliberadamente:

```sh
/usr/share/novaos/themes/apply-xfce.sh lite dark --reset-layout
```

Para restaurar a configuração anterior, encerre a sessão XFCE e copie o
subdiretório `xfce4` do backup para `~/.config/xfce4`. Faça uma cópia do estado
atual antes. `theme.lock` impede aplicações simultâneas; caso o processo seja
morto abruptamente, confira que não está rodando antes de remover esse diretório
vazio.

Lite desativa composição, sombras e animações GTK. Balanced/Ultra habilitam
composição e sombras; o XFWM4 não possui blur nativo, portanto não há blur nem
um efeito adicional exclusivo de Ultra nesta versão. O tema escuro permanece
legível com a composição desligada. O tamanho do framebuffer escolhe a arte:
retrato usa Mobile, paisagem usa Desktop. Não há processo de renderização
contínua do wallpaper.

## Widget opcional

No Desktop com `conky-std` instalado, execute:

```sh
/usr/share/novaos/themes/start-widget.sh
```

O widget consulta CPU, RAM, armazenamento, uptime, arquitetura e kernel a cada
três segundos. Não inicia automaticamente nem roda no Mobile. NovaMonitor é
a alternativa sob demanda. Temperatura, rede detalhada e informações de
processos são responsabilidade do monitor; sensores ausentes não são inventados.

## Validação e limites

`python3 -m unittest discover -s tests -p test_theme.py -v` valida arte SVG,
gerador determinístico, primeira configuração, backup, preservação de layout,
reconfiguração explícita, modo retrato, descoberta de monitores em perfil novo,
encerramento limitado do painel, perfis e rejeição de argumentos.
Os testes de configuração usam um substituto com estado para `xfconf-query`;
isso não equivale a testar renderização gráfica, touchscreen ou o aparelho.
Os PNGs foram realmente renderizados com Inkscape e a arte Desktop inspecionada.
Os dois temas GTK foram carregados por `Gtk.CssProvider` (GTK 3.24) sem erros
de sintaxe; esse teste sem display não valida aparência ou interação.
A aplicação real em Xvfb confirmou o wallpaper e os temas em uma sessão XFCE.
Perfis novos exigem descobrir o conector XRandR: apenas `monitor0` não é válido
em todas as telas. O script configura os conectores encontrados e recarrega o
xfdesktop. A validação integrada completa consta no relatório geral.

A regressão de contraste de janelas sem foco tem teste GTK próprio:

```sh
xvfb-run -a /usr/bin/python3 tests/integration/theme_contrast.py \
  --report dist/validation/theme-contrast.json
```

Ele consulta as cores realmente resolvidas pelo GTK para fundo, texto e texto
de botões, nos estados ativo e `:backdrop`, nos dois temas. Os valores são
iguais entre estados: escuro `#10091C`/`#EDE6FF`, claro `#F3EDFC`/`#261237`.
Isso impede que regras herdadas do Adwaita tornem o NovaMonitor cinza e pouco
legível quando outra janela recebe foco.

## Atualização Plasma e NovaFetch

A integração experimental Plasma 6 usa Breeze com esquema NovaOS, ícones próprios,
painel superior flutuante, dock inferior, wallpaper original e Konsole roxo escuro.
O perfil Lite desliga composição e blur. O layout inicial é aplicado uma vez;
alterações posteriores dos painéis são preservadas. Configurações anteriores
ficam em `~/.config/novaos/backups/plasma-*`.

NovaFetch usa Fastfetch real, logo original e seções com cores roxo/ciano, com
formatos compacto e amplo. Veja [instalação e limites](PLASMA-MOBILE.md).
A [captura real](validation/plasma-desktop.png) foi feita em Debian/Xvfb com KWin,
não em Android nem em uma simulação web.
