# IMPORTAR BIBLIOTECLA E RECURSOS
import pyautogui
import time
import ctypes
import os
import pyperclip
import re
import json
import sys
from pathlib import Path
import tkinter as tk
from tkinter import simpledialog, messagebox


BRIDGE_ACTIVE = os.environ.get('MDF_BRIDGE_ACTIVE') == '1'
BRIDGE_PREFIX = os.environ.get('MDF_BRIDGE_PREFIX', '__MDF_GUI_BRIDGE__')
BRIDGE_ACK = os.environ.get('MDF_BRIDGE_ACK', '__MDF_GUI_ACK__')
BRIDGE_CANCEL = os.environ.get('MDF_BRIDGE_CANCEL', '__MDF_GUI_CANCEL__')


def _bridge_request(payload):
    if not BRIDGE_ACTIVE:
        return None, False

    try:
        message = BRIDGE_PREFIX + json.dumps(payload, ensure_ascii=False)
        print(message, flush=True)
        response = sys.stdin.readline()
        if response is None or response == '':
            return None, True
        response = response.rstrip('\n')
        if response == BRIDGE_CANCEL:
            return None, True
        if response == BRIDGE_ACK:
            return '', True
        return response, True
    except Exception:
        return None, False


def _parse_text_title_defaults(args, kwargs, default_title):
    text = ''
    title = default_title
    default_value = None

    if args:
        text = args[0]
    if len(args) > 1:
        title = args[1]
    if len(args) > 2:
        default_value = args[2]

    if 'text' in kwargs:
        text = kwargs['text']
    if 'title' in kwargs:
        title = kwargs['title']
    if 'default' in kwargs:
        default_value = kwargs['default']

    return text, title, default_value


def prompt_topmost(*args, **kwargs):
    """Exibe um prompt que permanece acima de todas as janelas."""
    text, title, default_value = _parse_text_title_defaults(args, kwargs, 'Entrada')

    response, handled = _bridge_request({
        'type': 'prompt',
        'text': text or '',
        'title': title or 'Entrada',
        'default': default_value or ''
    })
    if handled:
        return response

    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    root.lift()
    root.after(0, root.focus_force)
    root.after(0, root.lift)

    try:
        return simpledialog.askstring(title or 'Entrada', text or '', parent=root, initialvalue=default_value)
    finally:
        root.destroy()


def alert_topmost(*args, **kwargs):
    """Exibe um alerta informativo em primeiro plano."""
    text, title, _ = _parse_text_title_defaults(args, kwargs, 'Informação')

    _, handled = _bridge_request({
        'type': 'alert',
        'text': text or '',
        'title': title or 'Informação'
    })
    if handled:
        return 'OK'

    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    root.lift()
    root.after(0, root.focus_force)
    root.after(0, root.lift)

    try:
        messagebox.showinfo(title or 'Informação', text or '', parent=root)
    finally:
        root.destroy()

    return 'OK'


def confirm_topmost(*args, **kwargs):
    """Exibe uma janela de confirmação com botões personalizados sempre no topo."""
    text, title, _ = _parse_text_title_defaults(args, kwargs, 'Confirmação')
    buttons = kwargs.get('buttons', ['OK', 'Cancel'])

    if not buttons:
        buttons = ['OK']

    response, handled = _bridge_request({
        'type': 'confirm',
        'text': text or '',
        'title': title or 'Confirmação',
        'buttons': buttons
    })
    if handled:
        return response if response is not None else ('Cancel' if 'Cancel' in buttons else buttons[-1])

    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    root.lift()

    top = tk.Toplevel(root)
    top.title(title or 'Confirmação')
    top.transient(root)
    top.attributes('-topmost', True)
    top.resizable(False, False)

    result = {'value': buttons[0]}

    def on_click(value):
        result['value'] = value
        top.destroy()

    def on_close():
        if 'Cancel' in buttons:
            result['value'] = 'Cancel'
        else:
            result['value'] = buttons[-1]
        top.destroy()

    top.protocol('WM_DELETE_WINDOW', on_close)

    label = tk.Label(top, text=text or '', justify='left', wraplength=420)
    label.pack(padx=20, pady=(20, 10))

    button_frame = tk.Frame(top)
    button_frame.pack(padx=20, pady=(0, 20))

    columns = min(3, len(buttons)) or 1
    for idx, btn_text in enumerate(buttons):
        button = tk.Button(button_frame, text=btn_text, width=18, command=lambda value=btn_text: on_click(value))
        row = idx // columns
        col = idx % columns
        button.grid(row=row, column=col, padx=5, pady=5, sticky='ew')

    top.update_idletasks()
    top.lift()
    top.focus_force()
    width = top.winfo_width()
    height = top.winfo_height()
    screen_width = top.winfo_screenwidth()
    screen_height = top.winfo_screenheight()
    pos_x = (screen_width // 2) - (width // 2)
    pos_y = (screen_height // 2) - (height // 2)
    top.geometry(f"+{pos_x}+{pos_y}")
    top.grab_set()
    top.focus_force()
    top.lift()

    root.wait_window(top)
    root.destroy()
    return result['value']
pyautogui.FAILSAFE = True  # Pausa de emergência movendo o mouse para o canto superior esquerdo
#---------------------------------------------------------------

#---------------------------------------------------------------
# ABRIR NAVEGADOR
time.sleep(1)
pyautogui.hotkey('winleft', '1')
time.sleep(1)
#---------------------------------------------------------------

#GAP
pyautogui.press('enter')
pyautogui.hotkey('ctrl', 'shift', 'a')
time.sleep(0.2)


# IR PARA 1ª ABA DO NAVEGADOR

pyautogui.hotkey('ctrl', '1')
time.sleep(2)
pyautogui.hotkey('ctrl', '1')
time.sleep(1)
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
    title='DT'
)

if not codigo:
    alert_topmost('Nenhum código informado. O script foi pausado.')
    pyautogui.FAILSAFE = True
    exit()
pyautogui.write(codigo.upper(), interval=0.1)
pyautogui.press('enter')
time.sleep(0.3)
pyautogui.press('enter')
time.sleep(0.5)
#---------------------------------------------------------------

#ALERTA
alert_topmost(
    'Antes de prosseguir:\n\n'
    '1. Baixe o arquivo XML;\n'
    '2. Mantenha 3 abas do Invoisys abertas no começo do navegador;\n'
    '2. Mantenha o site de averbação logado.\n\n'
    'OBS: Para interromper o processo, deslize o mouse repetidamente em direção ao canto superior direito da tela'
)
time.sleep(2)
#---------------------------------------------------------------

#DESATIVAR CAPS LOOK
VK_CAPITAL = 0x14  # código da tecla Caps Lock

# Obtém o estado atual do Caps Lock
caps_state = ctypes.windll.user32.GetKeyState(VK_CAPITAL)

# Se estiver ativo, desliga
if caps_state & 1:
    # Pressiona Caps Lock
    ctypes.windll.user32.keybd_event(VK_CAPITAL, 0, 0, 0)
    # Solta Caps Lock
    ctypes.windll.user32.keybd_event(VK_CAPITAL, 0, 2, 0)

#---------------------------------------------------------------

# IR PARA 3ª ABA DO NAVEGADOR
pyautogui.hotkey('ctrl', '3')
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

# ALERTA
alert_topmost('Aguarde o formulário abrir.')
time.sleep(2)
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
list_of_files = list(downloads_path.glob('*'))
if not list_of_files:
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
    buttons=['19041000', '19059090', '18069000', '20098921', '22029900', '30005980', 'Outro código', 'Cancelar']
)

if opcao == 'Cancelar':
    alert_topmost('Nenhum código NCM selecionado. O script foi pausado.')
    pyautogui.FAILSAFE = True
    exit()
elif opcao == 'Outro código':
    codigo = prompt_topmost('Digite o código NCM:')
    if not codigo:
        alert_topmost('Nenhum código NCM digitado. O script foi pausado.')
        pyautogui.FAILSAFE = True
        exit()
else:
    codigo = opcao
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


#-----------------------------------------------------#-----------------------------------------------------------------#
#-----------------------------------------------------#-----------------------------------------------------------------#
#						AVERBAÇÃO								#

	
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
list_of_files = list(downloads_path.glob('*'))
if not list_of_files:
    alert_topmost('A pasta Downloads está vazia!')
else:
    latest_file = max(list_of_files, key=os.path.getctime)
    pyautogui.write(str(latest_file), interval=0.07)
    time.sleep(0.3)
    pyautogui.press('enter')
time.sleep(2)
#---------------------------------------------------------------
# Seleciona todo o texto da janela e copia
pyautogui.hotkey('ctrl', 'a')
time.sleep(0.2)
pyautogui.hotkey('ctrl', 'c')
time.sleep(0.2)

# Pega o texto da área de transferência
texto = pyperclip.paste()

# Extrai somente os números da linha "Número de Averbação"
match = re.search(r'Número de Averbação:\s*([\d]+)', texto)
if match:
    numero_averbacao = match.group(1)
    
    # Coloca somente os números da averbação de volta na área de transferência
    pyperclip.copy(numero_averbacao)
    print("Número de Averbação copiado:", numero_averbacao)
else:
    print("Número de Averbação não encontrado")

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
pyautogui.hotkey('alt', 'tab')
time.sleep(0.5)

#ALERTA
alert_topmost('Copie o número do CT-E')
time.sleep(0.5)

pyautogui.hotkey('alt', 'tab')
time.sleep(0.5)
pyautogui.hotkey('ctrl', 'v')
time.sleep(0.5)
pyautogui.write(' NF: ', interval=0.10)
time.sleep(0.5)


# ---------- FINALIZAÇÃO ----------
alert_topmost('Sucesso! Inclua a NF e os dados do motorista')
