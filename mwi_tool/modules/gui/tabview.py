from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from modules.profit import compute_profit

class TabView(QWidget):
    def __init__(self, recipes, base_prices, market_prices, speed):
        super().__init__()
        self.recipes = recipes
        self.base_prices = base_prices
        self.market_prices = market_prices
        self.speed = speed
        lay = QVBoxLayout(self)
        self.table = QTableWidget()
        lay.addWidget(self.table)
        self.refresh()

    def refresh(self):
        r = self.recipes
        self.table.setRowCount(len(r))
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            ["Item", "Saída", "Tempo base", "Tempo efetivo", "Custo", "Lucro", "C/H", "L/H"]
        )
        results = [compute_profit(x, self.base_prices, self.market_prices, self.speed) for x in r]
        best = max(x["pph"] for x in results) if results else 0
        for row, (rec, res) in enumerate(zip(r, results)):
            vals = [
                rec["name"],
                str(rec["output_qty"]),
                f"{rec['base_time']:.2f}",
                f"{res['eff']:.2f}",
                f"{res['cost']:.2f}",
                f"{res['profit']:.2f}",
                f"{res['cph']:.2f}",
                f"{res['pph']:.2f}",
            ]
            for col, v in enumerate(vals):
                it = QTableWidgetItem(v)
                if col > 0:
                    it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if res["pph"] == best and best > 0:
                    it.setBackground(QColor(90, 40, 120))
                    it.setForeground(QColor(255, 255, 255))
                self.table.setItem(row, col, it)
        self.table.resizeColumnsToContents()
