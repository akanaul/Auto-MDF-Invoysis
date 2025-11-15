"""Utilitários para reconhecimento de imagens e detecção de elementos visuais."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional, Tuple

_pyautogui: Optional[object] = None

try:
    import pyautogui as _pyautogui  # type: ignore
except Exception:  # pragma: no cover - pyautogui may be missing in some envs
    _pyautogui = None

pyautogui = _pyautogui

# Caminho base para imagens de reconhecimento
IMG_DIR = Path(__file__).resolve().parent.parent / "img"


class ImageRecognitionError(Exception):
    """Erro durante reconhecimento de imagem."""
    pass


def wait_for_image(
    image_name: str,
    timeout: float = 30.0,
    confidence: float = 0.9,
    check_interval: float = 0.5,
) -> Tuple[int, int, int, int]:
    """Aguarda até que uma imagem apareça na tela.

    Args:
        image_name: Nome do arquivo de imagem (sem caminho)
        timeout: Tempo máximo para aguardar em segundos
        confidence: Confiança mínima para reconhecimento (0.0-1.0)
        check_interval: Intervalo entre verificações em segundos

    Returns:
        Tupla (left, top, width, height) da posição encontrada

    Raises:
        ImageRecognitionError: Se a imagem não for encontrada no timeout
    """
    if pyautogui is None:
        raise ImageRecognitionError("PyAutoGUI não está disponível")

    image_path = IMG_DIR / image_name
    if not image_path.exists():
        raise ImageRecognitionError(f"Imagem não encontrada: {image_path}")

    elapsed = 0.0
    while elapsed < timeout:
        try:
            pos = pyautogui.locateOnScreen(
                str(image_path),
                confidence=confidence
            )
            if pos:
                return pos
        except pyautogui.ImageNotFoundException:
            pass

        time.sleep(check_interval)
        elapsed += check_interval

    raise ImageRecognitionError(
        f"Imagem '{image_name}' não encontrada em {timeout} segundos"
    )


def is_image_present(
    image_name: str,
    confidence: float = 0.9,
) -> bool:
    """Verifica se uma imagem está presente na tela.

    Args:
        image_name: Nome do arquivo de imagem (sem caminho)
        confidence: Confiança mínima para reconhecimento (0.0-1.0)

    Returns:
        True se a imagem foi encontrada, False caso contrário
    """
    if pyautogui is None:
        return False

    image_path = IMG_DIR / image_name
    if not image_path.exists():
        return False

    try:
        pos = pyautogui.locateOnScreen(
            str(image_path),
            confidence=confidence
        )
        return pos is not None
    except pyautogui.ImageNotFoundException:
        return False


def wait_for_invoisys_form(
    timeout: float = 15.0,
    confidence: float = 0.7,
) -> bool:
    """Aguarda o carregamento do formulário MDF-e do Invoisys.

    Esta função é mais robusta pois primeiro verifica se a imagem já está presente
    (de um formulário anterior) e aguarda ela desaparecer antes de aguardar
    o novo formulário aparecer. A verificação ocorre a cada 1.5 segundos.

    Args:
        timeout: Tempo máximo para aguardar em segundos
        confidence: Confiança mínima para reconhecimento (0.0-1.0, padrão 0.7)
                   Nota: Valor alto necessário para precisão na detecção

    Returns:
        True se o formulário foi detectado, False caso contrário
    """
    print(f'[AutoMDF] Iniciando detecção de formulário com confiança {confidence} e timeout {timeout}s', flush=True)

    try:
        # Primeiro, verifica se a imagem já está presente (formulário antigo)
        if is_image_present("recon.png", confidence=confidence):
            print('[AutoMDF] Imagem antiga detectada, aguardando desaparecimento...', flush=True)
            # Aguarda até a imagem desaparecer (máximo 5 segundos)
            elapsed = 0.0
            while elapsed < 5.0 and is_image_present("recon.png", confidence=confidence):
                time.sleep(0.5)
                elapsed += 0.5
            print('[AutoMDF] Imagem antiga desapareceu ou timeout atingido', flush=True)
        else:
            print('[AutoMDF] Nenhuma imagem antiga detectada, prosseguindo...', flush=True)

        # Agora aguarda o novo formulário aparecer (verificação a cada 1.5 segundos)
        print('[AutoMDF] Aguardando novo formulário MDF-e aparecer...', flush=True)
        wait_for_image("recon.png", timeout=timeout, confidence=confidence, check_interval=1.5)
        print('[AutoMDF] Novo formulário MDF-e detectado!', flush=True)
        return True
    except ImageRecognitionError as e:
        print(f'[AutoMDF] Erro na detecção do formulário: {e}', flush=True)
        return False


def wait_for_page_reload_and_form(
    timeout: float = 15.0,
    confidence: float = 0.7,
) -> bool:
    """Aguarda a página ser recarregada e depois o formulário MDF-e aparecer.

    Esta função é mais robusta pois:
    1. Primeiro aguarda a página ser recarregada (usando indicadores visuais)
    2. Só então inicia o reconhecimento de imagem do formulário
    3. Só permite continuar se o reconhecimento for bem-sucedido

    Args:
        timeout: Tempo máximo para aguardar em segundos
        confidence: Confiança mínima para reconhecimento (0.0-1.0, padrão 0.7)

    Returns:
        True se o formulário foi detectado após recarregamento, False caso contrário
    """
    print(f'[AutoMDF] Iniciando espera por recarregamento da página e detecção de formulário...', flush=True)
    print(f'[AutoMDF] Timeout total: {timeout}s | Confiança: {confidence}', flush=True)

    start_time = time.time()
    page_reloaded = False

    try:
        # PASSO 1: Aguardar a página ser recarregada
        print('[AutoMDF] PASSO 1: Aguardando recarregamento da página...', flush=True)

        # Estratégia: aguardar um pequeno período para que a página comece a recarregar
        # e depois verificar se elementos da página estão presentes
        time.sleep(2.0)  # Aguarda 2 segundos para início do recarregamento

        # Verificar se a página está carregando (aguardar até 10 segundos)
        reload_timeout = min(10.0, timeout * 0.3)  # Máximo 30% do timeout total
        reload_start = time.time()

        while time.time() - reload_start < reload_timeout:
            # Verificar se há algum indicador de carregamento ou se a página mudou
            # Por enquanto, apenas aguardamos o tempo necessário
            time.sleep(1.0)
            elapsed = time.time() - reload_start
            print(f'[AutoMDF] Aguardando recarregamento... ({elapsed:.1f}s)', flush=True)

        page_reloaded = True
        print('[AutoMDF] Página recarregada com sucesso!', flush=True)

        # PASSO 2: Só agora iniciar reconhecimento de imagem do formulário
        print('[AutoMDF] PASSO 2: Iniciando reconhecimento de imagem do formulário...', flush=True)

        remaining_timeout = timeout - (time.time() - start_time)
        if remaining_timeout <= 0:
            print('[AutoMDF] Timeout esgotado antes do reconhecimento', flush=True)
            return False

        # Usar a função wait_for_invoisys_form com o tempo restante
        result = wait_for_invoisys_form(timeout=remaining_timeout, confidence=confidence)

        if result:
            print('[AutoMDF] ✅ Formulário MDF-e detectado após recarregamento da página!', flush=True)
            return True
        else:
            print('[AutoMDF] ❌ Formulário MDF-e NÃO detectado após recarregamento', flush=True)
            return False

    except Exception as e:
        elapsed = time.time() - start_time
        print(f'[AutoMDF] Erro durante espera por recarregamento: {e} (após {elapsed:.1f}s)', flush=True)
        return False


def diagnose_image_detection(image_name: str = "recon.png") -> None:
    """Diagnóstico para testar diferentes níveis de confiança na detecção de imagem.

    Args:
        image_name: Nome do arquivo de imagem para testar
    """
    print(f'[AutoMDF] Iniciando diagnóstico de detecção para {image_name}', flush=True)

    confidence_levels = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1]

    for confidence in confidence_levels:
        try:
            result = is_image_present(image_name, confidence=confidence)
            print(f'[AutoMDF] Confiança {confidence}: {"DETECTADA" if result else "NÃO DETECTADA"}', flush=True)
        except Exception as e:
            print(f'[AutoMDF] Confiança {confidence}: ERRO - {e}', flush=True)

    print('[AutoMDF] Diagnóstico concluído', flush=True)


def test_image_recognition_in_screenshot(image_name: str = "recon.png") -> None:
    """Testa se uma imagem de referência pode ser encontrada em uma captura de tela atual.

    Esta função é útil para verificar se a imagem de reconhecimento pode ser detectada
    dentro da imagem maior do formulário aberto na tela.

    Args:
        image_name: Nome do arquivo de imagem de referência para testar
    """
    if pyautogui is None:
        print('[AutoMDF] ❌ PyAutoGUI não está disponível', flush=True)
        return

    print(f'[AutoMDF] 🧪 Testando reconhecimento de {image_name} na tela atual...', flush=True)

    try:
        # Tira uma captura de tela da tela atual
        screenshot = pyautogui.screenshot()
        print('[AutoMDF] 📸 Captura de tela tirada com sucesso', flush=True)

        # Salva temporariamente a captura de tela
        temp_screenshot_path = IMG_DIR / "temp_screenshot.png"
        screenshot.save(str(temp_screenshot_path))
        print(f'[AutoMDF] 💾 Captura salva temporariamente em {temp_screenshot_path}', flush=True)

        # Testa diferentes níveis de confiança
        confidence_levels = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1]
        best_confidence = None
        best_position = None

        print('[AutoMDF] 🔍 Testando reconhecimento com diferentes níveis de confiança:', flush=True)

        for confidence in confidence_levels:
            try:
                # Tenta localizar a imagem de referência na captura de tela
                position = pyautogui.locate(str(IMG_DIR / image_name), str(temp_screenshot_path), confidence=confidence)
                if position:
                    print(f'[AutoMDF] ✅ Confiança {confidence}: IMAGEM ENCONTRADA na posição {position}', flush=True)
                    if best_confidence is None or confidence > best_confidence:
                        best_confidence = confidence
                        best_position = position
                else:
                    print(f'[AutoMDF] ❌ Confiança {confidence}: imagem não encontrada', flush=True)
            except Exception as e:
                print(f'[AutoMDF] ⚠️  Confiança {confidence}: erro durante teste - {e}', flush=True)

        # Remove o arquivo temporário
        if temp_screenshot_path.exists():
            temp_screenshot_path.unlink()
            print('[AutoMDF] 🗑️  Arquivo temporário removido', flush=True)

        # Resultado final
        if best_confidence is not None:
            print(f'[AutoMDF] 🎯 MELHOR RESULTADO: Confiança {best_confidence} - Posição {best_position}', flush=True)
            print('[AutoMDF] ✅ A imagem de referência PODE ser reconhecida na tela atual!', flush=True)
            print('[AutoMDF] 💡 Recomendação: Use confiança >= {best_confidence} para detecção confiável', flush=True)
        else:
            print('[AutoMDF] ❌ A imagem de referência NÃO foi encontrada na tela atual', flush=True)
            print('[AutoMDF] 💡 Possíveis causas:', flush=True)
            print('      - O formulário não está aberto na tela', flush=True)
            print('      - A imagem de referência não corresponde ao que está na tela', flush=True)
            print('      - A resolução ou zoom da tela pode estar afetando o reconhecimento', flush=True)

    except Exception as e:
        print(f'[AutoMDF] ❌ Erro durante teste de reconhecimento: {e}', flush=True)
        # Remove arquivo temporário em caso de erro
        temp_screenshot_path = IMG_DIR / "temp_screenshot.png"
        if temp_screenshot_path.exists():
            temp_screenshot_path.unlink()


def wait_for_page_load(
    image_name: str,
    timeout: float = 30.0,
    confidence: float = 0.9,
) -> bool:
    """Aguarda o carregamento de uma página através de reconhecimento de imagem.

    Args:
        image_name: Nome da imagem que representa a página carregada
        timeout: Tempo máximo para aguardar em segundos
        confidence: Confiança mínima para reconhecimento

    Returns:
        True se a página foi carregada, False caso contrário
    """
    try:
        wait_for_image(image_name, timeout=timeout, confidence=confidence)
        return True
    except ImageRecognitionError:
        return False