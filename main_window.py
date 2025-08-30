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
    SELECTION_TOLERANCE = 15

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF Editor")
        self.setGeometry(100, 100, 800, 600)

        self.doc = None
        self.current_page_num = 0
        self.current_pixmap = None
        self.scale_factor = 1.0
        self.spans = []
        
        # NEW: We now track two states: hovered and selected
        self.hovered_span = None
        self.selected_span = None

        self.image_label = ClickableLabel("Open a PDF file to begin.")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.clicked.connect(self.on_page_clicked)
        self.image_label.hovered.connect(self.on_page_hovered) # NEW: Connect hover signal

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.image_label)
        self.setCentralWidget(self.scroll_area)
        self._create_menu_bar()

    def _create_menu_bar(self):
        # ... (This method remains unchanged)
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")
        open_action = QAction("&Open", self)
        open_action.triggered.connect(self.open_pdf)
        file_menu.addAction(open_action)
        exit_action = QAction("&Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def _distance_point_to_rect(self, point, rect):
        # ... (This method remains unchanged)
        closest_x = max(rect.x0, min(point.x, rect.x1))
        closest_y = max(rect.y0, min(point.y, rect.y1))
        return math.sqrt((point.x - closest_x)**2 + (point.y - closest_y)**2)

    def open_pdf(self):
        # ... (This method remains unchanged)
        filepath, _ = QFileDialog.getOpenFileName(self, "Open PDF File", "", "PDF Files (*.pdf)")
        if filepath:
            try:
                self.doc = fitz.open(filepath)
                self.display_page(0)
            except Exception as e:
                print(f"Error opening PDF: {e}")
                self.image_label.setText("Failed to load PDF.")

    def display_page(self, page_number):
        # ... (This method is mostly unchanged, just clears new states)
        if not self.doc or not (0 <= page_number < self.doc.page_count):
            return
        self.current_page_num = page_number
        self.selected_span = None
        self.hovered_span = None
        self.spans = []
        page = self.doc.load_page(self.current_page_num)
        page_dict = page.get_text("dict")
        for block in page_dict.get("blocks", []):
            if block["type"] == 0:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        span_info = {
                            "text": span["text"], "font": span["font"],
                            "size": span["size"], "color": span["color"],
                            "rect": fitz.Rect(span["bbox"])
                        }
                        self.spans.append(span_info)
        pix = page.get_pixmap()
        self.current_pixmap = QPixmap.fromImage(
            QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
        )
        self.scale_factor = self.current_pixmap.width() / page.rect.width
        self.image_label.setPixmap(self.current_pixmap)
    
    # NEW: This method handles the logic for finding the span under the cursor
    def _find_span_at_position(self, position):
        if not self.doc or not self.spans:
            return None
        pdf_point = fitz.Point(position.x() / self.scale_factor, position.y() / self.scale_factor)
        
        # First check for a direct hit
        for span in self.spans:
            if span["rect"].contains(pdf_point):
                return span
        
        # If no direct hit, check for a near miss
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

    # NEW: Handles the hover event
    def on_page_hovered(self, position):
        span_under_cursor = self._find_span_at_position(position)
        # Only update if the hovered span has changed to avoid constant redrawing
        if self.hovered_span != span_under_cursor:
            self.hovered_span = span_under_cursor
            self.highlight_selection()

    # MODIFIED: The click handler is now much simpler
    def on_page_clicked(self, position):
        # The hovered span becomes the selected span
        self.selected_span = self.hovered_span
        self.highlight_selection()

    # MODIFIED: Now draws two different highlights
    def highlight_selection(self):
        if self.current_pixmap is None:
            return
        
        temp_pixmap = self.current_pixmap.copy()
        painter = QPainter(temp_pixmap)

        # Draw hover highlight (subtle grey)
        if self.hovered_span:
            span_rect = self.hovered_span["rect"]
            highlight_rect = QRectF(
                span_rect.x0 * self.scale_factor, span_rect.y0 * self.scale_factor,
                span_rect.width * self.scale_factor, span_rect.height * self.scale_factor
            )
            hover_color = QColor(150, 150, 150, 80) # Light grey, semi-transparent
            painter.fillRect(highlight_rect, hover_color)

        # Draw selection highlight (prominent blue) on top
        if self.selected_span:
            span_rect = self.selected_span["rect"]
            highlight_rect = QRectF(
                span_rect.x0 * self.scale_factor, span_rect.y0 * self.scale_factor,
                span_rect.width * self.scale_factor, span_rect.height * self.scale_factor
            )
            select_color = QColor(0, 120, 215, 100) # Blue, semi-transparent
            painter.fillRect(highlight_rect, select_color)

        painter.end()
        self.image_label.setPixmap(temp_pixmap)