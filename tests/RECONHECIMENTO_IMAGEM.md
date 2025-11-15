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

## Resolução de Problemas

### Se a imagem não for encontrada:
1. Verifique se o formulário MDF-e está realmente aberto
2. Certifique-se de que não há pop-ups ou overlays bloqueando a visão
3. Tente ajustar o zoom do navegador para 100%
4. Se necessário, atualize a imagem `recon.png` com uma captura mais recente

### Se o reconhecimento for inconsistente:
1. Use o diagnóstico para encontrar o melhor nível de confiança
2. Considere usar uma região específica da tela ao invés de toda a tela
3. Verifique se há variações na interface (temas, idiomas, etc.)

## Configuração Atual

- **Imagem de referência**: `img/recon.png`
- **Confiança padrão**: 0.8 (alta precisão)
- **Timeout padrão**: 30-45 segundos

Para alterar essas configurações, edite as funções em `data/image_recognition.py`.