# Auto MDF InvoISys

Automação do fluxo MDF-e com uma central moderna em PySide6. A aplicação oferece um painel único para iniciar scripts, acompanhar logs e responder diálogos emitidos pelos robôs sem depender do front-end legado anterior.

**📚 Documentação Completa:** Para guias detalhados de instalação, uso e solução de problemas, consulte a pasta `docs/` com documentação completa em português para usuários finais.

**✨ Melhorias Recentes:** Código otimizado com type hints, tratamento de erros aprimorado, instalação automática via launcher, e documentação completa para facilitar o uso.

## Principais recursos

- Janela única em PySide6 com seleção de scripts, logs em tempo real e barra de progresso.
- Indicador flutuante sempre visível para acompanhar o andamento das automações.
- Painel de configurações em guia própria, com opção padrão para manter os tempos originais dos scripts e aba de temporizadores para ajustar pausa do PyAutoGUI, tentativas extras de foco e multiplicadores de `sleep` com lembrete visual do failsafe sempre ativo.
- Bridge Qt intercepta alertas, prompts e *confirms* emitidos pelos scripts e mostra diálogos nativos.
- Módulo `data/automation_focus.py` garante que o navegador correto esteja ativo.
- `ProgressManager` em `data/progress_manager.py` grava estado em `data/automation_progress.json` para feedback constante.
- Cada execução gera logs dedicados em `logs/` e protege contra execuções simultâneas.

## Requisitos

- Python 3.10 ou superior (Windows recomendado).
- Microsoft Edge instalado e fixado na barra de tarefas.
- Acesso ao Invoisys e ao portal de averbação autenticados.
- Permissão para instalar dependências Python (PySide6, PyAutoGUI, pyperclip, pygetwindow).

## Documentação

Para guias detalhados de instalação, uso e solução de problemas, consulte a pasta `docs/`:

- [README da Documentação](docs/README.md) - Visão geral e links para todos os guias
- [Instalação](docs/instalacao.md) - Guia passo-a-passo para instalar em Windows/Linux
- [Uso](docs/uso.md) - Como usar a interface e executar automações
- [Solução de Problemas](docs/problemas.md) - Resolução de erros comuns
- [Perguntas Frequentes](docs/faq.md) - Respostas para dúvidas comuns

## Instalação

### Método Mais Simples (Recomendado)

1. Dê duplo clique no arquivo `AutoMDF-Start.py` na raiz do projeto.
2. O launcher vai criar o ambiente virtual e instalar todas as dependências automaticamente.
3. A interface gráfica abrirá quando tudo estiver pronto.

### Instalação Manual (Alternativa)

Se preferir instalar manualmente ou se o launcher encontrar problemas:

### Instalação manual

1. `python -m venv .venv`
2. Ative o ambiente (Windows: `.\.venv\Scripts\activate`, Linux/macOS: `source .venv/bin/activate`).
3. `pip install -r requirements.txt`

## Início rápido

1. Dê duplo clique em `AutoMDF-Start.py` (o launcher instala tudo automaticamente na primeira execução).
2. Selecione um script da pasta `scripts/`.
3. Clique em **Iniciar** para rodar. Use **Parar** para encerrar a execução atual.
4. Ajuste, se necessário, as preferências na aba **Configurações** (por padrão a opção "Usar tempos padrão do script" mantém os timers originais).
5. Utilize **Exportar Log** ou **Abrir Log** para acessar os registros em `logs/`.

## Execução direta de scripts

Os scripts continuam executáveis via linha de comando (ideal para depuração):

```bash
python "scripts/ITU X DHL.py"
python "scripts/SOROCABA X DHL.py"
```

Quando executados fora da GUI, os scripts criam diálogos mínimos em PySide6, preservando a experiência consistente do *bridge* Qt.

## Estrutura do projeto

```text
Auto-MDF-Invoysis/
|-- AutoMDF-Start.py        # Launcher principal (cria .venv e inicia PySide6)
|-- app/                    # Código da interface moderna
|   |-- main.py             # Entry point da QApplication
|   |-- main_window.py      # Janela principal e lógica de UI
|   |-- automation_service.py # Coordena execução, foco e telemetria
|   |-- progress_overlay.py # Overlay flutuante com o status atual
|   |-- progress_watcher.py # Observa o JSON de progresso e emite sinais
|   |-- ui_components.py    # Widgets reutilizáveis (log, painel, configs)
|   |-- runner.py           # Gerencia a execução dos scripts
|   `-- dialogs.py          # Diálogos usados pelo bridge
|-- data/
|   |-- automation_focus.py # Rotinas de foco do navegador
|   |-- automation_settings.py # Preferências persistidas da automação
|   |-- automation_telemetry.py # Registro de telemetria amigável
|   |-- progress_manager.py # Persistência do progresso em JSON
|   `-- automation_progress.json
|-- scripts/                # Automações MDF-e (Itu, Sorocaba e outras)
|-- install/                # Instaladores unificados (Python, PowerShell, Bash)
|   |-- install.py          # Lógica principal de instalação (venv/user/system)
|   |-- install.bat         # Instalador Windows (.venv)
|   |-- install_user.bat    # Instalador Windows (--user)
|   |-- install.sh          # Instalador Linux/macOS
|   `-- find_python.ps1     # Descoberta de Python 3.10+
|-- requirements.txt
|-- logs/
`-- CHANGELOG.md
```

## Dicas e solução de problemas

- PySide6 não encontrado: execute `install\install.bat`, `install\install_user.bat` ou rode `python install/install.py --mode venv`.
- Nenhum script listado: confirme que arquivos `.py` estão dentro de `scripts/` e que o nome termina com `.py`.
- Logs vazios: verifique permissões de escrita em `logs/` e se o antivírus não bloqueia a pasta.
- Erro de foco no navegador: a automação oferece suporte apenas ao Microsoft Edge. Confirme que ele está aberto e fixado na posição configurada da barra de tarefas (Win+Número). Ajuste `MDF_BROWSER_TAB` e `MDF_BROWSER_TASKBAR_SLOT` se necessário.
- Edge em posição diferente: utilize a opção "Posição do Edge na barra de tarefas" na GUI ou defina `MDF_BROWSER_TASKBAR_SLOT` antes de iniciar a automação.
- Dependências extras: execute `python AutoMDF-Start.py` e use os botões de verificar ou instalar dependências.

## Uso

Este repositório destina-se ao time interno de automação. Consulte os responsáveis antes de redistribuir ou adaptar para outros contextos.
