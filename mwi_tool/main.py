import sys, os, json
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout
from modules.theme import apply_dark_theme
from modules.loader import load_all_professions
from modules.gui.sidebar import Sidebar
from modules.gui.tabview import TabView

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")


def load_base_prices():
    path = os.path.join(DATA_DIR, "prices.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_market_prices():
    path = os.path.join(DATA_DIR, "market_prices.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MWI Tool")
        self.resize(1200, 800)
        self.prof = load_all_professions(os.path.join(DATA_DIR))
        self.base_prices = load_base_prices()
        self.market_prices = load_market_prices()
        self.speed = 0.0

        central = QWidget()
        self.setCentralWidget(central)
        lay = QHBoxLayout(central)

        self.sidebar = Sidebar(self.load_tab)
        lay.addWidget(self.sidebar)
        self.current = None

    def load_tab(self, cat):
        if self.current:
            self.current.setParent(None)
        self.current = TabView(self.prof[cat], self.base_prices, self.market_prices, self.speed)
        self.centralWidget().layout().addWidget(self.current)


def main():
    app = QApplication(sys.argv)
    apply_dark_theme(app)
    w = Main()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
