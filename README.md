# Auto MDF InvoISys

Sistema avançado de automação para emissão e averbação de MDF-e com integração ao Invoisys.

## 📋 Descrição

Este projeto automatiza o processo de:
1. Busca e download de CT-e
2. Preenchimento de dados MDF-e
3. Configuração de modal rodoviário
4. Preenchimento de informações adicionais e seguros
5. Averbação no sistema segurador
6. Coleta de dados de averbação

## 🚀 Início Rápido

### ⚠️ Dependências Sob Demanda

A verificação de dependências agora ocorre **apenas quando erros de módulo são detectados durante a execução**:

- Se um script tentar usar `pyautogui` ou `pyperclip` e não encontrar, você será notificado
- A GUI oferecerá instalar automaticamente
- Você pode verificar e instalar manualmente a qualquer momento via botões

### 1. Instalar Dependências (Opcional até precisar)

**Opção A: Usando virtualenv (Recomendado)**

Windows CMD:
```batch
install.bat
.\\venv\\Scripts\\activate.bat
python AutoMDF-Start.py
```

**Opção B: Instalação para o usuário (--user)**

Windows CMD:
```batch
install_user.bat
python AutoMDF-Start.py
```

**Opção C: Instalação via GUI**

Depois de abrir a GUI, clique em "📥 Instalar Dependências" na aba Controle.

### 2. Executar a Automação

```bash
python AutoMDF-Start.py
```

Interface com 3 abas:
- **🎛️ Controle** - Selecionar e iniciar scripts + Gerenciar dependências
- **▶️ Em Execução** - Monitorar execução em tempo real
- **📜 Histórico** - Ver log de todas as execuções

### 3. Se Houver Erro de Módulo

Se um script precisar de uma dependência que não está instalada:
1. Você verá um aviso no log
2. A GUI oferecerá instalar automaticamente
3. Clique "Sim" para instalar e tente novamente

## 📁 Estrutura do Projeto

```
Auto MDF InvoISys/
├── ITU X DHL.py                 # Script de automação (ITU)
├── SOROCABA X DHL.py            # Script de automação (Sorocaba)
├── AutoMDF-Start.py     # Interface gráfica (USE ESTE)
├── progress_manager.py          # Gerenciador de progresso em tempo real
├── requirements.txt             # Dependências Python
├── install.bat                  # Instalador (Windows CMD)
├── install_user.bat             # Instalador com --user (Windows CMD)
└── README.md                    # Este arquivo
```

## 📦 Dependências

- `pyautogui` - Automação de GUI
- `pyperclip` - Gerenciamento de clipboard

Instaladas automaticamente via `install.bat`, `install_user.bat` ou via GUI.

## 🎯 Recursos

### GUI v0.5.0-Alpha-GUI

✅ **Verificação Inteligente de Dependências**
- Verifica apenas quando erros de módulo ocorrem
- Oferece instalar automaticamente ao detectar
- Não bloqueia a GUI na inicialização
- Botões para verificação e instalação manual

✅ **Execução Única**
- Apenas um script por vez
- Validação contra múltiplas execuções

✅ **Responsiva**
- GUI não trava durante execução
- Scripts rodam em processos isolados

✅ **Monitoramento em Tempo Real**
- Output capturado linha por linha
- Status: Executando, Concluído, Erro, Parado
- Tempo decorrido e % de progresso
- Histórico completo

✅ **Gerenciamento Fácil**
- Copiar logs para clipboard
- Salvar histórico em arquivo
- Parar execução a qualquer momento
- Gerenciar dependências (Instalar, Verificar)

### Progresso em Tempo Real

Se adaptar seus scripts com `ProgressManager`:

```python
from progress_manager import ProgressManager

progress = ProgressManager()
progress.start(total_steps=10)

for i in range(1, 11):
    progress.update(i * 10, f"Etapa {i}/10")
    # seu código aqui
    
progress.complete()
```

## 🔧 Como Usar

### Executar via GUI (Recomendado)

1. Abra a GUI: `python AutoMDF-Start.py`
2. **Primeira execução**: Instale as dependências (clique "📥 Instalar Dependências")
3. Aba **🎛️ Controle**: Selecione script
4. Clique **▶ Iniciar Execução**
5. Aba **▶️ Em Execução**: Monitore em tempo real
6. Aguarde conclusão ou clique **⏹ Parar**

### Gerenciar Dependências na GUI

Na aba **🎛️ Controle**, você tem dois botões:

- **📥 Instalar Dependências** - Instala automaticamente
- **✓ Verificar Dependências** - Verifica status e oferece instalar se necessário

### Executar Script Diretamente

```bash
python "ITU X DHL.py"
```

ou

```bash
python "SOROCABA X DHL.py"
```

### Menu Principal

O script `1. MDF.py` foi descontinuado e removido. Utilize a interface gráfica `AutoMDF-Start.py`.

## 📊 Abas da GUI v0.5.0-Alpha-GUI

### 🎛️ Controle
- Dropdown de scripts disponíveis
- Botões: Iniciar, Parar
- Informações gerais
- Status em tempo real
- **Seção de Gerenciamento de Dependências:**
  - 📥 Instalar Dependências
  - ✓ Verificar Dependências

### ▶️ Em Execução
- Painel do script atual
- Status (Executando, Concluído, Erro)
- Tempo decorrido
- % de progresso
- Output completo
- Botão: Copiar Log

### 📜 Histórico
- Log de todas as execuções
- Timestamps para cada ação
- Cores por tipo (info, success, error, warning)
- Registra verificação e instalação de dependências
- Botões: Salvar, Limpar histórico

## � Gerenciamento de Dependências

### Verificação Automática

A GUI verifica dependências em:
1. **Inicialização** - Ao abrir a aplicação
2. **Antes de executar** - Antes de rodar qualquer script
3. **Sob demanda** - Via botão "✓ Verificar Dependências"

### Instalação Obrigatória

Se as dependências faltarem:
- Janela obrigatória bloqueará a interface
- Você deve instalar antes de continuar
- Duas opções: Automática ou Manual

### Botões de Gerenciamento

**📥 Instalar Dependências**
- Abre janela interativa
- Tenta instalar automaticamente com pip
- Mostra progresso em tempo real

**✓ Verificar Dependências**
- Verifica status atual
- Mostra quais estão presentes/faltando
- Oferece instalar se necessário

## 🛠️ Instalação Detalhada

### Windows CMD (Recomendado)

```batch
:: Instalação com virtualenv
install.bat

:: Ou instalação com --user
install_user.bat

:: Executar GUI
python AutoMDF-Start.py
```

### Windows PowerShell

```powershell
# Ativar execução de scripts (se necessário)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Executar instalador
.\install.ps1

# Ativar virtualenv
.\venv\Scripts\Activate.ps1

# Executar GUI
python AutoMDF-Start.py
```

## ⚙️ Requisitos do Sistema

- **Python 3.8+**
- **Windows 7+** (testado em Windows 10/11)
- **Navegador** (Chrome, Edge, Firefox - compatível com PyAutoGUI)
- **Acesso ao Invoisys** logado
- **Acesso ao site de averbação** logado

## 🐛 Troubleshooting

### "Python não encontrado"
```bash
python --version
```

### "Dependências obrigatórias"
- Clique em "📥 Instalar Dependências" na aba Controle
- Ou execute `install.bat` manualmente

### "Nenhum script em execução"
- Verifique que os arquivos `.py` estão na mesma pasta
- Nomes devem conter "itu", "sorocaba" ou "dhl"

### "GUI não responde"
- GUI atualiza a cada 500ms (é normal uma pequena latência)
- Verifique a aba **▶️ Em Execução** para ver progresso real

### "Script executado mas sem output"
- Output é capturado após as primeiras linhas
- Aguarde alguns segundos para atualização

## 📝 Integração com ProgressManager

Para adicionar progresso em tempo real em seus scripts:

```python
from progress_manager import ProgressManager

progress = ProgressManager()
progress.start(total_steps=10)
progress.add_log("🚀 Iniciando automação...")

progress.update(50, "Preenchendo dados...", 5)
progress.add_log("✓ Dados preenchidos")

progress.complete("✅ Automação concluída!")
```

## 📖 Documentação Adicional

Consulte:
- `CHANGELOG.md` - Histórico de mudanças e atualizações

## 🔐 Segurança

Scripts rodam em processos isolados sem compartilhamento de estado.

Use FAILSAFE do PyAutoGUI:

```python
pyautogui.FAILSAFE = True
```

---

**Versão**: v0.5.0-Alpha-GUI | **Última atualização**: 3 de novembro de 2025