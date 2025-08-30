import sys
from PySide6.QtWidgets import QApplication
from main_window import PDFEditor

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PDFEditor()
    window.show()
    sys.exit(app.exec())