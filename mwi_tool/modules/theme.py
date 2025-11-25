
from PyQt5.QtGui import QPalette, QColor

def apply_dark_theme(app):
    app.setStyle('Fusion')
    pal=QPalette()
    colors={
        QPalette.Window:QColor(53,53,53),
        QPalette.WindowText:QColor(240,240,240),
        QPalette.Base:QColor(35,35,35),
        QPalette.AlternateBase:QColor(53,53,53),
        QPalette.ToolTipBase:QColor(240,240,240),
        QPalette.ToolTipText:QColor(240,240,240),
        QPalette.Text:QColor(240,240,240),
        QPalette.Button:QColor(53,53,53),
        QPalette.ButtonText:QColor(240,240,240),
        QPalette.Highlight:QColor(142,45,197),
        QPalette.HighlightedText:QColor(240,240,240)
    }
    for k,v in colors.items():
        pal.setColor(k,v)
    app.setPalette(pal)
