
from PyQt5.QtWidgets import QWidget,QVBoxLayout,QPushButton

class Sidebar(QWidget):
    def __init__(self, callback):
        super().__init__()
        self.callback=callback
        lay=QVBoxLayout(self)
        for cat in ["Lumber", "Cheesesmithing"]:
            b=QPushButton(cat)
            b.clicked.connect(lambda _,c=cat: callback(c))
            lay.addWidget(b)
        lay.addStretch(1)
