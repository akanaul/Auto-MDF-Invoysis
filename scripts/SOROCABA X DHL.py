# IMPORTAR BIBLIOTECLA E RECURSOS
import ctypes
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, cast

import pyautogui
import pyperclip

try:
    from data.automation_focus import focus
    from data.progress_manager import ProgressManager
    from data.script_runtime import (
        DEFAULT_TOTAL_STEPS,
        abort as _abort,
        alert_topmost,
        apply_pyautogui_bridge,
        confirm_topmost,
        configure_stdio,
        disable_caps_lock,
        ensure_browser_focus,
        prompt_topmost,
        register_exception_handler,
        switch_browser_tab,
        wait_for_form_load,
        wait_for_invoisys_form,
        wait_for_page_reload_and_form,
        extract_cte_number,
    )
except ModuleNotFoundError:
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from data.automation_focus import focus
    from data.progress_manager import ProgressManager
    from data.script_runtime import (
        DEFAULT_TOTAL_STEPS,
        abort as _abort,
        alert_topmost,
        apply_pyautogui_bridge,
        confirm_topmost,
        configure_stdio,
        disable_caps_lock,
        ensure_browser_focus,
        prompt_topmost,
        register_exception_handler,
        switch_browser_tab,
        wait_for_form_load,
        wait_for_invoisys_form,
        wait_for_page_reload_and_form,
        extract_cte_number,
    )

pyautogui = cast(Any, pyautogui)
configure_stdio()
apply_pyautogui_bridge(pyautogui)

progress = ProgressManager(auto_save=False)
progress.start(total_steps=DEFAULT_TOTAL_STEPS)
register_exception_handler(progress)
progress.add_log('Automação iniciada')
#---------------------------------------------------------------

#---------------------------------------------------------------
# ABRIR NAVEGADOR
time.sleep(1)
try:
    initial_tab = int(os.environ.get('MDF_BROWSER_TAB', '').strip() or '0')
except ValueError:
    initial_tab = 0
window_hint = os.environ.get('MDF_BROWSER_TITLE_HINT', '').strip()

focus.prepare_for_execution()
if window_hint:
    try:
        focus.set_preferred_window_title(window_hint)
    except Exception:
        pass
if initial_tab > 0:
    try:
        focus.target_tab = initial_tab
    except Exception:
        pass
focus.launch_taskbar_slot()
ensure_browser_focus(
    target_tab=initial_tab if initial_tab > 0 else None,
    preserve_tab=initial_tab <= 0,
)
time.sleep(1)
progress.update(5, 'Navegador em foco')
print('[AutoMDF] Navegador preparado', flush=True)
#---------------------------------------------------------------

#GAP
pyautogui.press('enter')
pyautogui.hotkey('ctrl', 'shift', 'a')
time.sleep(0.2)


# IR PARA 1ª ABA DO NAVEGADOR
ensure_browser_focus()
time.sleep(0.5)
#---------------------------------------------------------------

#PESQUISAR E BAIXAR CTE
pyautogui.hotkey('ctrl', 'f')
pyautogui.write('FINAL', interval=0.20)
pyautogui.press('esc')
time.sleep(0.2)

for _ in range(4):
    pyautogui.press('tab')
    time.sleep(0.2)

time.sleep(0.5)
#PROMPT DE COMANDO PARA DIGITAR A DT
codigo = prompt_topmost(
    text='Digite o número do DT:',
    title='DT',
    require_input=True,
    cancel_message='Cancelar a inserção do número do DT interrompe a automação. Deseja cancelar mesmo assim?'
)

if not codigo:
    pyautogui.FAILSAFE = True
    _abort(progress, 'Nenhum código DT informado. A automação foi encerrada.')

codigo = cast(str, codigo).strip()
if not codigo:
    pyautogui.FAILSAFE = True
    _abort(progress, 'Nenhum código DT informado. A automação foi encerrada.')
pyautogui.write(codigo.upper(), interval=0.1)
pyautogui.press('enter')
time.sleep(0.3)
pyautogui.press('enter')
time.sleep(0.5)
progress.update(15, 'DT localizado e carregado')
print('[AutoMDF] DT localizado', flush=True)
#---------------------------------------------------------------

#ALERTA
alert_topmost(
    'Antes de prosseguir:\n\n'
    '1. Confirme que o Microsoft Edge está aberto com as abas necessárias do Invoisys;\n'
    '2. Baixe o arquivo XML;\n'
    '3. Garanta que o site de averbação esteja logado no Edge.\n\n'
    'OBS: Para interromper o processo, deslize o mouse repetidamente em direção ao canto superior direito da tela'
)
time.sleep(2)
progress.update(20, 'Aguardando download do XML e validações iniciais')
print('[AutoMDF] Instruções exibidas ao operador', flush=True)
#---------------------------------------------------------------

#DESATIVAR CAPS LOCK
disable_caps_lock()

#---------------------------------------------------------------

# IR PARA 3ª ABA DO NAVEGADOR (INVOISYS - PARA ABRIR FORMULÁRIO)
switch_browser_tab(3)
time.sleep(1)

#-----------------------------------------------------#-----------------------------------------------------------------#
#-----------------------------------------------------#-----------------------------------------------------------------#
#						DADADOS DO MDF-E							#


# ABRIR DADOS DO MDF-E
pyautogui.hotkey('ctrl', 'f')
pyautogui.write('EMITIR NOTA', interval=0.10)
pyautogui.press('esc')
pyautogui.press('enter')
time.sleep(0.5)
pyautogui.hotkey('ctrl', 'f')
pyautogui.write('MDF-E', interval=0.10)
pyautogui.press('esc')
pyautogui.press('enter')
#---------------------------------------------------------------

# AGUARDAR PÁGINA RECARREGAR E FORMULÁRIO CARREGAR (SEQUENCIAL)
print('[AutoMDF] Aguardando recarregamento da página e carregamento do formulário MDF-e...', flush=True)
if wait_for_page_reload_and_form(timeout=15.0):
    print('[AutoMDF] Formulário MDF-e detectado após recarregamento da página!', flush=True)
else:
    raise RuntimeError("Formulário MDF-e não foi detectado após recarregamento da página (15s). Verifique se o sistema Invoisys está funcionando corretamente.")

progress.update(25, 'Formulário MDF-e aberto')
print('[AutoMDF] Formulário MDF-e aberto', flush=True)
#---------------------------------------------------------------

## DADOS DO MDFE: PRESTADPR DE SERVIÇO
pyautogui.hotkey('ctrl', 'f')
pyautogui.write('SELECIONE...', interval=0.10)
pyautogui.press('esc')
time.sleep(0.2)
pyautogui.press('enter')
time.sleep(0.2)
pyautogui.write('PRESTADOR', interval=0.1)
time.sleep(0.5)
pyautogui.press('enter')
time.sleep(0.2)
pyautogui.press('tab')
time.sleep(0.2)
pyautogui.press('space')
time.sleep(0.2)
#---------------------------------------------------------------

## DADOS DO MDFE: EMITENTE
pyautogui.write('0315-60', interval=0.10)
pyautogui.press('enter')
time.sleep(0.5)

for _ in range(7):
    pyautogui.press('tab')
    time.sleep(0.1)
pyautogui.press('space')
time.sleep(0.2)
#---------------------------------------------------------------

## DADOS DO MDFE: UF CARREGAMENTO E DESCARREGAMENTO
pyautogui.write('SP', interval=0.20)
pyautogui.press('enter')
pyautogui.press('tab')
time.sleep(0.5)
pyautogui.press('space')
time.sleep(0.2)
pyautogui.write('SP', interval=0.20)
pyautogui.press('enter')
time.sleep(0.5)
#---------------------------------------------------------------

## DADOS DO MDFE: MUNICIPIO DE CARREGAMENTO
pyautogui.press('tab')
time.sleep(0.1)
pyautogui.write('SOROCABA'.upper(), interval=0.15)
time.sleep(0.3)

for _ in range(4):
    pyautogui.press('down')
    time.sleep(0.1)
for _ in range(3):
    pyautogui.press('up')
    time.sleep(0.1)
pyautogui.press('enter')
time.sleep(0.2)
#---------------------------------------------------------------

## UPLOAD DO ARQUIVO XML
for _ in range(2):
    pyautogui.press('tab')
pyautogui.press('space')
time.sleep(2)

downloads_path = Path.home() / "Downloads"
if not (list_of_files := list(downloads_path.glob('*'))):
    alert_topmost('A pasta Downloads está vazia!')
else:
    latest_file = max(list_of_files, key=os.path.getctime)
    pyautogui.write(str(latest_file), interval=0.05)
    time.sleep(0.3)
    pyautogui.press('enter')
time.sleep(0.3)
for _ in range(2):
    pyautogui.press('tab')
    time.sleep(0.1)
pyautogui.press('enter')
time.sleep(2)
progress.update(30, 'Dados básicos do emitente preenchidos')
print('[AutoMDF] Dados básicos do emitente preenchidos', flush=True)
#---------------------------------------------------------------

## DADOS DO MDFE: UNIDADE DE MEDIDA
for _ in range(5):
    pyautogui.press('tab')
    time.sleep(0.1)
pyautogui.press('space')
time.sleep(0.1)
pyautogui.write('1', interval=0.1)
pyautogui.press('enter')
#---------------------------------------------------------------

## DADOS DO MDFE: TIPO DE CARGA
for _ in range(2):
    pyautogui.press('tab')
    time.sleep(0.1)
pyautogui.press('space')
pyautogui.press('tab')
pyautogui.press('space')
time.sleep(0.1)
pyautogui.write('05', interval=0.1)
pyautogui.press('enter')

## DADOS DO MDFE: DESCRIÇÃO DO PRODUTO
pyautogui.press('tab')
pyautogui.write('PA/PALLET', interval=0.1)
#---------------------------------------------------------------

## DADOS DO MDFE: CÓDIGO NCM
for _ in range(2):
    pyautogui.press('tab')
    time.sleep(0.1)
opcao = confirm_topmost(
    text='Selecione o código NCM ou escolha "Outro código" para digitar manualmente:',
    title='Escolha de NCM',
    buttons=['19041000', '19059090', '20052000', 'Outro código', 'Cancelar']
)

if opcao == 'Cancelar':
    pyautogui.FAILSAFE = True
    _abort(progress, 'Nenhum código NCM selecionado. A automação foi encerrada.')
elif opcao == 'Outro código':
    codigo = prompt_topmost(
        text='Digite o código NCM:',
        title='Código NCM',
        require_input=True,
        cancel_message='Cancelar a inserção do código NCM interrompe a automação. Deseja cancelar mesmo assim?'
    )
    if not codigo:
        pyautogui.FAILSAFE = True
        _abort(progress, 'Nenhum código NCM digitado. A automação foi encerrada.')
else:
    codigo = opcao
codigo = cast(str, codigo).strip()
if not codigo:
    pyautogui.FAILSAFE = True
    _abort(progress, 'Nenhum código NCM digitado. A automação foi encerrada.')
pyautogui.write(codigo.upper(), interval=0.1)
pyautogui.press('enter')
#---------------------------------------------------------------

## DADOS DO MDFE: CEP ORIGEM
pyautogui.press('tab')
pyautogui.press('space')
pyautogui.press('tab')
pyautogui.write('18087101', interval=0.1)

## DADOS DO MDFE: CEP DESTINO
for _ in range(3):
    pyautogui.press('tab')
    time.sleep(0.1)
pyautogui.write('13315000', interval=0.1)
time.sleep(1)
progress.update(35, 'XML selecionado e enviado')
print('[AutoMDF] XML anexado', flush=True)
progress.update(40, 'Dados do contribuinte preenchidos')
print('[AutoMDF] Dados do contribuinte preenchidos', flush=True)
progress.update(45, 'Dados do MDF-e preenchidos')
print('[AutoMDF] Dados do MDF-e preenchidos', flush=True)
progress.update(50, 'Dados básicos do MDF-e preenchidos')
print('[AutoMDF] Dados básicos preenchidos', flush=True)


#-----------------------------------------------------#-----------------------------------------------------------------#
#-----------------------------------------------------#-----------------------------------------------------------------#
#						MODAL RODOVIÁRIO							#


# ABRIR DADOS DO MODAL RODOVIÁRIO
time.sleep(1)
pyautogui.hotkey('ctrl', 'f')
pyautogui.write('MODAL R', interval=0.12)
pyautogui.press('esc')
pyautogui.press('enter')
time.sleep(1)
#---------------------------------------------------------------


## RNTRC
pyautogui.hotkey('ctrl', 'f')
pyautogui.write('RNTRC', interval=0.10)
pyautogui.press('esc')
pyautogui.press('tab')
pyautogui.write('45501846', interval=0.10)
#---------------------------------------------------------------

## NOME DO CONTRATANTE
for _ in range(6):
    pyautogui.press('tab')
    time.sleep(0.1)
pyautogui.press('space')
pyautogui.press('tab')
pyautogui.write('PEPSICO SOROCABA', interval=0.20)
time.sleep(0.1)

## CNPJ DO CONTRATATANTE
pyautogui.press('tab')
pyautogui.write('02957518000739', interval=0.12)
for _ in range(2):
    pyautogui.press('tab')
    time.sleep(0.1)
pyautogui.press('enter')
time.sleep(1)
progress.update(55, 'Modal rodoviário preenchido')
print('[AutoMDF] Modal rodoviário preenchido', flush=True)


#-----------------------------------------------------#-----------------------------------------------------------------#
#-----------------------------------------------------#-----------------------------------------------------------------#
#						INFORMAÇÕES OPCIONAIS							#

# ABRIR DADOS DE INFORMAÇÕES OPCIONAIS
pyautogui.hotkey('ctrl', 'f')
pyautogui.write('OPCIONAIS', interval=0.10)
pyautogui.press('esc')
time.sleep(0.5)
pyautogui.press('enter')
time.sleep(1)


## INFORMAÇÕES ADICIONAIS
pyautogui.hotkey('ctrl', 'f')
time.sleep(0.5)
pyautogui.write('ADICIONAIS', interval=0.10)
time.sleep(0.3)
pyautogui.press('esc')
time.sleep(0.3)
pyautogui.press('enter')
time.sleep(0.5)

## CNPJ DA AUTORIZADA
pyautogui.hotkey('ctrl', 'f')
time.sleep(0.5)
pyautogui.write('CONTRIBUINTE', interval=0.10)
time.sleep(0.3)
pyautogui.press('esc')
time.sleep(0.3)
for _ in range(3):
    pyautogui.press('tab')
    time.sleep(0.3)
pyautogui.write('04898488000177', interval=0.10)
pyautogui.press('tab')
time.sleep(0.3)
pyautogui.press('enter')

## INFORMACOES DA SEGURADORA
for _ in range(2):
    pyautogui.press('tab')
    time.sleep(0.2)
pyautogui.press('space')
time.sleep(0.2)
pyautogui.press('tab')
pyautogui.press('space')
time.sleep(0.2)
pyautogui.write('CONTRA', interval=0.10)
pyautogui.press('enter')
time.sleep(0.3)
pyautogui.press('tab')
pyautogui.write('02957518000739', interval=0.12)
pyautogui.press('tab')
pyautogui.write('SEGUROS SURA SA', interval=0.10)
pyautogui.press('tab')
pyautogui.write('33065699000127', interval=0.12)
pyautogui.press('tab')
pyautogui.write('5400035882', interval=0.10)
pyautogui.press('tab')
pyautogui.press('enter')
time.sleep(0.3)

## INFORMACOES DO FRETE
for _ in range(4):
    pyautogui.press('tab')
    time.sleep(0.3)
pyautogui.press('space')
time.sleep(0.2)

pyautogui.press('tab')
time.sleep(0.2)
pyautogui.write('PEPSICO DO BRASIL', interval=0.12)
time.sleep(0.2)

pyautogui.press('tab')
time.sleep(0.2)
pyautogui.write('02957518000739', interval=0.12)
time.sleep(0.2)


for _ in range(2):
    pyautogui.press('tab')
    time.sleep(0.3)

pyautogui.write('1321.02', interval=0.12)
time.sleep(0.2)

pyautogui.press('tab')
time.sleep(0.2)
pyautogui.press('space')
time.sleep(0.2)
pyautogui.write('1', interval=0.12)
time.sleep(0.2)

pyautogui.press('enter')
time.sleep(0.3)
pyautogui.press('tab')
time.sleep(0.2)
pyautogui.write('237', interval=0.12)
time.sleep(0.2)

pyautogui.press('tab')
time.sleep(0.2)
pyautogui.write('2372/8', interval=0.12)
time.sleep(0.2)

for _ in range(2):
    pyautogui.press('tab')
    time.sleep(0.3)

pyautogui.press('enter')
time.sleep(0.3)

pyautogui.press('tab')
time.sleep(0.2)
pyautogui.press('enter')

pyautogui.hotkey('ctrl', 'f')
pyautogui.write('SELECIONE...', interval=0.10)
pyautogui.press('esc')
pyautogui.press('enter')
pyautogui.write('FRETE', interval=0.10)
pyautogui.press('enter')
time.sleep(0.2)
pyautogui.press('tab')
time.sleep(0.2)
pyautogui.write('1321.02', interval=0.12)
time.sleep(0.2)
pyautogui.press('tab')
time.sleep(0.2)
pyautogui.write('FRETE', interval=0.12)
pyautogui.press('tab')
time.sleep(0.2)
pyautogui.press('enter')
time.sleep(0.2)
progress.update(60, 'Informações complementares preenchidas')
print('[AutoMDF] Informações complementares preenchidas', flush=True)

pyautogui.hotkey('ctrl', 'f')
pyautogui.write('SELECIONE...', interval=0.10)
pyautogui.press('esc')
time.sleep(0.10)

for _ in range(5):
    pyautogui.press('tab')
    time.sleep(0.05)
pyautogui.write('1', interval=0.10)

for _ in range(2):
    pyautogui.press('tab')
    time.sleep(0.05)
pyautogui.press('space')
time.sleep(0.10)

for _ in range(7):
    pyautogui.press('tab')
    time.sleep(0.05)
pyautogui.press('space')
time.sleep(0.05)
pyautogui.press('space')
time.sleep(0.05)
pyautogui.press('tab')
time.sleep(0.05)
pyautogui.press('enter')
time.sleep(0.05)
pyautogui.press('tab')
pyautogui.write('1321.02', interval=0.10)
time.sleep(0.05)
pyautogui.press('tab')
time.sleep(0.05)
pyautogui.press('enter')
time.sleep(1)
progress.update(65, 'Informações adicionais preenchidas')
print('[AutoMDF] Informações adicionais concluídas', flush=True)


#-----------------------------------------------------#-----------------------------------------------------------------#
#-----------------------------------------------------#-----------------------------------------------------------------#
#						AVERBAÇÃO								#

# IR PARA 4ª ABA DO NAVEGADOR (AVERBAÇÃO)
switch_browser_tab(4)
time.sleep(1)

pyautogui.hotkey('ctrl', 'shift', 'a')
time.sleep(0.5)
pyautogui.write('ATM', interval=0.10)
pyautogui.press('enter')
time.sleep(1)

pyautogui.hotkey('ctrl', 'f')
time.sleep(0.5)
pyautogui.write('OK', interval=0.10)
time.sleep(0.5)
pyautogui.press('esc')
time.sleep(0.2)
pyautogui.press('enter')
time.sleep(0.5)

pyautogui.hotkey('ctrl', 'f')
time.sleep(0.5)
pyautogui.write('XML', interval=0.10)
time.sleep(0.5)
pyautogui.press('esc')
time.sleep(0.2)
pyautogui.press('enter')
time.sleep(0.5)

pyautogui.hotkey('ctrl', 'f')
time.sleep(0.5)
pyautogui.write('ENVIAR', interval=0.10)
time.sleep(0.5)
pyautogui.press('esc')
time.sleep(0.2)
pyautogui.press('enter')
time.sleep(1)


#---------------------------------------------------------------

## UPLOAD DO ARQUIVO XML
downloads_path = Path.home() / "Downloads"
if not (list_of_files := list(downloads_path.glob('*'))):
    alert_topmost('A pasta Downloads está vazia!')
else:
    latest_file = max(list_of_files, key=os.path.getctime)
    pyautogui.write(str(latest_file), interval=0.07)
    time.sleep(0.3)
    pyautogui.press('enter')
time.sleep(2)
progress.update(70, 'XML enviado para averbação')
print('[AutoMDF] XML enviado', flush=True)
#---------------------------------------------------------------
# Seleciona todo o texto da janela e copia
pyautogui.hotkey('ctrl', 'a')
time.sleep(0.2)
pyautogui.hotkey('ctrl', 'c')
time.sleep(0.2)

# Pega o texto da área de transferência
texto = pyperclip.paste()

# Extrai somente os números da linha "Número de Averbação"
if match := re.search(r'Número de Averbação:\s*([\d]+)', texto):
    numero_averbacao = match.group(1)

    # Coloca somente os números da averbação de volta na área de transferência
    pyperclip.copy(numero_averbacao)
    print(f"[AutoMDF] Número de Averbação copiado: {numero_averbacao}", flush=True)
else:
    print('[AutoMDF] Número de Averbação não encontrado', flush=True)

time.sleep(0.5)
pyautogui.hotkey('alt', 'tab')
time.sleep(1)

pyautogui.hotkey('ctrl', 'f')
time.sleep(0.5)
pyautogui.write('DETALHES', interval=0.10)
time.sleep(0.3)
pyautogui.press('esc')
pyautogui.press('enter')
time.sleep(0.5)
for _ in range(2):
    pyautogui.press('tab')
    time.sleep(0.5)
time.sleep(0.5)
pyautogui.hotkey('ctrl', 'v')
pyautogui.press('tab')
time.sleep(0.5)
pyautogui.press('enter')
time.sleep(1)
progress.update(75, 'Arquivo XML carregado')
print('[AutoMDF] Arquivo XML carregado', flush=True)

progress.update(80, 'Averbação realizada e número copiado')
print('[AutoMDF] Averbação concluída', flush=True)


# ---------- CÓDIGO ITU PARTE 5: COLETAR DT e CTE -------

pyautogui.hotkey('ctrl', 'shift', 'a')
time.sleep(0.5)
pyautogui.write('INVOISYS', interval=0.10)
pyautogui.press('enter')
time.sleep(1)

pyautogui.hotkey('ctrl', 'f')
pyautogui.write('FINAL', interval=0.20)
pyautogui.press('esc')
time.sleep(0.2)

for _ in range(4):
    pyautogui.press('tab')
    time.sleep(0.2)
time.sleep(0.5)

pyautogui.hotkey('ctrl', 'a')
time.sleep(0.5)
pyautogui.hotkey('ctrl', 'c')
time.sleep(0.5)
progress.update(85, 'Dados de DT e CTE coletados')
print('[AutoMDF] Dados coletados', flush=True)
switch_browser_tab(initial_tab)
time.sleep(0.5)
pyautogui.hotkey('alt', 'tab')
time.sleep(0.5)
pyautogui.hotkey('ctrl', 'f')
time.sleep(0.5)
pyautogui.write('CONTRIBUINTE', interval=0.10)
time.sleep(0.3)
pyautogui.press('esc')
time.sleep(0.5)
pyautogui.press('tab')
time.sleep(0.5)
pyautogui.write('DT: ', interval=0.10)
time.sleep(0.3)
pyautogui.hotkey('ctrl', 'v')
time.sleep(0.5)
pyautogui.write(' CTE: ', interval=0.10)
time.sleep(0.5)

# NAVEGAÇÃO PARA EXTRAÇÃO DA CTE
print('[AutoMDF] Navegando para primeira aba para extrair CTE...', flush=True)
pyautogui.hotkey('alt', 'tab')  # Vai para primeira aba (resultado da CTE)
time.sleep(1.0)  # Tempo para alternar de aba

# EXTRAÇÃO AUTOMÁTICA DO NÚMERO DA CTE
print('[AutoMDF] Extraindo número da CTE automaticamente...', flush=True)
numero_cte = extract_cte_number()
if numero_cte:
    print(f'[AutoMDF] ✅ Número da CTE extraído: {numero_cte}', flush=True)
else:
    print('[AutoMDF] ❌ ERRO: Não foi possível extrair o número da CTE automaticamente', flush=True)
    print('[AutoMDF] Encerrando automação devido à falha na extração da CTE', flush=True)
    progress.update(100, 'ERRO: Falha na extração da CTE')
    alert_topmost('ERRO: Não foi possível extrair o número da CTE. Verifique se a página está correta.')
    sys.exit(1)

# VOLTA PARA A TERCEIRA ABA (FORMULÁRIO MDF-E)
print('[AutoMDF] Voltando para terceira aba para colar a CTE...', flush=True)
pyautogui.hotkey('alt', 'tab')  # Volta para terceira aba (formulário)
time.sleep(1.0)  # Tempo para alternar de aba

# ALERTA (mantido para consistência, mas agora a CTE já foi extraída)
alert_topmost('CTE extraído automaticamente. Inclua a NF e os dados do motorista')
time.sleep(0.5)

# COLA O NÚMERO DA CTE
print('[AutoMDF] Colando número da CTE no formulário...', flush=True)
pyautogui.hotkey('ctrl', 'v')
time.sleep(0.5)
pyautogui.write(' NF: ', interval=0.10)
time.sleep(0.5)

progress.update(90, 'Campos de DT, CTE e NF atualizados')
print('[AutoMDF] Campos finais atualizados', flush=True)


# ---------- FINALIZAÇÃO ----------
alert_topmost('Sucesso! Inclua a NF e os dados do motorista')
progress.complete('Automação concluída com sucesso')
print('[AutoMDF] Execução finalizada com sucesso', flush=True)
