# Changelog - Auto MDF InvoISys

## 2025-11-09 - Correções de Barra de Progresso e Melhorias de Estabilidade

- **Barra de Progresso Linear:** Corrigida regressão na barra de progresso que causava avanço não-linear (ex.: 65% → 30%). Padronizados checkpoints de progresso entre scripts ITU X DHL.py e SOROCABA X DHL.py com 17 pontos idênticos de 5% a 90%. Implementado salvamento automático de progresso em tempo real para atualização fluida da interface.
- **Melhorias de Foco do Navegador:** Ajustado parâmetro `preserve_tab` para manter aba selecionada durante foco. Adicionado delay de 0.5s antes de troca de abas para estabilidade. Aumentado intervalo de retry de foco para 4 segundos.
- **Tratamento de Failsafe:** Implementado handler específico para failsafe do PyAutoGUI, permitindo ao usuário escolher continuar ou parar a automação via diálogo.
- **Desativação Automática de Caps Lock:** Adicionada função `disable_caps_lock()` para garantir entrada consistente de texto maiúsculo/minúsculo.
- **Interface Sempre Visível:** Diálogos de prompt, alerta e confirmação agora ficam sempre no topo da tela para evitar perda de foco.
- **Otimização de Performance:** Reduzido intervalo de atualização de progresso de 1000ms para 200ms para feedback mais responsivo. Desabilitado bridge ativo para evitar travamentos.
- **Scripts de Teste:** Criados scripts de teste para validação de progresso em tempo real (`test_realtime_progress.py`, `test_realtime_save.py`, `test_tracing.py`, `test_progress_realtime.py`).
- **Correções de Configuração:** Ajustado `focus_retry_seconds` de 3.0 para 4.0s. Habilitado `use_default_timers` por padrão para manter compatibilidade.

## 2025-11-08 - Otimizações de Código, Documentação Completa e Ajustes Empresariais

- **Otimização de Código:** Adicionados helpers `_build_install_error_details` e `_build_missing_modules_details` em `AutoMDF-Start.py` para mensagens de erro mais claras e consistentes. Incluídos type hints em `install/install.py` para melhor manutenção.
- **Correções:** Ajustado caminho de importação em `tests/settings_roundtrip.py` para testes funcionarem corretamente. Removidos wrappers obsoletos `tools/install.py` e `tools/find_python.ps1`.
- **Documentação Completa:** Criada pasta `docs/` com documentação abrangente em português para usuários finais: README da documentação, guia de instalação, guia de uso, solução de problemas e FAQ. Linguagem simplificada, com ênfase na simplicidade.
- **Launcher como Método Principal:** Confirmado que `AutoMDF-Start.py` faz instalação automática completa (ambiente virtual + dependências). Atualizado README e documentação para priorizar duplo clique no launcher como método mais intuitivo.
- **README Atualizado:** Reorganizado para destacar launcher automático, documentação completa e melhorias recentes. Seção de instalação simplificada com método automático como padrão.
- **Ajustes Empresariais:** Adicionada proteção contra execução simultânea em módulos principais. Criado script de teste de stress de logs (`scripts/log_stress_test.py`) para validação corporativa. Adicionado arquivo de teste de foco (`test_focus.py`) para diagnóstico. Reforçado estado de progresso com dados completos para recuperação de sessão.

## 2025-11-07 - Monitor de Progresso Sempre Visível e Customização Avançada

- **Monitor de Progresso:** Adicionada `app/progress_overlay.py`, criando overlay compacto que mantém progresso e status visíveis mesmo com janela minimizada. Atualizado `app/main_window.py` para acionar overlay e reforçar ciclo de vida dos estados.
- **Customização de Temporizadores:** Adicionada configuração avançada com multiplicadores independentes para sleeps do PyAutoGUI. Destaque permanente do failsafe ativo.
- **Desacoplamento da Interface:** Criados `app/automation_service.py` e `app/progress_watcher.py` para reduzir polling e emitir sinais de progresso. Adicionado `app/log_manager.py` para gerenciamento centralizado de logs.
- **Componentes Reutilizáveis:** Criado `app/ui_components.py` com widgets para painel de progresso, visualizador de logs e configurações.
- **Persistência e Telemetria:** Implementada persistência de configurações em `data/automation_settings.py` e telemetria leve em `data/automation_telemetry.py` para falhas de foco.
- **Layout Aprimorado:** Painel de configurações remodelado com aba de temporizadores. Configurações da automação movidas para guia própria com alertas visuais. Reorganizados utilitários da janela principal para reduzir duplicação.

## 2025-11-06 - Foco Unificado no Edge e Refatoração Completa

- **Foco no Microsoft Edge:** Refatorado `data/automation_focus.py` para suportar apenas Edge, com seletor de janela preferencial e configuração do slot da barra de tarefas. Atualizada interface com textos específicos do Edge.
- **Centralização de Diálogos:** Adicionada `data/dialog_service.py` para centralizar prompts/alertas Qt e impedir loops de reativação.
- **Utilitários Estendidos:** Melhorados utilitários em `data/script_runtime.py` com seleção explícita de abas via `switch_browser_tab` e restauração de foco mais previsível.
- **Scripts Atualizados:** Ajustados scripts `scripts/ITU X DHL.py` e `scripts/SOROCABA X DHL.py` para aproveitar novos utilitários e orientar sobre uso do Edge.
- **Documentação Atualizada:** Requisito do Edge documentado no README com variáveis `MDF_BROWSER_TASKBAR_SLOT` / `MDF_BROWSER_TAB`.

## 2025-11-05 - GUI Moderna Completa e Limpeza de Legados

- **GUI Moderna em PySide6:** Implementação completa de interface moderna com arquitetura modular. Criados módulos `app/main_window.py`, `app/runner.py`, `app/dialogs.py`.
- **Sistema de Progresso:** Implementado gerenciamento avançado com `data/progress_manager.py` e `data/automation_progress.json`.
- **Execução Controlada:** Adicionado `data/script_runtime.py` para execução controlada de scripts.
- **Instaladores Unificados:** Criados `install.bat`, `install_user.bat`, `install.sh` com lógica consistente.
- **Organização de Scripts:** Automação movida para pasta `scripts/` com melhor isolamento.
- **Limpeza de Legados:** Removidos artefatos antigos (`AutoMDF-Start.legacy.py`, arquivos duplicados na raiz, `app/installer.py`, wrappers obsoletos).
- **Documentação Atualizada:** README e CHANGELOG reescritos para refletir nova estrutura.

## 2025-11-03 - Versão Inicial da GUI Funcional

- Primeira implementação de interface gráfica funcional em PySide6.
- Criado launcher `AutoMDF-Start.py` com lógica de instalação automática.
- Adicionados scripts básicos de instalação (`install.bat`, `install_user.bat`).
- Implementado gerenciamento básico de progresso.
- Estrutura inicial de CHANGELOG e documentação.
