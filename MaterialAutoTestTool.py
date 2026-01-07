import os
import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton, QMessageBox, QSizePolicy, QLineEdit, QFrame, QSlider, QScrollArea, QDialog, QTextEdit, QPushButton, QFileDialog, QProgressBar
)
from PyQt5.QtGui import QFont, QIcon, QMovie
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
import subprocess
import re

class TestRunnerThread(QThread):
    line_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int)  # current, total
    progress_start_signal = pyqtSignal(int, int)  # current, total - začátek otázky

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
                    # Parsuj start progress zprávy (formát: PROGRESS_START: current/total)
                    elif line.startswith('PROGRESS_START:'):
                        try:
                            parts = line.split('PROGRESS_START:')[1].strip().split('/')
                            if len(parts) == 2:
                                current = int(parts[0].strip())
                                total = int(parts[1].strip())
                                self.progress_start_signal.emit(current, total)
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
        # Tmavé pozadí s vysokou opacity pro efekt ztmavení
        self.setStyleSheet('background: rgba(0, 0, 0, 0.6);')
        
        # Hlavní layout
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Světlý kontejner pro obsah (modal design)
        content_widget = QWidget()
        content_widget.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border-radius: 20px;
                padding: 40px 50px;
                min-width: 450px;
            }
        """)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.setSpacing(24)
        
        self.spinner = QLabel()
        self.spinner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Použijeme GIF spinner (můžeš nahradit vlastním spinnerem)
        spinner_gif = QMovie(self.resource_path('spinner.gif'))
        self.spinner.setMovie(spinner_gif)
        spinner_gif.start()
        content_layout.addWidget(self.spinner)
        
        self.label = QLabel('Probíhá testování…')
        self.label.setFont(QFont('.SF NS Text', 18, QFont.Weight.Medium))
        self.label.setStyleSheet('color: #1d1d1f; padding: 0px;')
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self.label)
        
        # Progress bar
        progress_container = QWidget()
        progress_layout = QVBoxLayout(progress_container)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(8)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 6px;
                text-align: center;
                background-color: #e5e5e7;
                height: 8px;
                width: 400px;
                color: transparent;
            }
            QProgressBar::chunk {
                background-color: #007AFF;
                border-radius: 6px;
            }
        """)
        self.progress_bar.setFormat('')
        self.progress_bar.show()
        progress_layout.addWidget(self.progress_bar)
        
        # Text s počtem otázek pod progress barem (malý nevýrazný font)
        self.questions_count_label = QLabel('0/0')
        self.questions_count_label.setFont(QFont('.SF NS Text', 11))
        self.questions_count_label.setStyleSheet('color: #86868b; padding: 0px;')
        self.questions_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.questions_count_label.show()
        progress_layout.addWidget(self.questions_count_label)
        
        content_layout.addWidget(progress_container)
        
        main_layout.addWidget(content_widget)
        self.setLayout(main_layout)
        
        # Timer pro smooth progress animaci
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self._animate_progress)
        self.current_progress = 0.0
        self.target_progress = 0.0
        self.start_progress = 0.0
        self.total_tests = 1
        
    def _animate_progress(self):
        # Plynulá animace progressu
        if self.current_progress < self.target_progress:
            # Zvyšujeme progress postupně
            step = (self.target_progress - self.start_progress) / 100.0
            self.current_progress = min(self.current_progress + step, self.target_progress)
            percentage = int(self.current_progress)
            self.progress_bar.setValue(percentage)
            
            # Aktualizuj počet otázek pod progress barem
            if self.total_tests > 0:
                current_test = max(1, int((self.current_progress / 100.0) * self.total_tests))
                self.questions_count_label.setText(f'{current_test}/{self.total_tests}')
            
            if self.current_progress >= self.target_progress:
                self.progress_timer.stop()
        else:
            self.progress_timer.stop()
    
    def start_progress_animation(self, current, total):
        """Začne animaci progressu pro aktuální otázku"""
        if total > 0:
            self.total_tests = total
            # Aktualizuj počet otázek
            self.questions_count_label.setText(f'{current}/{total}')
            
            # Spočítáme start a target progress
            prev_progress = ((current - 1) / total) * 100.0 if current > 1 else 0.0
            target_progress = (current / total) * 100.0
            
            self.start_progress = self.current_progress if self.current_progress > prev_progress else prev_progress
            self.target_progress = target_progress
            
            # Spustíme timer pro smooth animaci (aktualizace každých 50ms)
            if not self.progress_timer.isActive():
                self.progress_timer.start(50)
    
    def update_progress(self, current, total):
        """Nastaví finální progress po dokončení otázky"""
        if total > 0:
            self.total_tests = total
            # Zastavíme animaci
            self.progress_timer.stop()
            
            # Nastavíme finální progress
            percentage = int((current / total) * 100)
            self.current_progress = percentage
            self.target_progress = percentage
            self.progress_bar.setValue(percentage)
            self.progress_bar.show()
            
            # Aktualizuj počet otázek
            self.questions_count_label.setText(f'{current}/{total}')
            self.questions_count_label.show()
        else:
            # I když není total, zobraz progress bar s 0%
            self.progress_timer.stop()
            self.progress_bar.setValue(0)
            self.current_progress = 0.0
            self.target_progress = 0.0
            self.progress_bar.show()
            self.questions_count_label.setText('0/0')
            self.questions_count_label.show()

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
        self.setStyleSheet('background-color: #f5f5f7;')
        self.init_ui()

    def init_ui(self):
        # macOS systémové fonty
        font_label = QFont('.SF NS Text', 13)
        font_text = QFont('SF Mono', 11)
        font_button = QFont('.SF NS Text', 13, QFont.Weight.Medium)
        font_summary = QFont('.SF NS Display', 16, QFont.DemiBold)

        # Hlavní scrollovací oblast
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        content = QWidget()
        main_layout = QVBoxLayout(content)
        main_layout.setSpacing(24)
        main_layout.setContentsMargins(40, 30, 40, 30)

        # How to tlačítko (README)
        howto_btn = QPushButton('How to')
        howto_btn.setFont(font_button)
        howto_btn.setStyleSheet("""
            QPushButton {
                border-radius: 8px;
                background-color: #ffffff;
                color: #1d1d1f;
                padding: 10px 20px;
                border: 1px solid #d2d2d7;
            }
            QPushButton:hover {
                background-color: #f5f5f7;
            }
            QPushButton:pressed {
                background-color: #e5e5e7;
            }
        """)
        howto_btn.clicked.connect(self.open_readme)
        main_layout.addWidget(howto_btn)

        # Endpoint zadání
        endpoint_layout = QHBoxLayout()
        endpoint_layout.setSpacing(12)
        endpoint_label = QLabel('Endpoint chatbota:')
        endpoint_label.setFont(font_label)
        endpoint_label.setStyleSheet('color: #1d1d1f;')
        endpoint_layout.addWidget(endpoint_label)
        self.endpoint_input = QLineEdit()
        self.endpoint_input.setFont(font_text)
        self.endpoint_input.setPlaceholderText('např. http://127.0.0.1:1234')
        self.endpoint_input.setText(self.load_endpoint())
        self.endpoint_input.setFixedWidth(350)
        self.endpoint_input.setStyleSheet("""
            QLineEdit {
                border-radius: 8px;
                background-color: #ffffff;
                border: 1px solid #d2d2d7;
                padding: 10px 14px;
                color: #1d1d1f;
            }
            QLineEdit:focus {
                border: 2px solid #007AFF;
                padding: 9px 13px;
            }
        """)
        endpoint_layout.addWidget(self.endpoint_input)
        save_endpoint_btn = QPushButton('Uložit endpoint')
        save_endpoint_btn.setFont(font_button)
        save_endpoint_btn.setStyleSheet("""
            QPushButton {
                border-radius: 8px;
                background-color: #007AFF;
                color: #ffffff;
                padding: 10px 20px;
                border: none;
            }
            QPushButton:hover {
                background-color: #0051D5;
            }
            QPushButton:pressed {
                background-color: #0040AA;
            }
        """)
        save_endpoint_btn.clicked.connect(self.save_endpoint)
        endpoint_layout.addWidget(save_endpoint_btn)
        endpoint_layout.addStretch()
        main_layout.addLayout(endpoint_layout)

        # Context1
        label1 = QLabel('Vlož obsah context1.txt:')
        label1.setFont(font_label)
        label1.setStyleSheet('color: #1d1d1f; margin-bottom: 8px;')
        main_layout.addWidget(label1)
        self.context1_text = QTextEdit()
        self.context1_text.setFont(font_text)
        self.context1_text.setPlaceholderText('Sem vlož materiál...')
        self.context1_text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        modern_scrollbar = """
QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 11px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #c7c7cc;
    min-height: 30px;
    border-radius: 5px;
    margin: 2px;
}
QScrollBar::handle:vertical:hover {
    background: #aeaeb2;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}
"""
        self.context1_text.setStyleSheet(f"""
            QTextEdit {{
                border-radius: 10px;
                background-color: #ffffff;
                border: 1px solid #d2d2d7;
                padding: 12px;
                color: #1d1d1f;
            }}
            QTextEdit:focus {{
                border: 2px solid #007AFF;
                padding: 11px;
            }}
            {modern_scrollbar}
        """)
        main_layout.addWidget(self.context1_text)
        # Tlačítka pro vložení materiálu
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        paste1_btn = QPushButton('Vložit ze schránky')
        paste1_btn.setFont(font_button)
        paste1_btn.setStyleSheet("""
            QPushButton {
                border-radius: 8px;
                background-color: #ffffff;
                color: #1d1d1f;
                padding: 10px 20px;
                border: 1px solid #d2d2d7;
            }
            QPushButton:hover {
                background-color: #f5f5f7;
            }
            QPushButton:pressed {
                background-color: #e5e5e7;
            }
        """)
        paste1_btn.clicked.connect(lambda: self.paste_from_clipboard(self.context1_text))
        buttons_layout.addWidget(paste1_btn)
        load_pdf_btn = QPushButton('Nahrát PDF')
        load_pdf_btn.setFont(font_button)
        load_pdf_btn.setStyleSheet("""
            QPushButton {
                border-radius: 8px;
                background-color: #ffffff;
                color: #1d1d1f;
                padding: 10px 20px;
                border: 1px solid #d2d2d7;
            }
            QPushButton:hover {
                background-color: #f5f5f7;
            }
            QPushButton:pressed {
                background-color: #e5e5e7;
            }
        """)
        load_pdf_btn.clicked.connect(lambda: self.load_pdf(self.context1_text))
        buttons_layout.addWidget(load_pdf_btn)
        buttons_layout.addStretch()
        main_layout.addLayout(buttons_layout)

        # YAML
        label2 = QLabel('Vlož YAML (testovací scénáře):')
        label2.setFont(font_label)
        label2.setStyleSheet('color: #1d1d1f; margin-bottom: 8px;')
        main_layout.addWidget(label2)
        self.yaml_text = QTextEdit()
        self.yaml_text.setFont(font_text)
        self.yaml_text.setPlaceholderText('Sem vlož YAML scénáře...')
        self.yaml_text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.yaml_text.setStyleSheet(f"""
            QTextEdit {{
                border-radius: 10px;
                background-color: #ffffff;
                border: 1px solid #d2d2d7;
                padding: 12px;
                color: #1d1d1f;
            }}
            QTextEdit:focus {{
                border: 2px solid #007AFF;
                padding: 11px;
            }}
            {modern_scrollbar}
        """)
        main_layout.addWidget(self.yaml_text)
        paste2_btn = QPushButton('Vložit ze schránky')
        paste2_btn.setFont(font_button)
        paste2_btn.setStyleSheet("""
            QPushButton {
                border-radius: 8px;
                background-color: #ffffff;
                color: #1d1d1f;
                padding: 10px 20px;
                border: 1px solid #d2d2d7;
            }
            QPushButton:hover {
                background-color: #f5f5f7;
            }
            QPushButton:pressed {
                background-color: #e5e5e7;
            }
        """)
        paste2_btn.clicked.connect(lambda: self.paste_from_clipboard(self.yaml_text))
        main_layout.addWidget(paste2_btn)

        # Spustit test
        self.run_button = QPushButton('Spustit test')
        self.run_button.setFont(QFont('.SF NS Display', 15, QFont.DemiBold))
        self.run_button.setStyleSheet("""
            QPushButton {
                border-radius: 10px;
                background-color: #007AFF;
                color: #ffffff;
                padding: 14px 0;
                border: none;
            }
            QPushButton:hover {
                background-color: #0051D5;
            }
            QPushButton:pressed {
                background-color: #0040AA;
            }
            QPushButton:disabled {
                background-color: #c7c7cc;
                color: #8e8e93;
            }
        """)
        self.run_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.run_button.clicked.connect(self.save_and_run_test)
        main_layout.addWidget(self.run_button)

        # Souhrn výsledku
        self.summary_label = QLabel('')
        self.summary_label.setFont(font_summary)
        self.summary_label.setStyleSheet('color: #1d1d1f; padding: 12px; background-color: #ffffff; border-radius: 10px; border: 1px solid #d2d2d7;')
        main_layout.addWidget(self.summary_label)

        # Výsledky testu (bez scrollbaru, roste s obsahem)
        self.result_label = QLabel('Výsledky testu:')
        self.result_label.setFont(font_label)
        self.result_label.setStyleSheet('color: #1d1d1f; margin-bottom: 8px;')
        main_layout.addWidget(self.result_label)
        self.result_output = QTextEdit()
        self.result_output.setFont(QFont('SF Mono', 11))
        self.result_output.setReadOnly(True)
        self.result_output.setStyleSheet("""
            QTextEdit {
                border-radius: 10px;
                background-color: #ffffff;
                border: 1px solid #d2d2d7;
                padding: 12px;
                color: #1d1d1f;
            }
        """)
        self.result_output.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.result_output.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.result_output.setMaximumHeight(100000)  # prakticky neomezené
        main_layout.addWidget(self.result_output)

        scroll.setWidget(content)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 11px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #c7c7cc;
                min-height: 30px;
                border-radius: 5px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background: #aeaeb2;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
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
        # Reset progress na 0%
        self.loading_overlay.progress_bar.setValue(0)
        self.loading_overlay.questions_count_label.setText('0/0')
        self.loading_overlay.current_progress = 0.0
        self.loading_overlay.target_progress = 0.0
        self.loading_overlay.start_progress = 0.0
        self.loading_overlay.progress_timer.stop()
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
            self.test_thread.progress_start_signal.connect(self.loading_overlay.start_progress_animation)
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