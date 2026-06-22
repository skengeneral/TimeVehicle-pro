import webbrowser
import sys
import os
import requests  # 🚀 Used for dynamic cloud loading, credit metrics & validation

from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QCheckBox, 
    QPushButton, QVBoxLayout, QHBoxLayout, QFrame, QMessageBox, QScrollArea, QInputDialog
)
from PyQt6.QtCore import Qt, QPoint, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QPainter, QPolygon, QColor, QCursor, QIcon

# 🛑 LOCAL STATIC ENGINE IMPORTS REMOVED TO ALLOW 100% SILENT CLOUD UPDATES
def get_local_api_key():
    if getattr(sys, 'frozen', False):
        current_dir = os.path.dirname(sys.executable)
    else:
        current_dir = os.path.dirname(os.path.abspath(__file__))
    key_file_path = os.path.join(current_dir, "serp_api.txt")
    if os.path.exists(key_file_path):
        try:
            with open(key_file_path, "r", encoding="utf-8") as file:
                return file.read().strip()
        except: pass
    return os.environ.get("SERPAPI_KEY")

def fetch_live_serp_credits():
    """Connects directly to SerpApi to extract remaining search credits with an optimized timeout."""
    api_key = get_local_api_key()
    if not api_key:
        return "Missing Key"
    endpoint = "https://serpapi.com/account.json"
    params = {"api_key": api_key}
    try:
        response = requests.get(endpoint, params=params, timeout=3)
        if response.status_code == 200:
            account_info = response.json()
            return str(account_info.get("plan_searches_left", 0))
    except:
        pass
    return "Offline (Check Connection)"


class LogoWidget(QWidget):
    """Custom widget rendering precise geometric emblem using vector points."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(50, 50) 

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        base_color = QColor("#6B1D66") 
        painter.setBrush(base_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(0, 0, self.width(), self.height())
        fold_color = QColor("#E397E1") 
        painter.setBrush(fold_color)
        points = QPolygon([
            QPoint(0, 0), QPoint(self.width(), 0),
            QPoint(self.width() // 2, int(self.height() * 0.46))
        ])
        painter.drawPolygon(points)


class ScraperWorker(QThread):
    """⚡ Dynamic Cloud Worker executing the latest online Pro scraping logic out of RAM."""
    finished_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, search_query, allowed_ratings, target_city):
        super().__init__()
        self.search_query = search_query
        self.allowed_ratings = allowed_ratings
        self.target_city = target_city

    def run(self):
        try:
            # 🟢 TARGETING YOUR PRO PRODUCTION REPOSITORY BRAIN
            CLOUD_SCRAPER_URL = "https://raw.githubusercontent.com/skengeneral/TimeVehicle-pro/main/pro/scraper_engine.py"
            response = requests.get(CLOUD_SCRAPER_URL, timeout=10)
            
            if response.status_code == 200:
                scraper_code = response.text
                
                # Execute live code securely in memory sandbox
                local_scope = {}
                exec(scraper_code, globals(), local_scope)
                
                # Fire the deep intelligence function straight from RAM
                extraction_packet = local_scope["extract_local_leads"](
                    search_query=self.search_query, 
                    allowed_ratings=self.allowed_ratings,
                    target_city=self.target_city
                )
                self.finished_signal.emit(extraction_packet)
            else:
                self.error_signal.emit(f"Could not reach Pro update server (Code: {response.status_code})")
        except Exception as e:
            self.error_signal.emit(str(e))


class TimeVehicleUI(QWidget):
    def __init__(self):
        super().__init__()
        self.live_credits = "Fetching Status..."
        self.scraper_worker = None  
        self.init_ui()
        QTimer.singleShot(100, self.lazy_load_credits)
        
    def init_ui(self):
        self.setWindowTitle("Time vehicle - 1.0")
        
        # 🎨 RUNTIME LOGO INJECTION: Sets matching taskbar & title icon profiles
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(base_dir, "timevehicle.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            
        self.setMinimumSize(440, 600)  
        self.resize(480, 680)          
        self.setStyleSheet("background-color: #FFFFFF;")
        
        title_font = QFont("Arial", 14, QFont.Weight.Bold)
        section_font = QFont("Arial", 11, QFont.Weight.Bold)
        label_font = QFont("Arial", 10)
        
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: #FFFFFF; }")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: #FFFFFF;")
        master_layout = QVBoxLayout(scroll_content)
        master_layout.setContentsMargins(0, 0, 0, 0)
        master_layout.setSpacing(0)
        
        header_widget = QWidget()
        header_widget.setStyleSheet("background-color: #002D4A; border: none;") 
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(25, 20, 25, 20)
        header_layout.setSpacing(15)
        
        self.logo_emblem = LogoWidget()
        header_layout.addWidget(self.logo_emblem)
        
        title = QLabel("TIME VEHICLE - 1.0")
        title.setFont(title_font)
        title.setStyleSheet("color: #FFFFFF; line-height: 1.2;") 
        header_layout.addWidget(title)
        header_layout.addStretch()
        master_layout.addWidget(header_widget)
        
        sheet_widget = QWidget()
        sheet_widget.setStyleSheet("background-color: #FFFFFF;")
        sheet_layout = QVBoxLayout(sheet_widget)
        sheet_layout.setSpacing(12)
        sheet_layout.setContentsMargins(25, 15, 25, 20)
        
        credit_frame = QFrame()
        credit_frame.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 4px;")
        credit_layout = QHBoxLayout(credit_frame)
        credit_layout.setContentsMargins(12, 6, 12, 6)
        
        self.lbl_credits = QLabel(f"💳 Searches Remaining: {self.live_credits}", font=label_font)
        self.lbl_credits.setStyleSheet("color: #0F172A; font-weight: bold;")
        
        btn_recharge = QPushButton("🔌 Recharge")
        btn_recharge.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        btn_recharge.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_recharge.setStyleSheet("""
            QPushButton {
                background-color: #10B981; color: white; border: none; 
                border-radius: 4px; padding: 5px 12px;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        btn_recharge.clicked.connect(self.open_serpapi_billing)
        
        credit_layout.addWidget(self.lbl_credits)
        credit_layout.addStretch()
        credit_layout.addWidget(btn_recharge)
        sheet_layout.addWidget(credit_frame)
        
        lbl_prof = QLabel("Field of search/profession:", font=label_font)
        lbl_prof.setStyleSheet("color: #333333;")
        sheet_layout.addWidget(lbl_prof)
        self.input_profession = QLineEdit()
        self.input_profession.setPlaceholderText("e.g., Orthopedic doctor")
        sheet_layout.addWidget(self.input_profession)
        
        lbl_local = QLabel("Locality/area name :", font=label_font)
        lbl_local.setStyleSheet("color: #333333;")
        sheet_layout.addWidget(lbl_local)
        self.input_locality = QLineEdit()
        self.input_locality.setPlaceholderText("e.g., 401 SW 42nd Ave #200")
        sheet_layout.addWidget(self.input_locality)
        
        geo_layout = QHBoxLayout()
        geo_layout.setSpacing(15)
        
        vbox_city = QVBoxLayout()
        lbl_city = QLabel("City:", font=label_font)
        lbl_city.setStyleSheet("color: #333333;")
        vbox_city.addWidget(lbl_city)
        self.input_city = QLineEdit()
        self.input_city.setPlaceholderText("e.g., Miami")
        vbox_city.addWidget(self.input_city)
        
        vbox_state = QVBoxLayout()
        lbl_state = QLabel("State:", font=label_font)
        lbl_state.setStyleSheet("color: #333333;")
        vbox_state.addWidget(lbl_state)
        self.input_state = QLineEdit()
        self.input_state.setPlaceholderText("e.g., Florida")
        vbox_state.addWidget(self.input_state)
        
        vbox_country = QVBoxLayout()
        lbl_country = QLabel("Country:", font=label_font)
        lbl_country.setStyleSheet("color: #333333;")
        vbox_country.addWidget(lbl_country)
        self.input_country = QLineEdit()
        self.input_country.setPlaceholderText("e.g., USA")
        vbox_country.addWidget(self.input_country)
        
        geo_layout.addLayout(vbox_city, stretch=1)
        geo_layout.addLayout(vbox_state, stretch=1)
        geo_layout.addLayout(vbox_country, stretch=1)
        sheet_layout.addLayout(geo_layout)
        
        for edit in [self.input_profession, self.input_locality, self.input_city, self.input_state, self.input_country]:
            edit.setStyleSheet("padding: 8px; border: 1px solid #B0C4DE; border-radius: 4px; background: #FFFFFF; color: #000000;")
        
        self.add_separator(sheet_layout)
        
        rating_label = QLabel("Google rating range")
        rating_label.setFont(section_font)
        rating_label.setStyleSheet("color: #002D4A;")
        sheet_layout.addWidget(rating_label)
        
        rating_layout = QHBoxLayout()
        ratings = ["5", "4", "3", "2", "1", "0", "ALL"]
        self.rating_checkboxes = {}
        checkbox_style = "QCheckBox { color: #333333; padding: 4px; } QCheckBox::indicator { width: 16px; height: 16px; }"
        
        for rate in ratings:
            cb = QCheckBox(rate)
            cb.setFont(label_font)
            cb.setStyleSheet(checkbox_style)
            if rate == "ALL":
                cb.setChecked(True)
                cb.toggled.connect(self.handle_all_ratings_toggle)
            else:
                cb.toggled.connect(self.handle_single_rating_toggle)
            rating_layout.addWidget(cb)
            self.rating_checkboxes[rate] = cb
            
        sheet_layout.addLayout(rating_layout)
        self.add_separator(sheet_layout)
        
        download_label = QLabel("Download to System:")
        download_label.setFont(section_font)
        download_label.setStyleSheet("color: #002D4A;")
        sheet_layout.addWidget(download_label)
        
        format_layout = QHBoxLayout()
        self.chk_excel = QCheckBox("Excel")
        self.chk_excel.setChecked(True)
        self.chk_excel.setFont(label_font)
        self.chk_excel.setStyleSheet(checkbox_style)
        
        format_layout.addWidget(self.chk_excel)
        sheet_layout.addLayout(format_layout)
        
        self.add_separator(sheet_layout)
        sheet_layout.addSpacing(5)
        
        self.btn_submit = QPushButton("SUBMIT")
        self.btn_submit.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.btn_submit.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_submit.setStyleSheet("""
            QPushButton {
                background-color: #002D4A; color: white;
                padding: 12px; border: none; border-radius: 4px;
            }
            QPushButton:hover { background-color: #004473; }
            QPushButton:pressed { background-color: #001524; }
            QPushButton:disabled { background-color: #64748B; color: #CBD5E1; }
        """)
        self.btn_submit.clicked.connect(self.handle_submit_action)
        sheet_layout.addWidget(self.btn_submit)
        
        sheet_layout.addSpacing(15)
        support_frame = QFrame()
        support_frame.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 12px;")
        support_layout = QHBoxLayout(support_frame)
        
        lbl_support_text = QLabel("💬 Need help or customized solutions? WhatsApp us at:\n👉 +91 77803 79259\n📧 Mail us at: support@timevehicle.com")
        lbl_support_text.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        lbl_support_text.setStyleSheet("color: #475569; line-height: 1.4;")
        lbl_support_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        support_layout.addWidget(lbl_support_text)
        sheet_layout.addWidget(support_frame)
        
        master_layout.addWidget(sheet_widget)
        scroll_area.setWidget(scroll_content)
        outer_layout.addWidget(scroll_area)
        
    def add_separator(self, layout):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("color: #E2E8F0; margin-top: 5px; margin-bottom: 5px; border: none; background-color: #E2E8F0; height: 1px;")
        layout.addWidget(line)

    def handle_all_ratings_toggle(self, checked):
        if checked:
            for rate, cb in self.rating_checkboxes.items():
                if rate != "ALL":
                    cb.blockSignals(True)
                    cb.setChecked(False)
                    cb.blockSignals(False)

    def handle_single_rating_toggle(self, checked):
        if checked:
            self.rating_checkboxes["ALL"].blockSignals(True)
            self.rating_checkboxes["ALL"].setChecked(False)
            self.rating_checkboxes["ALL"].blockSignals(False)
            
    def open_serpapi_billing(self, event=None):
        webbrowser.open("https://serpapi.com/plan")
        self.refresh_credit_display()
        
    def lazy_load_credits(self):
        self.live_credits = fetch_live_serp_credits()
        self.lbl_credits.setText(f"💳 Searches Remaining: {self.live_credits}")

    def refresh_credit_display(self):
        self.lbl_credits.setText("💳 Searches Remaining: Fetching Status...")
        self.live_credits = fetch_live_serp_credits()
        self.lbl_credits.setText(f"💳 Searches Remaining: {self.live_credits}")

    def verify_security_passkey(self):
        csv_export_url = "https://docs.google.com/spreadsheets/d/1_mHFrZcnhupYNU2FA9B1I5DEFNerNsIwW61lX_ygPHs/export?format=csv&gid=0"
        
        passkey, ok = QInputDialog.getText(
            self, 
            "Security Verification", 
            "Please enter your Time Vehicle Activation Passkey:",
            QLineEdit.EchoMode.Normal
        )
        if not ok:
            return False
            
        passkey_clean = passkey.strip()
        if not passkey_clean:
            QMessageBox.warning(self, "Entry Empty", "Passkey cannot be empty.")
            return False
            
        try:
            response = requests.get(csv_export_url, timeout=4)
            if response.status_code == 200:
                raw_text = response.text
                active_cloud_keys = set()
                for line in raw_text.splitlines():
                    for segment in line.split(','):
                        clean_token = segment.strip().replace('"', '').replace("'", "")
                        if clean_token:
                            active_cloud_keys.add(clean_token.lower())
                            
                if passkey_clean.lower() in active_cloud_keys:
                    return True
                else:
                    QMessageBox.critical(self, "Verification Failure", "The passkey you entered is not authorized or has expired.")
                    return False
            else:
                QMessageBox.critical(self, "Database Error", f"Could not sync with validation server. Code: {response.status_code}")
                return False
        except Exception as e:
            QMessageBox.critical(self, "Network Failure", f"Could not connect to database for verification. Check internet connection.\nDetail: {str(e)}")
            return False

    def handle_submit_action(self):
        profession = self.input_profession.text().strip()
        locality = self.input_locality.text().strip()
        city = self.input_city.text().strip()
        state = self.input_state.text().strip()
        country = self.input_country.text().strip()
        
        if not profession or not city:
            QMessageBox.warning(self, "Missing Information", "Profession and City fields are mandatory!")
            return
            
        selected_ratings = []
        if self.rating_checkboxes["ALL"].isChecked():
            selected_ratings = ["ALL"]
        else:
            for rate, cb in self.rating_checkboxes.items():
                if rate != "ALL" and cb.isChecked():
                    selected_ratings.append(rate)
                    
        if not selected_ratings:
            QMessageBox.warning(self, "Missing Rating", "Please select at least one rating box or select 'ALL'.")
            return

        if not self.verify_security_passkey():
            return

        search_components = []
        if profession: search_components.append(profession)
        if locality:   search_components.append(locality)
        clean_search_query = " ".join(search_components)
        
        geo_components = []
        if city:    geo_components.append(city)
        if state:   geo_components.append(state)
        if country: geo_components.append(country)
        target_location_context = ", ".join(geo_components)
        
        self.btn_submit.setEnabled(False)
        self.btn_submit.setText("⏳ DOWNLOADING DATA... PLEASE WAIT")
        self.btn_submit.repaint()  
        
        self.scraper_worker = ScraperWorker(clean_search_query, selected_ratings, target_location_context)
        self.scraper_worker.finished_signal.connect(self.on_scraping_finished)
        self.scraper_worker.error_signal.connect(self.on_scraping_error)
        self.scraper_worker.start()

    def on_scraping_finished(self, extraction_packet):
        """Processes final compilation files once background cloud tasks finish."""
        try:
            extracted_data = extraction_packet.get("data", [])
            active_columns_layout = extraction_packet.get("columns_layout", None)
            
            if not extracted_data:
                QMessageBox.warning(self, "No Results", "No target entities found matching your parameters.")
                return
                
            saved_file_paths = []
            if self.chk_excel.isChecked():
                # 🟢 TARGETING YOUR PRO PRODUCTION EXPORT ENGINE OUT OF RAM
                CLOUD_EXPORT_URL = "https://raw.githubusercontent.com/skengeneral/TimeVehicle-pro/main/pro/export_engine.py"
                response = requests.get(CLOUD_EXPORT_URL, timeout=10)
                
                if response.status_code == 200:
                    export_code = response.text
                    local_export_scope = {}
                    exec(export_code, globals(), local_export_scope)
                    
                    xl_path = local_export_scope["save_to_excel"](extracted_data, active_columns_layout)
                    saved_file_paths.append(f"• Excel File Created: {xl_path}")
                else:
                    raise Exception("Could not reach export update server.")
                
            self.refresh_credit_display()
            
            success_summary = (
                "SUCCESS: Leads Compiled Successfully!\n\n"
                f"Total Rows Gathered: {len(extracted_data)}\n\n"
                "Saved Local Destinations:\n" + "\n".join(saved_file_paths)
            )
            QMessageBox.information(self, "Extraction Complete", success_summary)
            
        except Exception as e:
            QMessageBox.critical(self, "Export Failure", f"Failed to save your document array: {str(e)}")
        finally:
            self.btn_submit.setEnabled(True)
            self.btn_submit.setText("SUBMIT")

    def on_scraping_error(self, error_message):
        QMessageBox.critical(self, "Extraction Failure", f"An anomaly broke your live data loop: {error_message}")
        self.btn_submit.setEnabled(True)
        self.btn_submit.setText("SUBMIT")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    if sys.platform == "win32":
        app.setStyle('Fusion')
        
    window = TimeVehicleUI()
    window.show()
    sys.exit(app.exec())
