# Build e distribuição

Os scripts geram artefatos locais a partir de código-fonte legível. Nenhum comando
neste documento publica automaticamente um site, repositório ou release.

## Dependências do build

Debian 13: `python3`, `python3-numpy`, `python3-psutil`, `ffmpeg`, `dpkg-dev`, `tar`,
`gzip` e ferramentas coreutils. Para testes GUI: Python GI, GTK3, GStreamer, Xvfb e
xauth. As dependências de runtime estão em `desktop/packages-lite.txt` e no campo
`Depends` do pacote. Nenhum `pip install` global é necessário.

```sh
python3 -m unittest discover -s tests -v
python3 music/generate.py
bash scripts/build-deb.sh
bash scripts/release.sh
(cd dist && sha256sum -c SHA256SUMS)
```

`build-deb.sh` usa `installers/install-system.sh --destdir` e `dpkg-deb
--root-owner-group`; não precisa de root e não instala dependências no host. O
pacote `novaos-desktop` contém aplicativos, temas, wallpapers e integração.
`novaos-music` é separado e só existe quando os arquivos gerados estão presentes.
O instalador de sistema é a única fonte da estrutura do pacote.

`release.sh` produz:

- `novaos-desktop_0.1.0_all.deb` e, se renderizado, `novaos-music_0.1.0_all.deb`;
- `novaos-0.1.0-source.tar.gz`, com código e instruções;
- `novaos-0.1.0-mobile.tar.gz`, o mesmo código completo para instalar pelo Termux;
- `novaos-0.1.0-themes.tar.gz`, temas e wallpapers;
- `novaos-0.1.0-music.tar.gz`, apenas se o álbum existir;
- `release-manifest.json` com tamanhos/hashes, e `dist/SHA256SUMS`;
- arquivos `.tar.gz.sha256` ao lado dos bundles, para conferir cada download;
- `SHA256SUMS` na raiz do código e dentro dos bundles, para verificar os fontes.
- `install-novaos.sh` e `.sha256`: downloader externo com o hash do bundle fixado.

O downloader é gerado **depois** do arquivo Mobile para não criar uma dependência
circular entre os hashes. `NOVAOS_DOWNLOAD_BASE_URL` permite apontar uma release
HTTPS diferente; o padrão é a release `v0.1.0-mobile-lite` do repositório NovaOS.
Sua origem é `mobile/bootstrap-termux.sh.in`, com geração por
`scripts/build-bootstrap.py`. Ele preserva os fontes numa pasta nova e remove
o download temporário ao terminar. Falhas de rede ou checksum não executam a
instalação. O parâmetro `--download-only` verifica/extrai sem instalar.

O bundle Mobile não é uma rootfs pronta nem APK. Ele instala Debian/pacotes usando
os repositórios configurados. Nesta entrega, os bundles de fontes e Mobile incluem
as 12 gravações prontas, com hashes no manifesto, para não exigir geração no
celular. O pacote separado de músicas também é fornecido. Depois da instalação, as operações locais essenciais podem
funcionar sem Internet. A instalação inicial requer downloads.

`NOVAOS_VERSION` permite uma versão Debian válida e `NOVAOS_DIST_DIR` define a
saída. `SOURCE_DATE_EPOCH` normaliza timestamps dos arquivos; por padrão é zero.
Reexecute `release.sh` após qualquer alteração final: o manifesto de fontes precisa
corresponder exatamente aos arquivos distribuídos. Os arquivos tar têm ordenação,
proprietário e timestamps normalizados. Isso não
é uma alegação de ISO bit a bit reproduzível: APT usa os repositórios Debian atuais,
as versões de ferramentas podem variar e não há snapshot fixo. Guarde os logs e
hashes dos pacotes usados quando for preparar uma release formal.

## GitHub Actions

Os workflows têm permissões mínimas por job e versões das actions fixadas por
commit. A imagem Debian usa codename `trixie-slim`; atualizações da imagem podem
mudar dependências. A CI é uma configuração entregue, não uma execução realizada
neste ambiente.

- `validate.yml`: em push/PR, valida sintaxe, executa testes, gera o álbum e os
  pacotes, verifica dependências, testa os controles GTK/GStreamer em Xvfb com
  saída de áudio descartada e envia artifacts do workflow.
- `iso.yml`: execução manual, build privilegiado em container Debian, produz ISO
  real com log. Deve ser usado somente em referência confiável do repositório.
- `release.yml`: execução manual de uma tag existente. Sempre prepara artifacts;
  publica prerelease **somente** com `publish=true` e variável de repositório
  `NOVAOS_PUBLISH_RELEASES=true`. O padrão não publica. `gh release create
  --verify-tag` recusa criar tag implicitamente. A versão inicial aceita `v0.1.0-mobile-lite`;
  atualize a validação ao versionar o projeto.

A receita de ISO e a publicação de release são etapas distintas. A release de
pacotes não inclui uma ISO automaticamente. O mantenedor precisa validar o boot e
anexar o artefato de ISO aprovado; nenhuma ISO ou APK é fabricado para completar
uma lista de arquivos.

## Licenças e confiança

Distribua os arquivos de licença do código, arte e música junto com os artefatos.
Pacotes Debian mantêm suas próprias licenças em `/usr/share/doc`. Checksums são
integridade, não autenticação. Para uma release pública, publique hashes em canal
confiável e adicione uma assinatura com uma chave administrada pelo mantenedor.
Não há chave de assinatura privada criada ou distribuída por este projeto.

As opções da receita foram conferidas no [manual live-build do Debian 13](https://manpages.debian.org/trixie/live-build/lb_config.1.en.html). A receita inclui `ca-certificates` no bootstrap para usar mirrors HTTPS e usa `none` para omitir o instalador. Isso valida as opções documentadas, não a execução/boot da ISO.
