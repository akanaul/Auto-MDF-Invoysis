# Auto MDF InvoISys

Automacao do fluxo MDF-e com uma central moderna em PySide6. A aplicacao oferece um painel unico para iniciar scripts, acompanhar logs e responder dialogos emitidos pelos robos sem depender do antigo front-end Tkinter.

## Principais recursos
- Janela unica em PySide6 com selecao de scripts, logs em tempo real e barra de progresso.
- Bridge Qt intercepta alertas, prompts e confirms emitidos pelos scripts e mostra dialogos nativos.
- Modulo data/automation_focus.py garante que o navegador correto esteja ativo.
- ProgressManager em data/progress_manager.py grava estado em data/automation_progress.json para feedback constante.
- Cada execucao gera logs dedicados em logs/ e protege contra execucoes simultaneas.

## Requisitos
- Python 3.10 ou superior (Windows recomendado).
- Acesso ao Invoisys e ao portal de averbacao autenticados.
- Permissao para instalar dependencias Python (PySide6, pyautogui, pyperclip, pygetwindow).

## Instalacao
### Windows com virtualenv (padrao)
1. Abra o Prompt de Comando na raiz do projeto.
2. Execute install.bat para criar .venv e instalar dependencias.
3. Inicie a GUI com python AutoMDF-Start.py (o launcher relanca dentro da .venv automaticamente).

### Windows com --user
1. Rode install_user.bat para instalar apenas no perfil atual.
2. Opcionalmente crie uma .venv manualmente se preferir isolar o ambiente.

### Linux, macOS ou Codespaces
1. Torne o script executavel com chmod +x install.sh.
2. Execute ./install.sh.
3. Rode python AutoMDF-Start.py dentro do ambiente configurado.

### Instalacao manual
1. python -m venv .venv
2. Ative o ambiente (Windows: .\.venv\Scripts\activate, Linux/macOS: source .venv/bin/activate).
3. pip install -r requirements.txt

## Inicio rapido
1. Execute python AutoMDF-Start.py.
2. Aguarde o launcher criar ou ativar a .venv e conferir dependencias.
3. Selecione um script da pasta scripts/.
4. Clique em Iniciar para rodar. Use Parar para encerrar a execucao atual.
5. Utilize Exportar Log ou Abrir Log para acessar os registros em logs/.

## Execucao direta de scripts
Os scripts continuam executaveis via linha de comando (ideal para depuracao):

    python "scripts/ITU X DHL.py"
    python "scripts/SOROCABA X DHL.py"

Quando executados fora da GUI, os scripts usam dialogs Tkinter de emergencia, mas o comportamento preferencial permanece atraves do bridge Qt.

## Estrutura do projeto
```
Auto-MDF-Invoysis/
|-- AutoMDF-Start.py        # Launcher principal (cria .venv e inicia PySide6)
|-- app/                    # Codigo da interface moderna
|   |-- main.py             # Entry point da QApplication
|   |-- main_window.py      # Janela principal e logica de UI
|   |-- runner.py           # Gerencia a execucao dos scripts
|   `-- dialogs.py          # Dialogos usados pelo bridge
|-- data/
|   |-- automation_focus.py # Rotinas de foco do navegador
|   |-- progress_manager.py # Persistencia do progresso em JSON
|   `-- automation_progress.json
|-- scripts/                # Automacoes MDF-e (ITU, Sorocaba e outras)
|-- tools/install.py        # Instalador unificado de dependencias
|-- install.bat / install_user.bat / install.sh
|-- requirements.txt
|-- logs/
`-- CHANGELOG.md
```

## Dicas e solucao de problemas
- PySide6 nao encontrado: execute install.bat ou install_user.bat ou rode python tools/install.py --mode venv.
- Nenhum script listado: confirme que arquivos .py estao dentro de scripts/ e que o nome termina com .py.
- Logs vazios: verifique permissoes de escrita em logs/ e se o antivirus nao bloqueia a pasta.
- Erro de foco no navegador: valide se o navegador esta aberto e fixado na barra de tarefas; ajuste MDF_BROWSER_TAB se necessario.
- Dependencias extras: execute python AutoMDF-Start.py e use os botoes de verificar ou instalar dependencias.

## Uso
Este repositorio destina-se ao time interno de automacao. Consulte os responsaveis antes de redistribuir ou adaptar para outros contextos.
