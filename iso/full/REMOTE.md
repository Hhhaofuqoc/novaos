# NovaOS Full — acesso remoto pelo Android

O workflow **NovaOS Full Remote VM (browser)** inicia a ISO Live x86_64 dentro do QEMU em um runner temporário do GitHub Actions. Você acessa a tela pelo navegador Android, por noVNC e um túnel HTTPS Cloudflare com autenticação Nginx.

## Preparação (uma única vez)

1. Abra [Secrets do repositório](https://github.com/Hhhaofuqoc/novaos/settings/secrets/actions) → **New repository secret**.
2. Crie um segredo chamado **NOVAOS_REMOTE_PASSWORD**. Escolha **uma senha nova de pelo menos 16 caracteres**. Não use sua senha do GitHub.
3. Espere o workflow [NovaOS Full ISO (amd64)](https://github.com/Hhhaofuqoc/novaos/actions/workflows/novaos-full-iso.yml) terminar com **success**. A VM busca o artefato mais recente desse workflow, enquanto ele estiver disponível.
4. Acesse [NovaOS Full Remote VM (browser)](https://github.com/Hhhaofuqoc/novaos/actions/workflows/novaos-remote-vm.yml), toque em **Run workflow** e escolha 30, 60 ou 90 minutos.
5. Abra a execução em andamento. Em **Summary** ou no log da etapa `Start temporary authenticated browser desktop`, toque no URL `https://...trycloudflare.com/vnc.html?...`.
6. No navegador Android, informe usuário **nova** e a senha cadastrada no segredo. No noVNC, toque em **Connect** se necessário.

## Segurança e limites

- Sem acesso público direto ao VNC: QEMU e websockify escutam somente em `127.0.0.1`.
- O Nginx verifica a senha antes de servir HTML ou autorizar WebSocket. O workflow se recusa a expor a VM se a verificação HTTP 401 falhar.
- A URL aparece nos logs do repositório público, mas **a senha é um secret do GitHub e nunca é exibida**.
- O túnel HTTPS é temporário, sem garantia de disponibilidade, e desaparece quando a execução termina. Cancelar o workflow encerra a sessão.
- A imagem Live é **efêmera**: alterações dentro da VM **não ficam salvas** depois do desligamento.
- O runner pode não ter aceleração KVM; QEMU via TCG pode ficar lento.
- É um teste interativo temporário, não uma VM permanente.

## Problemas comuns

- **No successful NovaOS Full ISO build found**: construa a ISO pelo outro workflow e espere um resultado `success`.
- **Senha ausente**: crie ou confira o segredo `NOVAOS_REMOTE_PASSWORD` nos Settings.
- **Cloudflare tunnel failed**: houve falha ao criar a URL; execute o workflow novamente.
- **Tela preta / menu de boot**: confirme o progresso do Linux pelo display e consulte os logs; isso não comprova que a NovaShell abriu.
- **Autenticação repetida**: confirme usuário `nova` e o segredo; não coloque credenciais na URL pública.

A autenticação HTTPS não depende de instalar aplicativos além do navegador no Android.
