import pyautogui
import time

pyautogui.FAILSAFE = True  # Pausa de emergência movendo o mouse para o canto superior esquerdo

#-------CÓDIGO SOROCABA -------
# ---------- CÓDIGO PARTE 1 ----------
pyautogui.alert('Antes de iniciar, certifique-se de que: \n\n1. Você está logado no sistema INVOISYS.\n2. O arquivo XML para averbação foi o último item baixado.\n\nATENÇÃO: CASO DESEJE CANCELAR O PROCESSO MOVA O MOUSE PARA CANTO SUPERIOR ESQUERDO DO MONITOR.\n\nClique em OK para iniciar o processo automático.')

pyautogui.hotkey('winleft', '1')
time.sleep(2)
pyautogui.hotkey('ctrl', 'shift', 'a')
time.sleep(2)
pyautogui.write('INVOISYS', interval=0.10)
time.sleep(0.5)
pyautogui.press('enter')
time.sleep(1)

pyautogui.hotkey('ctrl', 'f')
pyautogui.write('EMITIR NOTA', interval=0.10)
pyautogui.press('esc')
pyautogui.press('enter')
time.sleep(0.5)

pyautogui.hotkey('ctrl', 'f')
pyautogui.write('MDF-E', interval=0.10)
pyautogui.press('esc')
pyautogui.press('enter')

pyautogui.alert('Aguarde o formulário abrir.')
time.sleep(2)

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
pyautogui.write('0315-60', interval=0.10)
pyautogui.press('enter')
time.sleep(0.5)

for _ in range(7):
    pyautogui.press('tab')
    time.sleep(0.1)
pyautogui.press('space')
pyautogui.write('SP', interval=0.20)
pyautogui.press('enter')
pyautogui.press('tab')
time.sleep(0.5)
pyautogui.press('space')
pyautogui.write('SP', interval=0.20)
pyautogui.press('enter')

pyautogui.press('tab')
pyautogui.write('SOROCABA'.upper(), interval=0.15)
time.sleep(0.3)
pyautogui.press('enter')

for _ in range(2):
    pyautogui.press('tab')
    time.sleep(0.1)
pyautogui.press('enter')
time.sleep(2)

# Acessar pasta de download e anexar arquivo xml
for _ in range(11):
    pyautogui.press('tab')
    time.sleep(0.1)
pyautogui.press('space')
pyautogui.press('enter')
time.sleep(1)

for _ in range(2):
    pyautogui.press('tab')
    time.sleep(0.1)
pyautogui.press('enter')
time.sleep(2)

for _ in range(5):
    pyautogui.press('tab')
    time.sleep(0.1)
pyautogui.press('space')
time.sleep(0.1)
pyautogui.write('1', interval=0.1)
pyautogui.press('enter')

for _ in range(2):
    pyautogui.press('tab')
    time.sleep(0.1)
pyautogui.press('space')
pyautogui.press('tab')
pyautogui.press('space')
time.sleep(0.1)
pyautogui.write('05', interval=0.1)
pyautogui.press('enter')
pyautogui.press('tab')
pyautogui.write('PA/PALLET', interval=0.1)

for _ in range(2):
    pyautogui.press('tab')
    time.sleep(0.1)

# --- ESCOLHA DO CÓDIGO NCM ---
opcao = pyautogui.confirm(
    text='Selecione o código NCM ou escolha "Outro código" para digitar manualmente:',
    title='Escolha de NCM',
    buttons=['19041000', '19059090', '18069000', '20098921', '22029900', '300005980', 'Outro código', 'Cancelar']
)

if opcao == 'Cancelar':
    pyautogui.alert('Nenhum código NCM selecionado. O script foi pausado.')
    pyautogui.FAILSAFE = True
    exit()
elif opcao == 'Outro código':
    codigo = pyautogui.prompt('Digite o código NCM:')
    if not codigo:
        pyautogui.alert('Nenhum código NCM digitado. O script foi pausado.')
        pyautogui.FAILSAFE = True
        exit()
else:
    codigo = opcao

# Preenche o NCM escolhido ou digitado
pyautogui.write(codigo.upper(), interval=0.1)
pyautogui.press('enter')

pyautogui.press('tab')
pyautogui.press('space')
pyautogui.press('tab')
pyautogui.write('18087101', interval=0.1)
for _ in range(3):
    pyautogui.press('tab')
    time.sleep(0.1)
pyautogui.write('13315000', interval=0.1)
time.sleep(1)

# ---------- CÓDIGO PARTE 2 ----------
time.sleep(1)
pyautogui.hotkey('ctrl', 'f')
pyautogui.write('MODAL R', interval=0.10)
pyautogui.press('esc')
pyautogui.press('enter')
time.sleep(1)

pyautogui.hotkey('ctrl', 'f')
pyautogui.write('RNTRC', interval=0.10)
pyautogui.press('esc')
pyautogui.press('tab')
pyautogui.write('45501846', interval=0.10)

for _ in range(6):
    pyautogui.press('tab')
    time.sleep(0.1)
pyautogui.press('space')
pyautogui.press('tab')
pyautogui.write('PEPSICO SOROCABA', interval=0.20)
time.sleep(0.1)
pyautogui.press('tab')
pyautogui.write('02957518000739', interval=0.10)
for _ in range(2):
    pyautogui.press('tab')
    time.sleep(0.1)
pyautogui.press('enter')
time.sleep(1)

# ---------- CÓDIGO PARTE 3 ----------
pyautogui.hotkey('ctrl', 'f')
pyautogui.write('OPCIONAIS', interval=0.10)
pyautogui.press('esc')
pyautogui.press('enter')

pyautogui.hotkey('ctrl', 'f')
time.sleep(0.5)
pyautogui.write('ADICIONAIS', interval=0.10)
time.sleep(0.3)
pyautogui.press('esc')
time.sleep(0.3)
pyautogui.press('enter')
time.sleep(0.5)

pyautogui.hotkey('ctrl', 'f')
time.sleep(0.5)
pyautogui.write('CONTRIBUINTE', interval=0.10)
time.sleep(0.3)
pyautogui.press('esc')
time.sleep(0.3)
pyautogui.press('tab')
time.sleep(0.3)
pyautogui.press('tab')
time.sleep(0.3)
pyautogui.press('tab')
time.sleep(0.3)
pyautogui.write('04898488000177', interval=0.10)
pyautogui.press('tab')
time.sleep(0.3)
pyautogui.press('enter')

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
pyautogui.write('02957518000739', interval=0.10)
pyautogui.press('tab')
pyautogui.write('SEGUROS SURA SA', interval=0.10)
pyautogui.press('tab')
pyautogui.write('33065699000127', interval=0.10)
pyautogui.press('tab')
pyautogui.write('5400035882', interval=0.10)
pyautogui.press('tab')
pyautogui.press('enter')
time.sleep(0.3)

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

# ---------- CÓDIGO PARTE 4: AVERBAÇÃO -------

pyautogui.hotkey('ctrl', 'shift', 'a')
time.sleep(0.5)
pyautogui.write('ATM', interval=0.10)
pyautogui.press('enter')
time.sleep(1)

pyautogui.hotkey('ctrl', 'f')
time.sleep(0.5)
pyautogui.write('OK', interval=0.10)
time.sleep(0.3)
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
time.sleep(0.3)
pyautogui.press('esc')
time.sleep(0.2)
pyautogui.press('enter')
time.sleep(0.5)

# Acessar pasta de download e anexar arquivo xml
for _ in range(11):
    pyautogui.press('tab')
    time.sleep(0.1)
pyautogui.press('space')
pyautogui.press('enter')
time.sleep(1)

pyautogui.alert('Copie o código da averbação.')
time.sleep(1)

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


# ---------- CÓDIGO PARTE 5: COLETAR DT e CTE -------

pyautogui.hotkey('ctrl', 'shift', 'a')
time.sleep(0.5)
pyautogui.write('INVOISYS', interval=0.10)
pyautogui.press('enter')
time.sleep(1)

pyautogui.hotkey('ctrl', 'f')
time.sleep(0.5)
pyautogui.write('FILIAIS?', interval=0.10)
time.sleep(0.3)
pyautogui.press('esc')
time.sleep(0.5)

for _ in range(8):
    pyautogui.press('tab')
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
pyautogui.alert('Copie o número do CTE.')
time.sleep(1)
pyautogui.hotkey('alt', 'tab')
time.sleep(0.5)
pyautogui.hotkey('ctrl', 'v')
time.sleep(0.5)
pyautogui.write(' NF: ', interval=0.10)
time.sleep(0.5)


# ---------- FINALIZAÇÃO ----------
pyautogui.alert('Sucesso! Inclua a NF e os dados do motorista')
