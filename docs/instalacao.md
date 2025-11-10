# Guia de Instalação - Auto MDF InvoISys

Este guia explica como instalar o Auto MDF InvoISys no seu computador. A instalação é **automática e simples** - o software baixa e instala todas as dependências necessárias sem necessidade de conhecimento técnico avançado. O método mais fácil é simplesmente executar o launcher, que cuida de tudo automaticamente.

## Método Mais Simples: Executar o Launcher (Recomendado)

**Para usuários iniciantes:** Dê duplo clique no arquivo `AutoMDF-Start.py` na pasta do projeto. O launcher vai:

- Criar um ambiente virtual automaticamente (se necessário).
- Baixar e instalar todas as dependências (PySide6, etc.).
- Abrir a interface gráfica do software.

Se tudo estiver correto, a janela principal abrirá diretamente. Se houver problemas, o launcher mostrará mensagens de erro com instruções.

Se houver problemas com o launcher, use os métodos abaixo para instalar manualmente primeiro.

## Instalação Manual (se o Launcher Falhar)

Se o launcher não conseguir instalar automaticamente, siga estes passos para instalar manualmente.

Antes de começar, verifique se o seu computador atende aos seguintes requisitos:

- **Sistema Operacional:** Windows 10/11 ou Linux (como Ubuntu).
- **Navegador:** Microsoft Edge instalado e configurado como navegador padrão (para automações).
- **Acesso à Internet:** Necessário para baixar dependências durante a instalação.
- **Permissões:** Você deve ter permissão para instalar programas no seu computador. Se for um computador de trabalho, peça ajuda ao responsável se necessário.

**Importante:** O software precisa de Python 3.10 ou superior. Se você não tiver, a instalação automática vai tentar instalar, mas pode ser necessário pedir ajuda ao suporte.

## Instalação no Windows

### Passo 1: Baixe ou Copie os Arquivos (Windows)

- Receba os arquivos do projeto (pasta `Auto-MDF-Invoysis`) e descompacte em um local fácil de acessar, como `C:\Projetos\Auto-MDF-Invoysis`. Evite pastas com espaços no nome se possível.

### Passo 2: Execute o Instalador (Windows)

**Método Simples (Recomendado):** Dê duplo clique no arquivo `install\install.bat` na pasta do projeto. O instalador vai executar automaticamente, procurando o Python e baixando as dependências necessárias.

**Método Alternativo (Terminal):** Se preferir ou se o duplo clique não funcionar:

1. Abra o **Prompt de Comando** (pesquise por "cmd" no menu Iniciar).
2. Navegue até a pasta do projeto: digite `cd C:\Projetos\Auto-MDF-Invoysis` e pressione Enter.
3. Execute o instalador: digite `install\install.bat` e pressione Enter.
   - O instalador vai procurar o Python automaticamente e criar um ambiente virtual (uma "caixa" isolada para o software).
   - Você verá mensagens no terminal mostrando o progresso. Aguarde até ver "Instalação concluída com sucesso!".
4. Se houver erros, anote a mensagem e consulte a seção [Solução de Problemas](problemas.md).

### Passo 3: Verifique a Instalação (Windows)

**Método Simples (Recomendado):** Dê duplo clique no arquivo `AutoMDF-Start.py` na pasta do projeto. Uma janela gráfica deve abrir automaticamente.

**Método Alternativo (Terminal):** Se preferir ou se o duplo clique não funcionar:

- Abra o Prompt de Comando, navegue até a pasta e digite `python AutoMDF-Start.py`.
- Uma janela gráfica deve abrir. Se abrir, a instalação foi bem-sucedida. Feche a janela por enquanto.

## Instalação no Linux

### Passo 1: Baixe ou Copie os Arquivos (Linux)

- Receba os arquivos do projeto e descompacte em uma pasta, como `/home/seu_usuario/Auto-MDF-Invoysis`.

### Passo 2: Execute o Instalador (Linux)

**Método Simples (Recomendado):** Dê duplo clique no arquivo `install/install.sh` na pasta do projeto (se o seu gerenciador de arquivos suportar execução de scripts). O instalador vai executar automaticamente e instalar as dependências.

**Método Alternativo (Terminal):** Se preferir ou se o duplo clique não funcionar:

1. Abra o **Terminal** (pesquise por "terminal" no menu).
2. Navegue até a pasta: digite `cd /home/seu_usuario/Auto-MDF-Invoysis` e pressione Enter.
3. Torne o script executável: digite `chmod +x install/install.sh` e pressione Enter.
4. Execute o instalador: digite `./install/install.sh` e pressione Enter.
   - O instalador vai instalar as dependências automaticamente.
   - Aguarde as mensagens de progresso.
5. Se houver erros, consulte [Solução de Problemas](problemas.md).

### Passo 3: Verifique a Instalação (Linux)

- Digite `python3 AutoMDF-Start.py` no Terminal.
- Uma janela gráfica deve abrir. Se abrir, está tudo certo.

## Instalação Manual (se Automática Falhar)

Se a instalação automática não funcionar, siga estes passos manuais (ou peça ajuda ao TI):

1. Instale Python 3.10+ do site oficial (python.org). Marque a opção para adicionar ao PATH durante a instalação.
2. Abra o Prompt de Comando/Terminal na pasta do projeto.
3. Digite `python -m venv .venv` para criar o ambiente virtual.
4. Ative o ambiente:
   - Windows: `.venv\Scripts\activate.bat`
   - Linux: `source .venv/bin/activate`
5. Instale dependências: `pip install -r requirements.txt`.
6. Teste: `python AutoMDF-Start.py`.

## Após a Instalação

- **Primeira Execução:** Execute `python AutoMDF-Start.py` para abrir a interface.
- **Configuração Inicial:** Na aba "Configurações", ajuste opções se necessário (padrões geralmente funcionam).
- **Logs:** Verifique a pasta `logs/` se algo der errado.

Se encontrar problemas, consulte [Solução de Problemas](problemas.md) ou entre em contato com o suporte.

---

**Dica:** Guarde este guia em um local acessível para referência futura.
