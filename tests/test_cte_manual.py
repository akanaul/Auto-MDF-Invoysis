#!/usr/bin/env python3
"""Script para testar a extração da CTE em tempo real."""

import sys
import time
from pathlib import Path

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

try:
    from data.script_runtime import extract_cte_number
    print("✅ Import da função extract_cte_number bem-sucedido")
except ImportError as e:
    print(f"❌ Erro no import: {e}")
    sys.exit(1)

def test_cte_extraction_manual():
    """Testa a extração da CTE manualmente."""
    print("=" * 70)
    print("TESTE MANUAL DE EXTRAÇÃO DA CTE")
    print("=" * 70)
    print()
    print("INSTRUÇÕES:")
    print("1. Abra o navegador com o sistema Invoisys")
    print("2. Navegue até a página que contém o resultado da CTE")
    print("3. Certifique-se de que a página mostra '100 - Autorizado o uso do CT-e.N'")
    print("4. POSICIONE na PRIMEIRA ABA do navegador")
    print("5. Clique em qualquer lugar da tela para dar foco")
    print("6. Pressione ENTER aqui para iniciar o teste")
    print()
    print("ESTRATÉGIA UTILIZADA:")
    print("- Foca apenas na primeira aba do navegador")
    print("- Faz prévia cópia para verificar conteúdo")
    print("- Se necessário, navega com 1-3 tabs dentro da página")
    print("- Procura por '100 - Autorizado o uso do CT-e.N' + 6 dígitos")
    print("- Ou variações com 'CT-e' + números")
    print()
    input("Pressione ENTER quando estiver pronto...")

    print()
    print("🔍 Iniciando extração da CTE (apenas primeira aba)...")
    print("Acompanhe os logs para ver o processo de busca.")
    print()

    # Chama a função
    resultado = extract_cte_number()

    print()
    print("=" * 70)
    print("RESULTADO:")
    if resultado:
        print(f"✅ Número da CTE encontrado: {resultado}")
        print("✅ O número foi copiado para a área de transferência")
    else:
        print("❌ Não foi possível encontrar o número da CTE")
        print("💡 Possíveis causas:")
        print("   - O resultado da CTE não está na primeira aba")
        print("   - O texto '100 - Autorizado o uso do CT-e.N' não está presente")
        print("   - O conteúdo não foi copiado corretamente")
        print("   - Verifique os logs acima para diagnóstico detalhado")
    print("=" * 70)

def main():
    """Função principal."""
    print("Teste de Extração da CTE - AutoMDF")
    print()

    while True:
        print("Opções:")
        print("1. Testar extração da CTE")
        print("2. Sair")
        print()

        try:
            choice = input("Escolha uma opção (1-2): ").strip()

            if choice == "1":
                test_cte_extraction_manual()
            elif choice == "2":
                print("Saindo...")
                break
            else:
                print("Opção inválida.")

        except KeyboardInterrupt:
            print("\nSaindo...")
            break

        print()
        print("-" * 50)
        print()

if __name__ == "__main__":
    main()