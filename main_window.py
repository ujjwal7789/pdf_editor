# file: main_window.py

import sys
import math
import fitz
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QPixmap, QImage, QAction, QPainter, QColor
from PySide6.QtWidgets import (
    QMainWindow,
    QFileDialog,
    QScrollArea
)

from widgets import ClickableLabel

class PDFEditor(QMainWindow):
    SELECTION_TOLERANCE = 10

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF Editor")
        self.setFixedSize(1200, 900)

        self.doc = None
        self.current_page = None
        self.current_pixmap = None
        self.spans = []
        self.hovered_span = None
        self.selected_span = None

        self.image_label = ClickableLabel("Open a PDF file to begin.")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.clicked.connect(self.on_page_clicked)
        self.image_label.hovered.connect(self.on_page_hovered)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.image_label)
        self.setCentralWidget(self.scroll_area)
        self._create_menu_bar()

    def _create_menu_bar(self):
        # ... (unchanged)
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")
        open_action = QAction("&Open", self)
        open_action.triggered.connect(self.open_pdf)
        file_menu.addAction(open_action)
        exit_action = QAction("&Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def _distance_point_to_rect(self, point, rect):
        # ... (unchanged)
        closest_x = max(rect.x0, min(point.x, rect.x1))
        closest_y = max(rect.y0, min(point.y, rect.y1))
        return math.sqrt((point.x - closest_x)**2 + (point.y - closest_y)**2)

    def open_pdf(self):
        # ... (unchanged)
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
        
        self.current_page = self.doc.load_page(page_number)
        self.selected_span = None
        self.hovered_span = None
        self.spans = []
        page_dict = self.current_page.get_text("dict")
        
        for block in page_dict.get("blocks", []):
            if block["type"] == 0:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        self.spans.append({"text": span["text"], "font": span["font"], "size": span["size"], "color": span["color"], "rect": fitz.Rect(span["bbox"])})
                        
        pix = self.current_page.get_pixmap(dpi=150)
        self.current_pixmap = QPixmap.fromImage(QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888))
        self.image_label.setPixmap(self.current_pixmap)
        self.highlight_selection() # Initial draw with no selection

    # --- REBUILT FROM SCRATCH: The correct mapping logic ---
    def _map_widget_to_pdf_coords(self, widget_pos):
        if self.current_pixmap is None or self.current_page is None:
            return None

        # Calculate the geometry of the displayed image (with letterboxing)
        label_size = self.image_label.size()
        pixmap_size = self.image_label.pixmap().size()
        scaled_pixmap_size = pixmap_size.scaled(label_size, Qt.KeepAspectRatio)
        offset_x = (label_size.width() - scaled_pixmap_size.width()) / 2
        offset_y = (label_size.height() - scaled_pixmap_size.height()) / 2

        # Convert widget coordinates to coordinates on the scaled pixmap
        pixmap_x = widget_pos.x() - offset_x
        pixmap_y = widget_pos.y() - offset_y

        # Check if click was in the letterbox area
        if not (0 <= pixmap_x <= scaled_pixmap_size.width() and 0 <= pixmap_y <= scaled_pixmap_size.height()):
            return None

        # Convert from scaled pixmap coordinates to PDF page coordinates using a direct ratio
        pdf_page_width = self.current_page.rect.width
        pdf_page_height = self.current_page.rect.height
        
        pdf_x = (pixmap_x / scaled_pixmap_size.width()) * pdf_page_width
        pdf_y = (pixmap_y / scaled_pixmap_size.height()) * pdf_page_height

        return fitz.Point(pdf_x, pdf_y)


    def _find_span_at_position(self, position):
        # This function is now correct because its input is correct
        pdf_point = self._map_widget_to_pdf_coords(position)
        if pdf_point is None:
            return None
        
        for span in self.spans:
            if span["rect"].contains(pdf_point): return span
        
        closest_span = None
        min_dist = float('inf')
        for span in self.spans:
            dist = self._distance_point_to_rect(pdf_point, span["rect"])
            if dist < min_dist:
                min_dist = dist
                closest_span = span
        if min_dist < self.SELECTION_TOLERANCE:
            return closest_span
        return None

    def on_page_hovered(self, position):
        # ... (unchanged)
        span_under_cursor = self._find_span_at_position(position)
        if self.hovered_span != span_under_cursor:
            self.hovered_span = span_under_cursor
            self.highlight_selection()

    def on_page_clicked(self, position):
        # ... (unchanged)
        self.selected_span = self.hovered_span
        self.highlight_selection()

    # --- REBUILT FROM SCRATCH: The correct drawing logic ---
    def highlight_selection(self):
        if self.current_pixmap is None:
            self.image_label.setPixmap(QPixmap()) # Clear the label if no pixmap
            return
        
        temp_pixmap = self.current_pixmap.copy()
        painter = QPainter(temp_pixmap)

        # Recalculate geometry for drawing (essential for correctness)
        label_size = self.image_label.size()
        pixmap_size = self.image_label.pixmap().size()
        scaled_pixmap_size = pixmap_size.scaled(label_size, Qt.KeepAspectRatio)
        offset_x = (label_size.width() - scaled_pixmap_size.width()) / 2
        offset_y = (label_size.height() - scaled_pixmap_size.height()) / 2
        pdf_page_width = self.current_page.rect.width
        pdf_page_height = self.current_page.rect.height

        # Function to convert a PDF rect to a drawable Qt rect
        def pdf_to_widget_rect(pdf_rect):
            x = (pdf_rect.x0 / pdf_page_width) * scaled_pixmap_size.width() + offset_x
            y = (pdf_rect.y0 / pdf_page_height) * scaled_pixmap_size.height() + offset_y
            width = (pdf_rect.width / pdf_page_width) * scaled_pixmap_size.width()
            height = (pdf_rect.height / pdf_page_height) * scaled_pixmap_size.height()
            return QRectF(x, y, width, height)

        # Draw hover highlight
        if self.hovered_span:
            painter.fillRect(pdf_to_widget_rect(self.hovered_span["rect"]), QColor(150, 150, 150, 80))

        # Draw selection highlight
        if self.selected_span:
            painter.fillRect(pdf_to_widget_rect(self.selected_span["rect"]), QColor(0, 120, 215, 100))

        painter.end()
        self.image_label.setPixmap(temp_pixmap)