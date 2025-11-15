#!/usr/bin/env python3
"""Script de teste para verificar se a imagem de reconhecimento pode ser encontrada na tela atual."""

import sys
import os
from pathlib import Path

# Adiciona o diretório raiz ao path para importar os módulos
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from data.image_recognition import test_image_recognition_in_screenshot

def main():
    """Função principal do teste."""
    print("=" * 60)
    print("TESTE DE RECONHECIMENTO DE IMAGEM - AutoMDF")
    print("=" * 60)
    print()
    print("Este teste verifica se a imagem 'recon.png' pode ser encontrada")
    print("na tela atual (que deve conter o formulário MDF-e aberto).")
    print()
    print("INSTRUÇÕES:")
    print("1. Abra o navegador com o sistema Invoisys")
    print("2. Navegue até a página do formulário MDF-e")
    print("3. Certifique-se de que o formulário está visível na tela")
    print("4. Execute este script")
    print()
    input("Pressione ENTER quando estiver pronto para o teste...")

    print()
    print("Iniciando teste...")
    print()

    # Executa o teste
    test_image_recognition_in_screenshot("recon.png")

    print()
    print("=" * 60)
    print("TESTE CONCLUÍDO")
    print("=" * 60)

if __name__ == "__main__":
    main()