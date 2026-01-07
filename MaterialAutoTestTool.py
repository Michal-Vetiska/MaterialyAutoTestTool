import os
import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton, QMessageBox, QSizePolicy, QLineEdit, QFrame, QSlider, QScrollArea, QDialog, QTextEdit, QPushButton, QFileDialog, QProgressBar
)
from PyQt5.QtGui import QFont, QIcon, QMovie
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import subprocess
import re

class TestRunnerThread(QThread):
    line_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int)  # current, total

    def run(self):
        self.result = ''
        try:
            process = subprocess.Popen(['python3', 'run_test.py'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            if process.stdout is not None:
                for line in process.stdout:
                    self.result += line
                    self.line_signal.emit(line)
                    # Parsuj progress zprávy (formát: PROGRESS: current/total)
                    if line.startswith('PROGRESS:'):
                        try:
                            parts = line.split('PROGRESS:')[1].strip().split('/')
                            if len(parts) == 2:
                                current = int(parts[0].strip())
                                total = int(parts[1].strip())
                                self.progress_signal.emit(current, total)
                        except (ValueError, IndexError):
                            pass
            process.wait()
        except Exception as e:
            self.result += f'Chyba při spouštění: {e}\n'
            self.line_signal.emit(f'Chyba při spouštění: {e}\n')
        self.finished_signal.emit(self.result)

class LoadingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        # self.setWindowFlags(Qt.Tool)
        self.setStyleSheet('background: rgba(255,255,255,0.75);')
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spinner = QLabel()
        self.spinner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Použijeme GIF spinner (můžeš nahradit vlastním spinnerem)
        spinner_gif = QMovie(self.resource_path('spinner.gif'))
        self.spinner.setMovie(spinner_gif)
        spinner_gif.start()
        layout.addWidget(self.spinner)
        self.label = QLabel('Probíhá testování…')
        self.label.setFont(QFont('Segoe UI', 18, QFont.Bold))
        self.label.setStyleSheet('color: #1976d2; padding: 12px;')
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #1976d2;
                border-radius: 8px;
                text-align: center;
                background-color: #e3f2fd;
                height: 30px;
                width: 400px;
            }
            QProgressBar::chunk {
                background-color: #1976d2;
                border-radius: 6px;
            }
        """)
        self.progress_bar.setFormat('%p%')
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        
        # Progress text
        self.progress_label = QLabel('')
        self.progress_label.setFont(QFont('Segoe UI', 14))
        self.progress_label.setStyleSheet('color: #1976d2; padding: 8px;')
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_label.hide()
        layout.addWidget(self.progress_label)
        
        self.setLayout(layout)
        
    def update_progress(self, current, total):
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar.setMaximum(100)
            self.progress_bar.setValue(percentage)
            self.progress_bar.show()
            self.progress_label.setText(f'Otázka {current} z {total}')
            self.progress_label.show()
        else:
            self.progress_bar.hide()
            self.progress_label.hide()

    def resource_path(self, relative):
        # Umožní použít spinner.gif i po zabalení aplikace
        if getattr(sys, '_MEIPASS', None) is not None:
            return os.path.join(getattr(sys, '_MEIPASS'), relative)
        return os.path.join(os.path.abspath('.'), relative)

class MaterialAutoTestToolApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Material Auto Test Tool')
        self.setWindowIcon(QIcon.fromTheme('applications-system'))
        self.setFixedSize(950, 950)
        self.setStyleSheet('background-color: #f4f7fb;')
        self.init_ui()

    def init_ui(self):
        font_label = QFont('Arial', 12)
        font_text = QFont('Menlo', 11)
        font_button = QFont('Arial', 13, QFont.Bold)
        font_summary = QFont('Arial', 15, QFont.Bold)

        # Hlavní scrollovací oblast
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        content = QWidget()
        main_layout = QVBoxLayout(content)
        main_layout.setSpacing(18)
        main_layout.setContentsMargins(30, 20, 30, 20)

        # How to tlačítko (README)
        howto_btn = QPushButton('How to')
        howto_btn.setFont(font_button)
        howto_btn.setStyleSheet('border-radius: 10px; background: #ffe0b2; padding: 8px 18px;')
        howto_btn.clicked.connect(self.open_readme)
        main_layout.addWidget(howto_btn)

        # Endpoint zadání
        endpoint_layout = QHBoxLayout()
        endpoint_label = QLabel('Endpoint chatbota:')
        endpoint_label.setFont(font_label)
        endpoint_layout.addWidget(endpoint_label)
        self.endpoint_input = QLineEdit()
        self.endpoint_input.setFont(font_text)
        self.endpoint_input.setPlaceholderText('např. http://127.0.0.1:1234')
        self.endpoint_input.setText(self.load_endpoint())
        self.endpoint_input.setFixedWidth(350)
        endpoint_layout.addWidget(self.endpoint_input)
        save_endpoint_btn = QPushButton('Uložit endpoint')
        save_endpoint_btn.setFont(font_button)
        save_endpoint_btn.setStyleSheet('border-radius: 10px; background: #e0eaff; padding: 8px 18px;')
        save_endpoint_btn.clicked.connect(self.save_endpoint)
        endpoint_layout.addWidget(save_endpoint_btn)
        endpoint_layout.addStretch()
        main_layout.addLayout(endpoint_layout)

        # Context1
        label1 = QLabel('Vlož obsah context1.txt:')
        label1.setFont(font_label)
        main_layout.addWidget(label1)
        self.context1_text = QTextEdit()
        self.context1_text.setFont(font_text)
        self.context1_text.setPlaceholderText('Sem vlož materiál...')
        self.context1_text.setStyleSheet('border-radius: 12px; background: #fff; padding: 8px;')
        self.context1_text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        modern_scrollbar = """
QScrollBar:vertical {
    border: none;
    background: #e0eaff;
    width: 14px;
    margin: 0px 0px 0px 0px;
    border-radius: 7px;
}
QScrollBar::handle:vertical {
    background: #4f8cff;
    min-height: 30px;
    border-radius: 7px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}
"""
        self.context1_text.setStyleSheet(self.context1_text.styleSheet() + modern_scrollbar)
        main_layout.addWidget(self.context1_text)
        # Tlačítka pro vložení materiálu
        buttons_layout = QHBoxLayout()
        paste1_btn = QPushButton('Vložit ze schránky')
        paste1_btn.setFont(font_button)
        paste1_btn.setStyleSheet('border-radius: 10px; background: #e0eaff; padding: 8px 18px;')
        paste1_btn.clicked.connect(lambda: self.paste_from_clipboard(self.context1_text))
        buttons_layout.addWidget(paste1_btn)
        load_pdf_btn = QPushButton('Nahrát PDF')
        load_pdf_btn.setFont(font_button)
        load_pdf_btn.setStyleSheet('border-radius: 10px; background: #e0eaff; padding: 8px 18px;')
        load_pdf_btn.clicked.connect(lambda: self.load_pdf(self.context1_text))
        buttons_layout.addWidget(load_pdf_btn)
        buttons_layout.addStretch()
        main_layout.addLayout(buttons_layout)

        # YAML
        label2 = QLabel('Vlož YAML (testovací scénáře):')
        label2.setFont(font_label)
        main_layout.addWidget(label2)
        self.yaml_text = QTextEdit()
        self.yaml_text.setFont(font_text)
        self.yaml_text.setPlaceholderText('Sem vlož YAML scénáře...')
        self.yaml_text.setStyleSheet('border-radius: 12px; background: #fff; padding: 8px;')
        self.yaml_text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        modern_scrollbar = """
QScrollBar:vertical {
    border: none;
    background: #e0eaff;
    width: 14px;
    margin: 0px 0px 0px 0px;
    border-radius: 7px;
}
QScrollBar::handle:vertical {
    background: #4f8cff;
    min-height: 30px;
    border-radius: 7px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}
"""
        self.yaml_text.setStyleSheet(self.yaml_text.styleSheet() + modern_scrollbar)
        main_layout.addWidget(self.yaml_text)
        paste2_btn = QPushButton('Vložit ze schránky')
        paste2_btn.setFont(font_button)
        paste2_btn.setStyleSheet('border-radius: 10px; background: #e0eaff; padding: 8px 18px;')
        paste2_btn.clicked.connect(lambda: self.paste_from_clipboard(self.yaml_text))
        main_layout.addWidget(paste2_btn)

        # Spustit test
        self.run_button = QPushButton('Spustit test')
        self.run_button.setFont(QFont('Arial', 16, QFont.Bold))
        self.run_button.setStyleSheet('border-radius: 16px; background: #4f8cff; color: #fff; padding: 14px 0;')
        self.run_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.run_button.clicked.connect(self.save_and_run_test)
        main_layout.addWidget(self.run_button)

        # Souhrn výsledku
        self.summary_label = QLabel('')
        self.summary_label.setFont(font_summary)
        self.summary_label.setStyleSheet('color: #2e7d32; padding: 8px;')
        main_layout.addWidget(self.summary_label)

        # Výsledky testu (bez scrollbaru, roste s obsahem)
        self.result_label = QLabel('Výsledky testu:')
        self.result_label.setFont(font_label)
        main_layout.addWidget(self.result_label)
        self.result_output = QTextEdit()
        self.result_output.setFont(QFont('Menlo', 12))
        self.result_output.setReadOnly(True)
        self.result_output.setStyleSheet('border-radius: 12px; background: #f0f4fa; padding: 8px;')
        self.result_output.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.result_output.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.result_output.setMaximumHeight(100000)  # prakticky neomezené
        main_layout.addWidget(self.result_output)

        scroll.setWidget(content)
        scroll.setStyleSheet(modern_scrollbar)
        layout = QVBoxLayout(self)
        layout.addWidget(scroll)
        self.setLayout(layout)
        self.test_thread = None
        self.loading_overlay = LoadingOverlay(self)
        self.loading_overlay.hide()

    def paste_from_clipboard(self, widget):
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            widget.setPlainText(clipboard.text())

    def load_pdf(self, widget):
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, 'Vyber PDF soubor', '', 'PDF Files (*.pdf)'
            )
            if file_path:
                try:
                    import PyPDF2
                    text_content = ''
                    with open(file_path, 'rb') as pdf_file:
                        pdf_reader = PyPDF2.PdfReader(pdf_file)
                        for page in pdf_reader.pages:
                            text_content += page.extract_text() + '\n'
                    widget.setPlainText(text_content)
                    QMessageBox.information(self, 'Úspěch', f'PDF soubor byl načten. Extrahováno {len(pdf_reader.pages)} stránek.')
                except ImportError:
                    QMessageBox.warning(
                        self, 'Chybějící knihovna',
                        'Pro načtení PDF je potřeba nainstalovat PyPDF2.\n\n'
                        'Spusť: pip3 install PyPDF2'
                    )
                except Exception as e:
                    QMessageBox.critical(self, 'Chyba', f'Nepodařilo se načíst PDF: {e}')
        except Exception as e:
            QMessageBox.critical(self, 'Chyba', f'Chyba při výběru souboru: {e}')

    def save_endpoint(self):
        endpoint = self.endpoint_input.text().strip()
        if not endpoint:
            QMessageBox.warning(self, 'Chyba', 'Endpoint nesmí být prázdný!')
            return
        try:
            with open('endpoint.txt', 'w', encoding='utf-8') as f:
                f.write(endpoint)
            QMessageBox.information(self, 'Uloženo', 'Endpoint byl uložen.')
        except Exception as e:
            QMessageBox.critical(self, 'Chyba', f'Nepodařilo se uložit endpoint: {e}')

    def load_endpoint(self):
        try:
            with open('endpoint.txt', 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception:
            return 'http://127.0.0.1:1234'

    def show_loading(self):
        self.loading_overlay.setGeometry(0, 0, self.width(), self.height())
        self.loading_overlay.show()
        self.loading_overlay.raise_()
        self.repaint()

    def hide_loading(self):
        self.loading_overlay.hide()

    def save_and_run_test(self):
        context1 = self.context1_text.toPlainText().strip()
        yaml_content = self.yaml_text.toPlainText().strip()
        endpoint = self.endpoint_input.text().strip()
        if not context1 or not yaml_content or not endpoint:
            QMessageBox.critical(self, 'Chyba', 'Všechna pole musí být vyplněna!')
            return
        try:
            with open('context1.txt', 'w', encoding='utf-8') as f1:
                f1.write(context1)
            with open('test_core_messenger_and_inbox.yaml', 'w', encoding='utf-8') as f2:
                f2.write(yaml_content)
            with open('endpoint.txt', 'w', encoding='utf-8') as f3:
                f3.write(endpoint)
            self.result_output.clear()
            self.summary_label.setText('')
            self.run_button.setEnabled(False)
            self.show_loading()
            self.test_thread = TestRunnerThread()
            self.test_thread.line_signal.connect(self.append_result)
            self.test_thread.finished_signal.connect(self.on_test_finished)
            self.test_thread.progress_signal.connect(self.loading_overlay.update_progress)
            self.test_thread.start()
        except Exception as e:
            self.result_output.setPlainText(f'Chyba při ukládání: {e}')

    def update_result_output_height(self):
        doc = self.result_output.document()
        if doc is not None:
            doc_height = doc.size().height()
            self.result_output.setFixedHeight(int(doc_height * 1.35) + 20)
        else:
            self.result_output.setFixedHeight(100)

    def show_result(self, text):
        self.result_output.setPlainText(text)
        self.update_result_output_height()
        self.update_summary(text)

    def append_result(self, text):
        self.result_output.moveCursor(self.result_output.textCursor().End)
        self.result_output.insertPlainText(text)
        self.result_output.moveCursor(self.result_output.textCursor().End)
        self.update_result_output_height()
        self.update_summary(self.result_output.toPlainText())

    def on_test_finished(self, result):
        self.hide_loading()
        self.run_button.setEnabled(True)
        self.update_summary(result)
        QMessageBox.information(self, 'Výsledek testu', 'Test byl dokončen! Výsledek najdeš v poli níže.')

    def update_summary(self, text):
        summary_pattern = r'={10,}\s*Celkem otázek: (\d+)\s*✅ Passed: (\d+)\s*❌ Failed: (\d+)\s*Úspěšnost: ([\d\.]+)%'
        match = re.search(summary_pattern, text)
        if match:
            total, passed, failed, success = match.groups()
            summary = f"Souhrn testu:\nCelkem otázek: {total}\n✅ Passed: {passed}\n❌ Failed: {failed}\nÚspěšnost: {success}%"
            if float(success) > 80.0:
                summary += "\n\nMateriál je Chatbot Ready 👍"
            self.summary_label.setText(summary)
        else:
            self.summary_label.setText('')

    def open_readme(self):
        readme_path = os.path.abspath('README.md')
        if not os.path.exists(readme_path):
            QMessageBox.warning(self, 'README nenalezen', 'README.md nebyl nalezen v aktuální složce.')
            return
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
        dlg = QDialog(self)
        dlg.setWindowTitle('Návod (README)')
        dlg.setMinimumSize(700, 600)
        layout = QVBoxLayout(dlg)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(content)
        layout.addWidget(text)
        close_btn = QPushButton('Zavřít')
        close_btn.clicked.connect(dlg.accept)
        layout.addWidget(close_btn)
        dlg.exec_()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MaterialAutoTestToolApp()
    window.show()
    sys.exit(app.exec_()) 