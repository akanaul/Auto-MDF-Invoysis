# Guia de Uso - Auto MDF InvoISys

Este guia explica como usar o Auto MDF InvoISys após a instalação. O software é projetado para ser **extremamente simples** - você pode iniciar tudo com um duplo clique no launcher `AutoMDF-Start.py`, que cuida da instalação automática se necessário e abre a interface gráfica diretamente.

## Iniciando o Software

**Método Mais Simples (Recomendado):** Dê duplo clique no arquivo `AutoMDF-Start.py` na pasta do projeto. O launcher vai verificar e instalar dependências automaticamente (se necessário) e abrir a interface gráfica diretamente.

**Método Alternativo (Terminal):** Se preferir ou se o duplo clique não funcionar:

1. Abra o **Prompt de Comando** (Windows) ou **Terminal** (Linux).
2. Navegue até a pasta do projeto (ex.: `cd C:\Projetos\Auto-MDF-Invoysis`).
3. Digite `python AutoMDF-Start.py` e pressione Enter.
4. Uma janela chamada "Auto MDF InvoISys" vai abrir. Isso é a interface principal.

Se a janela não abrir, consulte [Solução de Problemas](problemas.md).

## Entendendo a Interface

A janela principal tem:

- **Lista de Scripts:** À esquerda, uma lista de automações disponíveis (ex.: "ITU X DHL.py", "SOROCABA X DHL.py").
- **Botões de Controle:** No centro, botões como "Iniciar", "Parar", "Exportar Log" e "Abrir Log".
- **Área de Logs:** Embaixo, uma caixa de texto mostrando mensagens do que está acontecendo.
- **Barra de Progresso:** Uma barra que mostra o andamento da automação.
- **Abas:** No topo, abas como "Principal" e "Configurações".

## Executando uma Automação

1. Na lista de scripts, selecione o que você quer executar (ex.: clique em "ITU X DHL.py").
2. Clique no botão **Iniciar**.
3. O software vai:
   - Abrir o Microsoft Edge automaticamente.
   - Navegar para o site do Invoisys.
   - Preencher formulários e gerar o MDF-e.
4. Observe a barra de progresso e os logs para ver o andamento.
5. Quando terminar, você verá uma mensagem de sucesso nos logs.

**Importante:** Não mexa no mouse ou teclado enquanto a automação estiver rodando. O software controla o navegador sozinho.

## Parando uma Automação

- Clique no botão **Parar** se precisar interromper.
- O software vai tentar parar de forma segura.

## Configurações

Na aba "Configurações":

- **Usar Tempos Padrão:** Deixe marcado para usar configurações recomendadas.
- **Temporizadores:** Ajuste pausas se a automação estiver muito rápida ou lenta (ex.: aumente "Pausa PyAutoGUI" se houver erros).
- **Posição do Edge:** Configure onde o Edge fica na barra de tarefas (ex.: posição 1, 2, etc.).

Salve as mudanças clicando em "Aplicar".

## Visualizando Logs

- **Durante Execução:** Veja mensagens em tempo real na área de logs.
- **Após Execução:** Clique em "Exportar Log" para salvar em um arquivo, ou "Abrir Log" para ver arquivos antigos na pasta `logs/`.

## Dicas de Segurança

- Sempre faça login no Invoisys antes de executar, se necessário.
- Verifique se o Edge está fechado antes de iniciar.
- Não execute múltiplas automações ao mesmo tempo.
- Se algo der errado, pare imediatamente e consulte os logs.

## Saindo do Software

- Feche a janela clicando no "X" no canto superior direito.
- O software vai salvar configurações automaticamente.

Se tiver dúvidas, consulte [Perguntas Frequentes](faq.md) ou [Solução de Problemas](problemas.md).
