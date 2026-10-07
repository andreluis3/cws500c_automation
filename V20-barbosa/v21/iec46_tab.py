from tkinter import ttk

class IEC46Tab:
    def __init__(self, parent, app):
        self.app = app
        self.iec46_tab = parent
        self.build_ui()

    def build_ui(self):
        label = ttk.Label(self.iec46_tab, text="IEC 61000-4-6 (Em construção!)")
        label.pack(pady=20)

        