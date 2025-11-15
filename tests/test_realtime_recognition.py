#!/usr/bin/env python3
"""Script para testar reconhecimento de imagem em tempo real."""

import sys
import time
from pathlib import Path

# Adiciona o diretório raiz ao path para importar os módulos
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from data.image_recognition import test_image_recognition_in_screenshot, diagnose_image_detection

def main():
    """Função principal para testes em tempo real."""
    print("=" * 70)
    print("TESTE DE RECONHECIMENTO DE IMAGEM EM TEMPO REAL - AutoMDF")
    print("=" * 70)
    print()

    while True:
        print("OPÇÕES:")
        print("1. Testar reconhecimento na tela atual")
        print("2. Executar diagnóstico de confiança")
        print("3. Sair")
        print()

        try:
            choice = input("Escolha uma opção (1-3): ").strip()

            if choice == "1":
                print()
                print("Testando reconhecimento de imagem na tela atual...")
                print("Certifique-se de que o formulário MDF-e está visível!")
                print()
                input("Pressione ENTER para continuar...")
                test_image_recognition_in_screenshot("recon.png")

            elif choice == "2":
                print()
                print("Executando diagnóstico de confiança...")
                diagnose_image_detection("recon.png")

            elif choice == "3":
                print("Saindo...")
                break

            else:
                print("Opção inválida. Tente novamente.")

        except KeyboardInterrupt:
            print("\nSaindo...")
            break
        except Exception as e:
            print(f"Erro: {e}")

        print()
        print("-" * 70)
        print()

if __name__ == "__main__":
    main()