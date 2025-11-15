# Testes de Reconhecimento de Imagem - AutoMDF

Este documento explica como usar os testes de reconhecimento de imagem para verificar se a automação funcionará corretamente.

## Visão Geral

O sistema de automação usa reconhecimento de imagem para detectar quando o formulário MDF-e está carregado. Para que a automação funcione, a imagem de referência (`recon.png`) deve poder ser encontrada dentro da imagem maior da tela do navegador.

## Arquivos de Teste

### `test_image_recognition.py`
Teste único que verifica se a imagem `recon.png` pode ser encontrada na tela atual.

**Como usar:**
1. Abra o navegador com o sistema Invoisys
2. Navegue até a página do formulário MDF-e
3. Certifique-se de que o formulário está visível na tela
4. Execute o script: `python tests/test_image_recognition.py`

### `test_realtime_recognition.py`
Teste interativo que permite executar múltiplos testes em tempo real.

**Como usar:**
1. Execute o script: `python tests/test_realtime_recognition.py`
2. Escolha as opções do menu:
   - Opção 1: Testa reconhecimento na tela atual
   - Opção 2: Executa diagnóstico de confiança
   - Opção 3: Sair

## Como Executar os Testes

### No Windows (PowerShell):
```powershell
# Ativar ambiente virtual
.venv\Scripts\Activate.ps1

# Executar teste único
python tests/test_image_recognition.py

# Ou executar teste interativo
python tests/test_realtime_recognition.py
```

### No Linux/Mac:
```bash
# Ativar ambiente virtual
source .venv/bin/activate

# Executar teste único
python tests/test_image_recognition.py

# Ou executar teste interativo
python tests/test_realtime_recognition.py
```

## Interpretação dos Resultados

### ✅ Sucesso
Se o teste mostrar "IMAGEM ENCONTRADA", significa que:
- A imagem de referência pode ser detectada na tela atual
- A automação deve funcionar corretamente
- O nível de confiança recomendado será exibido

### ❌ Falha
Se o teste mostrar "imagem não encontrada", possíveis causas:
- O formulário MDF-e não está aberto na tela
- A imagem de referência não corresponde ao que está sendo exibido
- Resolução/zoom da tela afetando o reconhecimento
- Interface do sistema Invoisys foi alterada

## Diagnóstico de Confiança

O diagnóstico testa diferentes níveis de confiança (0.1 a 0.9) para encontrar o melhor valor. Valores mais altos são mais precisos mas podem falhar se houver pequenas variações na imagem.

## Funcionalidades Adicionais

### Extração Automática da CTE

O sistema inclui uma funcionalidade automática para extrair o número da CTE (Conhecimento de Transporte Eletrônico) no final da automação:

- **Função**: `extract_cte_number()` em `data/script_runtime.py`
- **Estratégia**: **Apenas primeira aba do navegador** (mais segura e confiável)
- **Como funciona**:
  1. Limpa a área de transferência
  2. Alterna para a primeira aba do navegador
  3. Faz prévia cópia para verificar conteúdo
  4. Se necessário, navega com 1-3 tabs dentro da página
  5. Copia o conteúdo da tela (Ctrl+A, Ctrl+C)
  6. Procura pela linha "100 - Autorizado o uso do CT-e.N"
  7. Extrai o número de 6 dígitos que segue essa frase
  8. Se não encontrar, tenta variações mais flexíveis com "CT-e" + números
  9. Copia automaticamente para a área de transferência

- **Vantagens da abordagem**:
  - **Mais segura**: Não alterna entre múltiplas abas desnecessariamente
  - **Mais rápida**: Foca apenas onde o conteúdo deve estar
  - **Menos invasiva**: Não interfere com outras abas abertas
  - **Mais confiável**: Comportamento consistente e previsível

- **Comportamento de erro**: Se não encontrar os 6 dígitos da CTE, **encerra a automação** com erro
- **Debugging**: Logging detalhado mostra exatamente o que foi copiado e analisado
- **Integração**: Automática nos scripts `ITU X DHL.py` e `SOROCABA X DHL.py`

#### Teste da Extração da CTE

Para testar/debuggar a extração da CTE:

```bash
python tests/test_cte_manual.py
```

Este script permite testar a extração em tempo real e ver exatamente que conteúdo está sendo copiado da tela.

### Dependências

- `pyperclip`: Para manipulação da área de transferência
- `re`: Para expressões regulares na extração do número