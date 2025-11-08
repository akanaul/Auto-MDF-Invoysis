# Solução de Problemas - Auto MDF InvoISys

Este guia ajuda a resolver problemas comuns ao usar o Auto MDF InvoISys. Se o problema não estiver aqui, anote a mensagem de erro e entre em contato com o suporte.

## Problemas de Instalação

### "Python não encontrado" ou "Nao foi possivel localizar Python"

- **Causa:** Python não está instalado ou não está no PATH.
- **Solução:**
  1. Baixe Python 3.10+ de python.org.
  2. Durante a instalação, marque "Add Python to PATH".
  3. Reinicie o computador e tente instalar novamente.
  4. Se for um computador de trabalho, peça ao responsável para instalar.

### Instalação falha com erro de pip

- **Causa:** Problema de rede ou permissões.
- **Solução:**
  1. Verifique conexão com a internet.
  2. Execute como administrador (Windows) ou com sudo (Linux).
  3. Tente a instalação manual: siga os passos em [Instalação](instalacao.md).

### "Ambiente virtual não localizado"

- **Causa:** Problema na criação do .venv.
- **Solução:** Delete a pasta `.venv` e execute o instalador novamente.

## Problemas ao Iniciar o Software

### Janela não abre ao executar `python AutoMDF-Start.py`

- **Causa:** Dependências faltando ou erro no Python.
- **Solução:**
  1. Verifique se a instalação foi concluída.
  2. Execute `python -c "import PySide6; print('OK')"` no terminal. Se der erro, reinstale.
  3. Verifique logs em `logs/startup-install.log`.

### Erro "ModuleNotFoundError"

- **Causa:** Ambiente virtual não ativado.
- **Solução:** Certifique-se de executar de dentro da pasta do projeto. O launcher ativa automaticamente.

## Problemas Durante Execução

### Automação não inicia ou para imediatamente

- **Causa:** Edge não está aberto ou na posição errada.
- **Solução:**
  1. Abra o Microsoft Edge.
  2. Fixe-o na barra de tarefas (clique direito > "Fixar na barra de tarefas").
  3. Na aba "Configurações", ajuste "Posição do Edge" (ex.: 1 para primeira posição).
  4. Certifique-se de estar logado no Invoisys.

### "Foco perdido" ou "Elemento não encontrado"

- **Causa:** Janela do navegador mudou ou site carregou lentamente.
- **Solução:**
  1. Não mexa no mouse/teclado durante execução.
  2. Aumente pausas em "Configurações" > "Temporizadores".
  3. Feche outras janelas para evitar interferência.

### Barra de progresso para mas logs mostram erro

- **Causa:** Erro no script de automação.
- **Solução:**
  1. Pare a execução.
  2. Verifique logs detalhados.
  3. Tente novamente. Se persistir, reporte ao suporte.

### Software congela ou não responde

- **Causa:** Loop infinito ou erro interno.
- **Solução:**
  1. Force fechar a janela.
  2. Reinicie o software.
  3. Verifique logs para detalhes.

## Problemas Gerais

### Logs vazios ou não salvam

- **Causa:** Permissões de escrita.
- **Solução:** Execute como administrador ou verifique se a pasta `logs/` existe e é gravável.

### Erro de rede ou "No matching distribution"

- **Causa:** Problema com PySide6 ou pip.
- **Solução:** Instale Python 3.12 (última versão recomendada) e tente novamente.

### Computador de trabalho bloqueia instalação

- **Causa:** Políticas de segurança.
- **Solução:** Peça ao responsável para instalar Python e dar permissões.

## Como Obter Ajuda

1. Anote a mensagem de erro completa.
2. Verifique logs em `logs/`.
3. Consulte [Perguntas Frequentes](faq.md).
4. Entre em contato com o suporte técnico da empresa, enviando logs e descrição do problema.

**Dica:** Sempre teste em um ambiente controlado antes de usar em produção.
