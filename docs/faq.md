# Perguntas Frequentes - Auto MDF InvoISys

Aqui estão as perguntas mais comuns sobre o Auto MDF InvoISys. Se sua dúvida não estiver aqui, consulte [Solução de Problemas](problemas.md) ou entre em contato com o suporte.

## Sobre o Software

### O que é o Auto MDF InvoISys?

É uma ferramenta de automação que ajuda a processar MDFs (Manifestos de Documentos Fiscais) no sistema Invoisys, reduzindo trabalho manual e erros.

### Para que serve?

Automatiza tarefas repetitivas no Invoisys, como preenchimento de formulários, validações e geração de relatórios, economizando tempo e evitando erros humanos.

### É seguro usar?

Sim, o software apenas simula ações humanas no navegador. Não acessa dados confidenciais além do necessário para a automação.

## Instalação e Configuração

### Preciso de conhecimentos avançados para instalar?

Não, os instaladores automatizam tudo. Basta seguir o guia em [Instalação](instalacao.md). Se houver problemas, consulte [Solução de Problemas](problemas.md).

### Funciona em qualquer computador?

Funciona em Windows e Linux. Requer Python 3.10+ e Microsoft Edge. Em alguns ambientes, pode precisar de permissões especiais.

### Posso instalar em vários computadores?

Sim, mas cada instalação é independente. Copie os arquivos para cada máquina e execute o instalador.

## Uso do Software

### Como iniciar o software?

Execute o launcher `AutoMDF-Start.py` (duplo clique ou via terminal). Ele verifica e instala dependências automaticamente na primeira execução, depois abre a interface gráfica.

### O que são os "scripts" disponíveis?

São automações específicas para diferentes locais ou tipos de MDF. Escolha o script adequado na interface.

### Posso personalizar as automações?

As configurações básicas (como pausas e posições) podem ser ajustadas na aba "Configurações". Modificações avançadas requerem conhecimento técnico.

### O software salva meus dados?

Salva configurações locais e logs de execução. Não armazena dados do Invoisys permanentemente.

## Automação e Execução

### O que acontece durante a execução?

O software controla o Microsoft Edge automaticamente, preenchendo formulários e clicando botões como um usuário faria.

### Posso usar o computador durante a execução?

Não recomendado. O software precisa de foco exclusivo no navegador. Use outro computador ou aguarde a conclusão.

### Quanto tempo leva uma automação?

Depende do volume de dados e configurações de pausa. Pode levar de minutos a horas. Monitore a barra de progresso precisa que avança linearmente de 5% a 90%.

### E se der erro durante a execução?

A automação para automaticamente. Verifique logs para detalhes e consulte [Solução de Problemas](problemas.md).

## Suporte e Manutenção

### Como obter suporte?

Entre em contato com o suporte. Forneça logs da pasta `logs/` e descrição do problema.

### O software é atualizado?

Sim, novas versões podem ser lançadas. Baixe a versão mais recente e reinstale quando disponível.

### Posso sugerir melhorias?

Sim, envie sugestões ao suporte. Elas ajudam a melhorar o software para todos.

### Há custos para usar?

O software é gratuito. Não há custos de licença.

## Segurança e Conformidade

### O software atende às políticas de segurança?

Foi desenvolvido seguindo boas práticas. Em alguns ambientes, consulte o responsável antes de usar.

### Meus dados estão seguros?

O software não transmite dados para servidores externos. Tudo roda localmente no seu computador.

### Posso usar em produção?

Sim, mas sempre teste primeiro em ambiente controlado, conforme recomendado na [Instalação](instalacao.md).

Para mais detalhes, consulte os outros guias: [Instalação](instalacao.md), [Uso](uso.md), [Solução de Problemas](problemas.md).
