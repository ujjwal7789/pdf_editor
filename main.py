import sys
import fitz  # PyMuPDF
# --- MODIFIED: Import QPointF for floating-point coordinates ---
from PySide6.QtCore import Qt, Signal, QPointF, QRectF
from PySide6.QtGui import QPixmap, QImage, QAction, QPainter, QColor
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QFileDialog,
    QScrollArea
)

class ClickableLabel(QLabel):
    # --- MODIFIED: Signal now emits a QPointF ---
    clicked = Signal(QPointF)

    def __init__(self, parent=None):
        super().__init__(parent)

    def mousePressEvent(self, event):
        # --- MODIFIED: Use event.position() for precise, floating-point coordinates ---
        self.clicked.emit(event.position())
        super().mousePressEvent(event)


class PDFEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF Editor")
        self.setGeometry(100, 100, 800, 600)

        self.doc = None
        self.current_page_num = 0
        self.current_pixmap = None
        self.text_blocks = []
        self.selected_block = None
        self.scale_factor = 1.0

        self.image_label = ClickableLabel("Open a PDF file to begin.")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.clicked.connect(self.on_page_clicked)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.image_label)

        self.setCentralWidget(self.scroll_area)

        self._create_menu_bar()

    def _create_menu_bar(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")
        open_action = QAction("&Open", self)
        open_action.triggered.connect(self.open_pdf)
        file_menu.addAction(open_action)
        exit_action = QAction("&Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def open_pdf(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Open PDF File", "", "PDF Files (*.pdf)")
        if filepath:
            try:
                self.doc = fitz.open(filepath)
                self.display_page(0)
            except Exception as e:
                print(f"Error opening PDF: {e}")
                self.image_label.setText("Failed to load PDF.")

    def display_page(self, page_number):
        if not self.doc or not (0 <= page_number < self.doc.page_count):
            return

        self.current_page_num = page_number
        page = self.doc.load_page(self.current_page_num)
        
        self.selected_block = None
        self.text_blocks = page.get_text("blocks")

        pix = page.get_pixmap()
        self.current_pixmap = QPixmap.fromImage(
            QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
        )
        
        # This calculation remains the same, but the inputs will be more precise
        self.scale_factor = self.current_pixmap.width() / page.rect.width
        
        self.image_label.setPixmap(self.current_pixmap)

    # The 'position' argument now automatically receives a QPointF
    def on_page_clicked(self, position):
        if not self.doc:
            return

        pdf_x = position.x() / self.scale_factor
        pdf_y = position.y() / self.scale_factor
        pdf_point = fitz.Point(pdf_x, pdf_y)

        found_block = None
        for block in self.text_blocks:
            x0, y0, x1, y1, _, _, _ = block
            block_rect = fitz.Rect(x0, y0, x1, y1)
            if block_rect.contains(pdf_point):
                found_block = block
                break
        
        self.selected_block = found_block
        self.highlight_selection()

    def highlight_selection(self):
        if self.current_pixmap is None:
            return
            
        temp_pixmap = self.current_pixmap.copy()

        if self.selected_block:
            x0, y0, x1, y1, _, _, _ = self.selected_block
            
            highlight_rect = QRectF(
                x0 * self.scale_factor,
                y0 * self.scale_factor,
                (x1 - x0) * self.scale_factor,
                (y1 - y0) * self.scale_factor
            )

            painter = QPainter(temp_pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            highlight_color = QColor(0, 120, 215, 100)
            painter.fillRect(highlight_rect, highlight_color)
            painter.end()

        self.image_label.setPixmap(temp_pixmap)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PDFEditor()
    window.show()
    sys.exit(app.exec())

