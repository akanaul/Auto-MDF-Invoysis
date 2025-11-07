# Changelog - Auto MDF InvoISys

## 2025-11-07 - Monitor de progresso sempre visível

- Adicionada `app/progress_overlay.py`, criando um overlay compacto que mantém o progresso e o status da automação visíveis mesmo com a janela principal minimizada.
- Atualizado `app/main_window.py` para acionar o overlay, tornar a barra de progresso da GUI não interativa e reforçar o ciclo de vida dos estados de execução.
- Removida a integração experimental com a barra de tarefas do Windows; o feedback permanece disponível na barra de progresso interna e no overlay flutuante.
- Criados `app/automation_service.py` e `app/progress_watcher.py`, desacoplando a GUI da camada de automação, reduzindo polling e emitindo sinais de progresso.
- Adicionado `app/ui_components.py` com widgets reutilizáveis (painel de progresso, visualizador de logs e painel de configurações) alimentados por `data/automation_settings.py`.
- Persistência e aplicação automática das preferências do PyAutoGUI, além de telemetria leve (`data/automation_telemetry.py`) para falhas de foco e ajustes de configuração.
- Painel de configurações remodelado com aba de temporizadores, multiplicadores independentes para sleeps e destaque permanente de que o failsafe do PyAutoGUI permanece ligado.
- Configurações da automação movidas para a guia "Configurações", incluindo alternância marcada por padrão para manter os tempos originais dos scripts e alerta chamativo para ajustes manuais.
- Reorganizados utilitários da janela principal (ajustes em combos, formatação de logs e construção de linhas) para reduzir duplicação e manter o linting sem pendências.

## 2025-11-06 - Foco unificado no Microsoft Edge e Refatoração

- Adicionada `data/dialog_service.py` para centralizar prompts/alertas Qt e impedir loops de reativação.
- Refatorado `data/automation_focus.py` para suportar apenas o Microsoft Edge, com seletor de janela preferencial e configuração do slot da barra de tarefas.
- Estendidos os utilitários em `data/script_runtime.py`, permitindo seleção explícita de abas via `switch_browser_tab` e restauração de foco mais previsível.
- Atualizada a janela principal (`app/main_window.py`) com textos específicos do Edge, lista de janelas filtrada e novo campo para informar a posição do Edge na barra de tarefas.
- Ajustados os scripts `scripts/ITU X DHL.py` e `scripts/SOROCABA X DHL.py` para aproveitar os novos utilitários, consumir dicas de ambiente e orientar o operador sobre o uso do Edge.
- Documentado o requisito do Edge e as variáveis `MDF_BROWSER_TASKBAR_SLOT` / `MDF_BROWSER_TAB` no README, alinhando instalação e solução de problemas.

## 2025-11-05 - Limpeza de legados

- Removidos os artefatos de GUI legada (`AutoMDF-Start.legacy.py`, `automation_focus.py`, `progress_manager.py`).
- Eliminados os scripts duplicados na raiz (`ITU X DHL.py`, `SOROCABA X DHL.py`) em favor de `scripts/`.
- Excluída a thread de instalação integrada (`app/installer.py`) e o wrapper `dependencias/install.bat`.
- Changelog reescrito para refletir a estrutura atual.
