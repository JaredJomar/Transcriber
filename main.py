import sys
import os

# Set up DLL paths for PyInstaller frozen app BEFORE any imports
if getattr(sys, 'frozen', False) and sys.platform == 'win32':
    # Running as PyInstaller bundle
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    torch_lib = os.path.join(base_path, 'torch', 'lib')
    
    # Add torch lib to DLL search paths
    if os.path.exists(torch_lib):
        if hasattr(os, 'add_dll_directory'):
            try:
                os.add_dll_directory(torch_lib)
            except Exception:
                pass
        os.environ['PATH'] = torch_lib + os.pathsep + os.environ.get('PATH', '')

from PyQt6.QtWidgets import QApplication

from app.window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
