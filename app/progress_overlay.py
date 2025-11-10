"""Compact always-on-top overlay that mirrors automation progress.

Guia de edição (resumido)
- Modificável pelo usuário:
    - Textos exibidos no overlay e pequenas preferências visuais.
- Requer atenção:
    - Mudanças que afetem atributos de janela e flags podem impactar comportamento em diferentes sistemas operacionais.
- Apenas para devs:
    - Alterações profundas na lógica de posicionamento, performance de atualização e integração com o gerenciador de progresso.

Veja `docs/EDIT_GUIDELINES.md` para regras e exemplos.
"""

from __future__ import annotations

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QCursor, QGuiApplication
from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget


class ProgressOverlay(QWidget):
    """Indicador de progresso flutuante que permanece visível mesmo com a GUI minimizada."""

    # Seguro ajustar: estilo, padding e mensagens padrão.
    # Requer atenção: duração dos timers e flags de transparência — teste em todos os monitores-alvo.
    # Apenas para devs: flags de janela ou lógica de reposicionamento; valores incorretos quebram o comportamento sempre no topo.

    def __init__(self) -> None:
        flags = (
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        super().__init__(None, flags)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setWindowTitle("Auto MDF - Progresso")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 18)
        layout.setSpacing(10)

        self._message_label = QLabel("Automação em andamento...")
        self._message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._message_label.setWordWrap(True)
        self._message_label.setStyleSheet("font-weight: 600;")
        layout.addWidget(self._message_label)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setFormat("%p%")
        self._progress.setTextVisible(True)
        self._progress.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._progress.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        layout.addWidget(self._progress)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

        self.setStyleSheet(
            "background-color: rgba(20, 20, 20, 215);"
            "color: white;"
            "border-radius: 12px;"
            "padding: 6px;"
        )

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def show_indeterminate(self, message: str) -> None:
        """Exibe o overlay com um indicador de progresso contínuo."""
        self._hide_timer.stop()
        self._message_label.setText(message)
        self._progress.setRange(0, 0)
        self._progress.setFormat("...")
        self._ensure_visible()

    def update_progress(self, value: int, message: str | None = None) -> None:
        """Mostra o progresso percentual, atualizando a legenda se informado."""
        self._hide_timer.stop()
        self._progress.setRange(0, 100)
        self._progress.setValue(max(0, min(100, value)))
        if message:
            self._message_label.setText(message)
        self._progress.setFormat("%p%")
        self._ensure_visible()

    def show_result(
        self, success: bool, message: str, auto_hide_ms: int = 4000
    ) -> None:
        """Mantém o overlay visível em caso de sucesso ou erro e oculta após o atraso informado."""
        self._hide_timer.stop()
        self._progress.setRange(0, 100)
        self._progress.setValue(100 if success else 0)
        self._message_label.setText(message)
        self._progress.setFormat("%p%")
        self._ensure_visible()
        if auto_hide_ms > 0:
            self._hide_timer.start(auto_hide_ms)

    def hide_immediately(self) -> None:
        """Oculta o overlay imediatamente, sem aguardar o timer."""
        self._hide_timer.stop()
        self.hide()

    # ------------------------------------------------------------------
    # Auxiliares
    # ------------------------------------------------------------------
    def _ensure_visible(self) -> None:
        self._reposition()
        if not self.isVisible():
            self.show()
        self.raise_()

    def _reposition(self) -> None:
        """Reposiciona o overlay próximo ao canto inferior direito da tela ativa."""
        self.adjustSize()
        screen = (
            QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        )
        if screen is None:
            return
        geometry = screen.availableGeometry()
        x = geometry.right() - self.width() - 24
        y = geometry.bottom() - self.height() - 24
        self.move(max(geometry.left() + 12, x), max(geometry.top() + 12, y))
