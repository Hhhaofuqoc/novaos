# NovaMusic — biblioteca local original

NovaMusic é um aplicativo GTK 3 real, em Python, que usa GStreamer `playbin` para
reprodução local. Não usa navegador, streaming, amostras de terceiros nem um
motor de áudio JavaScript. O aplicativo só carrega o áudio quando o usuário dá
play. Não inicia automaticamente ao entrar na sessão.

A coleção **Your Universe** contém doze miniaturas instrumentais originais de
72 segundos cada: **14 minutos e 24 segundos** de áudio estéreo, 44,1 kHz, 16 bits,
em FLAC. Os arquivos foram gerados neste projeto e estão em `music/generated/`.
Aproximadamente 33 MiB são usados pelo álbum completo. `manifest.json` registra
metadados, duração, tamanho, pico, RMS e SHA-256 de cada faixa.

1. Neon Rain
2. Purple Orbit
3. Quiet Terminal
4. Digital Memories
5. Blue Horizon
6. Floating Pixels
7. Midnight Kernel
8. Soft Geometry
9. Distant Satellites
10. Empty Desktop
11. Celestial Code
12. Nova Dreams

O gerador usa osciladores matemáticos com envelopes de piano suave, pads lentos,
notas cristalinas esparsas e ecos curtos. As progressões, padrões e sementes estão
no código. Não incorpora melodias, gravações, MIDI ou SoundFonts existentes.
Cada faixa tem entrada e saída suaves; o player não implementa crossfade entre
arquivos. Os arquivos de áudio e a capa original são disponibilizados em CC0-1.0.

## Reprodução

No menu ou dock, abra **NovaMusic**. Pelo terminal:

```sh
novaos music
novaos music --mini
novaos music --ambient
```

O álbum aparece na playlist quando o pacote `novaos-music` está instalado.
**Add local music…** adiciona WAV, FLAC, OGG, Opus, MP3, M4A e AAC. O suporte a
cada codec depende dos plugins GStreamer instalados; o álbum FLAC funciona com
os plugins `base` e `good`. Falhas de decodificação ou de dispositivo de áudio
aparecem no rodapé. Arquivos locais importados não são copiados nem apagados.

Os controles de play/pause, anterior, próxima, volume, busca na faixa, playlist,
repetição de faixa/álbum e shuffle operam sobre o pipeline real. O shuffle toca
cada faixa uma vez antes de parar, salvo repetição do álbum. A seleção, volume,
modos e biblioteca persistem em `~/.config/novaos/music.json` (ou no diretório
`XDG_CONFIG_HOME`). A gravação das preferências é atômica. Arquivos locais que
foram removidos são ignorados ao restaurar a biblioteca.

Atalhos:

| Tecla | Ação |
| --- | --- |
| Espaço | Reproduzir / pausar |
| Ctrl+→ / Ctrl+← | Próxima / anterior |
| Ctrl+O | Importar arquivos locais |
| M | Alternar mini-player |
| Ctrl+Q | Encerrar, inclusive no modo Ambient |

**Mini** reduz a janela aos controles essenciais. **Ambient Desktop** mantém o
áudio quando a janela é fechada: a janela é minimizada e continua acessível pela
barra de tarefas. Isso não impede o Android de encerrar Termux em segundo plano.
Ctrl+Q encerra explicitamente e libera o pipeline. Não há serviço de áudio de
NovaMusic permanente após o encerramento.

Instâncias adicionais usam o mesmo `Gtk.Application` no D-Bus da sessão. Também
é possível controlar a instância atual:

```sh
novaos music --toggle
novaos music --next
novaos music --previous
```

O visualizador espectral não está implementado nesta versão; isso evita um loop
de desenho adicional no perfil Lite. O relógio de reprodução atualiza uma vez
por segundo somente enquanto o player está reproduzindo.

## Gerar o álbum novamente

No Debian, dependências de geração: `python3-numpy` e `ffmpeg`. Elas não são
necessárias para simplesmente ouvir o álbum pronto.

```sh
python3 music/generate.py
python3 music/verify.py --report /tmp/novaos-audio-verification.json
```

A geração é determinística para as mesmas versões de NumPy e do encoder.
Versões diferentes podem produzir hashes FLAC diferentes; a validação utiliza
os hashes do manifesto gerado na mesma execução. Cada faixa é gerada
individualmente, limitando o uso de memória durante a síntese. O padrão de
72 segundos não é uma promessa de duração para outros parâmetros.

Para um teste rápido ou máquinas sem encoder FLAC:

```sh
python3 music/generate.py --seconds 3 --sample-rate 8000 --format wav --output /tmp/novaos-music-test
python3 -m unittest discover -s tests -p test_music.py -v
```

`--track N` gera uma faixa isolada e um manifesto apenas daquela faixa; use um
diretório de saída separado para não substituir o manifesto do álbum completo.

## Validação e limites

O teste portátil cobre navegação e fim de playlist, repetição, shuffle, biblioteca,
recuperação de preferências inválidas, gravação atômica, síntese determinística,
limites de pico, ausência de silêncio completo e integridade dos doze arquivos.
`music/verify.py` verifica SHA-256, formato, duração e decodificação **completa**
de cada FLAC usando FFmpeg. O relatório de execução está em
`music/generated/verification.json`.

Com GStreamer instalado, este comando também decodifica uma faixa inteira via
`playbin` até EOS, usando `fakesink`:

```sh
novaos music --audio-test /usr/share/novaos/music/generated/01-neon-rain.flac
```

Decodificar para `fakesink` verifica o pipeline e o codec, não o alto-falante nem
a ligação de áudio entre PRoot e Termux. A saída física, interrupções do Android,
Bluetooth e latência exigem teste no aparelho. A interface utiliza o áudio da
sessão; os parâmetros de PulseAudio pertencem ao launcher mobile.

A validação executada neste ambiente Linux x86_64 também incluiu:

- As doze faixas decodificadas integralmente por GStreamer `playbin` até EOS;
  relatório `music/generated/gstreamer-verification.json`.
- Dezoito verificações reais de GTK/GStreamer sob Xvfb e D-Bus: abertura da
  janela, avanço da posição, pausa, busca até 20 segundos, navegação/metadados,
  volume no pipeline, shuffle/repetição, mini-player, tecla Espaço enviada por
  X11, Ambient Desktop, persistência, EOS da última faixa, rolagem em janela
  pequena para paisagem e liberação do pipeline. Resultado mais recente em
  `docs/validation/music-gui.json`.
- Pico de RSS do processo da última execução: **136.348 KiB**, incluindo Python, GTK,
  GStreamer e bibliotecas. Isso é uma medição do teste no cloud x86_64, não uma
  previsão de RAM no Android e não inclui o desktop completo.

Para repetir as verificações da interface numa instalação Debian com dependências,
`xvfb`, `xauth`, `xdotool` e `dbus` instalados:

```sh
NOVAOS_AUDIO_SINK=fakesink dbus-run-session -- xvfb-run -a \
  /usr/bin/python3 tests/integration_music.py
```

O script escreve `music/generated/gui-verification.json`. O `fakesink` está
ativado apenas no teste: a reprodução normal usa a saída de áudio da sessão.
