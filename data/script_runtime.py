"""Utilitários compartilhados de tempo de execução para scripts Auto MDF.

Centraliza o tratamento de diálogos integrados ao bridge, a restauração de
foco do navegador e utilitários de progresso/erros para manter cada script
leve e consistente. Reunir a lógica aqui reduz duplicidade e facilita aplicar
correções de compatibilidade (por exemplo, ajustes de tempo) em todo o
catálogo de scripts.
"""

from __future__ import annotations

import os
import sys
import time
from contextlib import suppress
from datetime import datetime
from typing import Any, Optional, Sequence

try:
    from .automation_focus import focus
except Exception:  # pragma: no cover - fallback when packages are missing
    focus = None  # type: ignore[assignment]

try:
    from .image_recognition import (
        wait_for_invoisys_form,
        wait_for_page_load,
        is_image_present,
        diagnose_image_detection,
        wait_for_page_reload_and_form,
    )
except Exception:  # pragma: no cover - fallback when packages are missing
    wait_for_invoisys_form = None  # type: ignore[assignment]
    wait_for_page_load = None  # type: ignore[assignment]
    is_image_present = None  # type: ignore[assignment]
    diagnose_image_detection = None  # type: ignore[assignment]
    wait_for_page_reload_and_form = None  # type: ignore[assignment]

from .dialog_service import DialogService

DEFAULT_TOTAL_STEPS = 100

_ORIGINAL_SLEEP = time.sleep
_SLEEP_PATCHED = False


def _log_event(message: str, *, level: str = "info") -> None:
    """Emite uma entrada padronizada de log diagnóstico para os scripts."""

    timestamp = datetime.now().strftime("%H:%M:%S")
    label = level.upper()
    print(f"[AutoMDF][{label}][{timestamp}] {message}", flush=True)


def disable_caps_lock() -> None:
    """Desabilita o Caps Lock se estiver ativo."""
    try:
        import ctypes
        VK_CAPITAL = 0x14  # código da tecla Caps Lock
        
        # Obtém o estado atual do Caps Lock
        caps_state = ctypes.windll.user32.GetKeyState(VK_CAPITAL)
        
        # Se estiver ativo, desliga
        if caps_state & 1:
            # Pressiona Caps Lock
            ctypes.windll.user32.keybd_event(VK_CAPITAL, 0, 0, 0)
            # Solta Caps Lock
            ctypes.windll.user32.keybd_event(VK_CAPITAL, 0, 2, 0)
            _log_event("Caps Lock desabilitado", level="debug")
    except Exception as e:
        _log_event(f"Erro ao desabilitar Caps Lock: {e}", level="warning")


def _resolve_bridge_override() -> Optional[bool]:
    """Determina se o bridge de diálogo deve ser forçado ligado ou desligado."""

    force = os.environ.get("MDF_FORCE_BRIDGE")
    if force is not None:
        normalized = force.strip().lower()
        return normalized in {"1", "true", "yes", "on"}

    return False


_BRIDGE_OVERRIDE = _resolve_bridge_override()
_DIALOG_SERVICE = DialogService(bridge_enabled=False)

if _BRIDGE_OVERRIDE is False:
    _log_event("Bridge de diálogo desativada (forçando Qt).", level="debug")
elif _BRIDGE_OVERRIDE is True:
    _log_event("Bridge de diálogo forçada explicitamente.", level="debug")


def configure_stdio() -> None:
    """Força saída UTF-8 para consoles Windows se comportarem como o bridge da GUI."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def ensure_browser_focus(
    *,
    target_tab: Optional[int] = None,
    preserve_tab: bool = False,
    allow_taskbar: bool = True,
    retries: int = 6,
    retry_delay: float = 0.25,
    switch_to_target_tab: Optional[bool] = None,
) -> bool:
    """Tenta trazer o navegador para o primeiro plano.

    O helper agora suporta selecionar uma aba específica do navegador (1-9).
    Quando ``target_tab`` é informado a função garante que o controlador
    ajuste essa aba e não preserve a atual.
    """
    if focus is None:
        _log_event(
            "automation_focus module indisponível; pulando restauração de foco.",
            level="warning",
        )
        return False

    if _DIALOG_SERVICE.is_modal_active():
        _log_event(
            "Restauração de foco ignorada porque um diálogo Qt modal está ativo.",
            level="debug",
        )
        return False

    if target_tab is not None:
        with suppress(Exception):
            focus.target_tab = target_tab
        preserve_tab = False

    focus.prepare_taskbar_retry()
    time.sleep(0.05)

    attempts = max(1, retries)
    pause = max(0.05, retry_delay)

    effective_switch = switch_to_target_tab
    if effective_switch is None:
        effective_switch = not preserve_tab
    if target_tab is not None:
        effective_switch = True

    for attempt in range(attempts):
        with suppress(Exception):
            if focus.ensure_browser_focus(
                allow_taskbar=allow_taskbar,
                preserve_tab=preserve_tab,
                switch_to_target_tab=effective_switch,
            ) and focus.wait_until_browser_active(
                force_tab=bool(effective_switch and not preserve_tab)
            ):
                _log_event("Foco do navegador restabelecido com sucesso.")
                return True
        if attempt < attempts - 1:
            time.sleep(pause)

    if focus.wait_until_browser_active(
        force_tab=bool(effective_switch and not preserve_tab)
    ):
        _log_event("Foco do navegador ativo detectado após tentativas auxiliares.")
        return True

    _log_event(
        "Não foi possível restabelecer o foco do navegador após o alerta.",
        level="warning",
    )
    return False


def switch_browser_tab(
    tab: int,
    *,
    ensure_focus: bool = True,
    allow_taskbar: bool = True,
) -> bool:
    """Alterna o foco da automação para uma aba específica do navegador."""

    if focus is None:
        _log_event(
            "automation_focus module indisponível; não é possível trocar de aba.",
            level="warning",
        )
        return False

    try:
        success = focus.switch_to_tab(
            tab,
            ensure_focus=ensure_focus,
            allow_taskbar=allow_taskbar,
        )
    except AttributeError:
        focus.target_tab = tab
        success = ensure_browser_focus(
            target_tab=tab,
            allow_taskbar=allow_taskbar,
            preserve_tab=False,
        )

    if success:
        _log_event(f"Aba do navegador alterada para {tab}.", level="debug")
    else:
        _log_event(f"Não foi possível alternar para a aba {tab}.", level="warning")
    return success


def prompt_topmost(*args, **kwargs) -> Optional[str]:
    """Exibe um prompt sempre visível, alinhado ao comportamento do bridge da GUI."""
    require_input = bool(kwargs.pop("require_input", False))
    allow_cancel = bool(kwargs.pop("allow_cancel", True))
    cancel_message = kwargs.pop("cancel_message", "")

    text, title, default_value = _parse_text_title_defaults(args, kwargs, "Entrada")
    _log_event(
        f"Solicitando prompt (title='{title}', require_input={require_input}, allow_cancel={allow_cancel}).",
        level="debug",
    )
    _DIALOG_SERVICE.refresh_environment()

    def restore_focus() -> None:
        ensure_browser_focus(preserve_tab=True)

    try:
        value = _DIALOG_SERVICE.prompt(
            text=str(text or ""),
            title=str(title or "Entrada"),
            default=str(default_value or "") if default_value is not None else "",
            require_input=require_input,
            allow_cancel=allow_cancel,
            cancel_message=str(cancel_message or ""),
            on_restore_focus=restore_focus,
            parent=None,
        )
    except Exception as exc:  # pragma: no cover - capture unexpected GUI failures
        _log_event(f"Falha ao exibir prompt Qt: {exc}", level="error")
        return None

    if value is None:
        _log_event("Prompt encerrado sem valor informado.", level="warning")
        return None

    trimmed = value.strip()
    _log_event(f"Resposta recebida do prompt (length={len(trimmed)}).", level="debug")
    return trimmed or value


def alert_topmost(*args, **kwargs) -> str:
    """Mostra um alerta sempre visível, usando o bridge da GUI quando possível."""
    text, title, button_default = _parse_text_title_defaults(args, kwargs, "Informação")
    button_text = kwargs.get("button", button_default or "OK")

    _DIALOG_SERVICE.refresh_environment()

    def restore_focus() -> None:
        ensure_browser_focus(preserve_tab=True)

    try:
        _DIALOG_SERVICE.alert(
            text=text or "",
            title=title or "Informação",
            button=button_text or "OK",
            on_restore_focus=restore_focus,
            parent=None,
        )
        _log_event(
            f"Alerta exibido (title='{title}', button='{button_text}').", level="debug"
        )
    except Exception as exc:  # pragma: no cover
        _log_event(f"Falha ao exibir alerta Qt: {exc}", level="error")
    return button_text or "OK"


def confirm_topmost(*args, **kwargs) -> Optional[str]:
    """Exibe um diálogo de confirmação que permanece em destaque."""
    text, title, _ = _parse_text_title_defaults(args, kwargs, "Confirmação")
    buttons = kwargs.get("buttons") or ["OK", "Cancel"]
    if not isinstance(buttons, list) or not buttons:
        buttons = ["OK", "Cancel"]
    else:
        buttons = [str(btn) for btn in buttons]

    _DIALOG_SERVICE.refresh_environment()

    def restore_focus() -> None:
        ensure_browser_focus(preserve_tab=True)

    try:
        choice = _DIALOG_SERVICE.confirm(
            text=text or "",
            title=title or "Confirmação",
            buttons=buttons,
            on_restore_focus=restore_focus,
            parent=None,
        )
    except Exception as exc:  # pragma: no cover
        _log_event(f"Falha ao exibir confirmação Qt: {exc}", level="error")
        return None

    if choice is None:
        fallback = "Cancel" if "Cancel" in buttons else buttons[-1]
        _log_event(
            f"Confirmação sem resposta; retornando fallback '{fallback}'.",
            level="warning",
        )
        return fallback

    trimmed = choice.strip()
    _log_event(f"Confirmação respondida com '{trimmed}'.", level="debug")
    return trimmed or choice


def register_exception_handler(progress_manager: Any) -> None:
    """Garante que erros não capturados apareçam no bridge da GUI e nos logs."""
    original_hook = sys.excepthook

    def _handle(exc_type, exc_value, exc_traceback):
        if exc_type is SystemExit:
            original_hook(exc_type, exc_value, exc_traceback)
            return
        
        # Verifica se é uma exceção de failsafe do PyAutoGUI
        is_failsafe = "FailSafe" in exc_type.__name__
        
        if is_failsafe:
            # Para failsafe, mostra um prompt de confirmação
            try:
                result = confirm_topmost(
                    "O failsafe do PyAutoGUI foi ativado!\n\n"
                    "A automação foi interrompida porque o mouse foi movido para um canto da tela.\n\n"
                    "Deseja parar a automação?",
                    title="Failsafe Ativado",
                    buttons=["Sim", "Não"]
                )
                if result == "Sim":
                    with suppress(Exception):
                        progress_manager.error("Automação interrompida pelo usuário (failsafe ativado).")
                    _log_event("Automação interrompida pelo failsafe.", level="info")
                    raise SystemExit(0)
                else:
                    # Usuário escolheu continuar, mas como é failsafe, talvez ignore ou log
                    _log_event("Failsafe ativado, mas usuário optou por continuar.", level="warning")
                    return  # Não propaga a exceção
            except Exception:
                # Se o confirm falhar, trata como erro normal
                pass
        
        with suppress(Exception):
            error_msg = "Automação interrompida pelo usuário (failsafe ativado)." if is_failsafe else f"Erro inesperado: {exc_value}"
            progress_manager.error(error_msg)
        _log_event(
            f"Exceção não tratada: {exc_type.__name__}: {exc_value}", level="error"
        )
        try:
            alert_topmost(
                "Ocorreu um erro inesperado. Verifique o log para detalhes.\n\n"
                f"{exc_value}"
            )
        finally:
            original_hook(exc_type, exc_value, exc_traceback)

    sys.excepthook = _handle


def checkpoint(progress_manager: Any, percent: int, step: str) -> None:
    """Atualiza o progresso de forma consistente entre os scripts."""
    progress_manager.update(percent, step, force_save=True)  # Forçar save em checkpoints
    progress_manager.add_log(step)


def update_progress_realtime(progress_manager: Any, percent: int, step: str) -> None:
    """Atualiza o progresso em tempo real sem forçar salvamento (salva apenas se percentual mudou)."""
    progress_manager.update(percent, step, force_save=False)
    progress_manager.add_log(step)




def abort(progress_manager: Any, message: str) -> None:
    """Interrompe a execução após informar o motivo ao operador."""
    progress_manager.error(message)
    raise SystemExit(1)


def apply_pyautogui_bridge(pyautogui_module: Any) -> None:
    """Ajusta diálogos e temporizações do PyAutoGUI para compatibilidade com o bridge."""
    setattr(pyautogui_module, "prompt", prompt_topmost)
    setattr(pyautogui_module, "alert", alert_topmost)
    setattr(pyautogui_module, "confirm", confirm_topmost)
    pyautogui_module.FAILSAFE = True

    if pause_env := os.environ.get("MDF_PYAUTOGUI_PAUSE"):
        with suppress(ValueError):
            pause_value = float(pause_env)
            if pause_value >= 0:
                pyautogui_module.PAUSE = pause_value

    if min_sleep_env := os.environ.get("MDF_PYAUTOGUI_MIN_SLEEP"):
        with suppress(ValueError):
            min_sleep_value = float(min_sleep_env)
            if min_sleep_value >= 0:
                pyautogui_module.MINIMUM_SLEEP = min_sleep_value

    _apply_sleep_scaling()


def _apply_sleep_scaling() -> None:
    global _SLEEP_PATCHED
    if _SLEEP_PATCHED:
        return

    env = os.environ
    short_threshold = _safe_float(
        env.get("MDF_SLEEP_THRESHOLD_SHORT"), default=0.35, minimum=0.0
    )
    medium_threshold = _safe_float(
        env.get("MDF_SLEEP_THRESHOLD_MEDIUM"), default=1.2, minimum=short_threshold
    )

    short_scale = _safe_float(
        env.get("MDF_SLEEP_SCALE_SHORT"), default=1.0, minimum=0.0
    )
    medium_scale = _safe_float(
        env.get("MDF_SLEEP_SCALE_MEDIUM"), default=1.0, minimum=0.0
    )
    long_scale = _safe_float(env.get("MDF_SLEEP_SCALE_LONG"), default=1.0, minimum=0.0)

    def _scaled_sleep(seconds: float) -> None:
        duration = seconds if isinstance(seconds, (int, float)) else 0.0
        if duration < 0:
            duration = 0.0
        if duration <= short_threshold:
            factor = short_scale
        elif duration <= medium_threshold:
            factor = medium_scale
        else:
            factor = long_scale
        adjusted = duration * factor
        if adjusted < 0:
            adjusted = 0.0
        _ORIGINAL_SLEEP(adjusted)

    time.sleep = _scaled_sleep
    _SLEEP_PATCHED = True


def _safe_float(raw: Optional[str], *, default: float, minimum: float) -> float:
    try:
        value = float(raw) if raw is not None else default
    except (TypeError, ValueError):
        value = default
    return max(minimum, value)


def _parse_text_title_defaults(
    args: Sequence[Any], kwargs: dict[str, Any], default_title: str
) -> tuple[str, str, Optional[str]]:
    text = ""
    title = default_title
    default_value: Optional[str] = None

    if args:
        text = args[0]
    if len(args) > 1:
        title = args[1]
    if len(args) > 2:
        default_value = args[2]

    if "text" in kwargs:
        text = kwargs["text"]
    if "title" in kwargs:
        title = kwargs["title"]
    if "default" in kwargs:
        default_value = kwargs["default"]

    return text, title, default_value


# ------------------------------------------------------------------
# Reconhecimento de Imagem
# ------------------------------------------------------------------

def wait_for_form_load(timeout: float = 30.0) -> bool:
    """Aguarda o carregamento do formulário MDF-e do Invoisys usando reconhecimento de imagem.

    Args:
        timeout: Tempo máximo para aguardar em segundos

    Returns:
        True se o formulário foi detectado, False caso contrário
    """
    if wait_for_invoisys_form is None:
        _log_event("Reconhecimento de imagem não disponível", level="warning")
        return False

    try:
        return wait_for_invoisys_form(timeout=timeout)
    except Exception as e:
        _log_event(f"Erro no reconhecimento de imagem: {e}", level="error")
        return False


def wait_for_image_on_screen(
    image_name: str,
    timeout: float = 30.0,
    confidence: float = 0.9,
) -> bool:
    """Aguarda uma imagem específica aparecer na tela.

    Args:
        image_name: Nome do arquivo de imagem na pasta img/
        timeout: Tempo máximo para aguardar em segundos
        confidence: Confiança mínima para reconhecimento (0.0-1.0)

    Returns:
        True se a imagem foi encontrada, False caso contrário
    """
    if wait_for_page_load is None:
        _log_event("Reconhecimento de imagem não disponível", level="warning")
        return False

    try:
        return wait_for_page_load(image_name, timeout=timeout, confidence=confidence)
    except Exception as e:
        _log_event(f"Erro no reconhecimento de imagem: {e}", level="error")
        return False


def check_image_present(
    image_name: str,
    confidence: float = 0.9,
) -> bool:
    """Verifica se uma imagem está presente na tela.

    Args:
        image_name: Nome do arquivo de imagem na pasta img/
        confidence: Confiança mínima para reconhecimento (0.0-1.0)

    Returns:
        True se a imagem foi encontrada, False caso contrário
    """
    if is_image_present is None:
        return False

    try:
        return is_image_present(image_name, confidence=confidence)
    except Exception as e:
        _log_event(f"Erro ao verificar imagem: {e}", level="error")
        return False


__all__ = [
    "DEFAULT_TOTAL_STEPS",
    "abort",
    "alert_topmost",
    "apply_pyautogui_bridge",
    "checkpoint",
    "check_image_present",
    "confirm_topmost",
    "configure_stdio",
    "diagnose_image_detection",
    "ensure_browser_focus",
    "prompt_topmost",
    "register_exception_handler",
    "switch_browser_tab",
    "update_progress_realtime",
    "wait_for_form_load",
    "wait_for_image_on_screen",
    "wait_for_page_reload_and_form",
]
