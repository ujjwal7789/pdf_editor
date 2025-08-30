# file: widgets.py

from PySide6.QtCore import Signal, QPointF
from PySide6.QtWidgets import QLabel

class ClickableLabel(QLabel):
    """
    A custom QLabel that emits signals for hovering and clicking,
    providing precise QPointF coordinates.
    """
    clicked = Signal(QPointF)
    hovered = Signal(QPointF) # NEW: Signal for mouse movement

    def __init__(self, parent=None):
        super().__init__(parent)
        # NEW: Enable mouse tracking to get hover events
        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        self.clicked.emit(event.position())
        super().mousePressEvent(event)

    # NEW: Handle mouse movement (hover) events
    def mouseMoveEvent(self, event):
        self.hovered.emit(event.position())
        super().mouseMoveEvent(event)