# Arquitetura da alpha 0.1.0

## Caminho prioritário: Android

Android mantém seu kernel, drivers, rede e gerenciamento de energia. Termux
fornece processos nativos Android; PRoot traduz acessos ao sistema de arquivos
para executar Debian ARM64/x86_64. Não há VM, kernel Debian nem systemd PID 1
no Mobile. O custo de PRoot em chamadas de sistema pode reduzir desempenho.

Termux:X11 apresenta a sessão X11 local. Uma instância de PulseAudio do launcher
usa socket Unix privado e transmite áudio ao Android. O usuário Linux `nova`
executa XFCE e aplicativos. PRoot não oferece isolamento de segurança equivalente
a container/VM; só instale programas em que você confia.

O launcher mantém processos e estado próprios; não usa `killall` para encerrar
outras sessões Termux. Configuração, documentos, biblioteca e notas residem no
rootfs persistente de `novaos`. A remoção do aplicativo Termux pelo Android
remove esse armazenamento privado: faça backup externo antes.

## Desktop

Debian 13 stable (trixie), kernel Debian, systemd, APT, LightDM e XFCE para Lite.
Uma lista separada permite build com Plasma. A integração visual entregue é XFCE;
Plasma ainda requer implementação visual e testes. A receita live-build inclui
boot BIOS/UEFI, opção de persistência e Debian Installer; nenhuma inicialização
de ISO foi validada nesta entrega.

## Aplicativos e privilégios

UI nativa GTK3, sem servidor HTTP e sem Chromium embutido. GStreamer decodifica
arquivos locais do NovaMusic. O CLI só importa GTK quando abre GUI. Aplicativos
existentes e mantidos fornecem terminal, arquivos, navegador, editor e processos.

`/usr/lib/novaos/apt-helper` aceita apenas `update`, `upgrade` e `install PACOTE`;
valida nomes, limpa ambiente, não usa shell e exige confirmação interativa.
No Mobile, somente esse helper tem autorização sudo sem senha. Não se concede
sudo geral a `nova`. No Desktop, pkexec pede autenticação administrativa.

## Desempenho implementado

Aplicativos abrem sob demanda. Music e Notes persistem estado por escrita atômica.
O agente de sessão lê métricas a cada 20 segundos; o monitor aberto, a cada 3.
Não há wallpaper animado nem renderização contínua customizada do desktop.
Lite desliga composição/animações; Balanced e Ultra usam os efeitos disponíveis
no XFWM. Não alegamos diferença de blur entre esses perfis: XFWM não implementa
blur aqui. Lite é o padrão automático no Android, independentemente da RAM.

Economia manual força Lite. Adaptação reduz efeitos se RAM disponível cair abaixo
de 512 MiB ou bateria mensurável ficar em até 20%, desconectada. A seleção anterior
é restaurada quando a condição termina. Android pode bloquear `/proc`/`sysfs`;
leituras bloqueadas são identificadas e a seleção Lite continua funcionando.

Cache APT é limpo ao instalar. Não há limpeza automática de documentos ou do cache
de outros aplicativos. Limites rígidos cgroup para serviços não são aplicados em
PRoot, onde não estão disponíveis sem privilégios; isso permanece uma limitação
explícita. Nenhuma meta de desempenho ARM64 foi medida no ambiente cloud x86_64.

## Integridade e distribuição

Pacotes Debian/Termux vêm de repositórios assinados. Rootfs Mobile usa digest OCI
fixado; proot-distro valida manifesto/camadas. Releases contêm SHA256SUMS e cada
arquivo distribuído recebe checksum externo. Checksums identificam corrupção;
não substituem assinatura de autor nem uma origem de download confiável.

A instalação instala apenas caminhos do projeto e preserva a home. Atualização
é reaplicação das fontes verificadas. O launcher implementa backup/restauração
e exige confirmação explícita para remover o ambiente. Não há publicação externa
automática executada; workflows de release precisam de um repositório configurado.
