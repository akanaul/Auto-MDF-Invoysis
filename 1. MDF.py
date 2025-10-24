import pyautogui
import os
import runpy

# Pergunta qual cidade rodar
opcao_cidade = pyautogui.confirm(
    text='Escolha a cidade para rodar o script:',
    title='Escolha de cidade',
    buttons=['ITU X DHL', 'SOROCABA X DHL', 'Cancelar']
)

if opcao_cidade == 'ITU X DHL':
    arquivo = 'itu x dhl.py'
elif opcao_cidade == 'SOROCABA X DHL':
    arquivo = 'sorocaba x dhl.py'
else:
    pyautogui.alert('Script cancelado.')
    exit()

# Verifica se o arquivo existe na mesma pasta
if not os.path.exists(arquivo):
    pyautogui.alert(f'O arquivo "{arquivo}" não foi encontrado na mesma pasta!')
    exit()

# Executa o arquivo selecionado
runpy.run_path(arquivo)
