from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
from types import SimpleNamespace
import tkinter as tk
from tkinter import ttk


ui_path = Path(__file__).resolve().parent / "ui" / "tab_4-6"
loader = SourceFileLoader("iec46_ui", str(ui_path))
spec = spec_from_loader(loader.name, loader)
if spec is None:
    raise ImportError(f"Não foi possível carregar a interface em {ui_path}")

ui_module = module_from_spec(spec)
loader.exec_module(ui_module)
IEC46Tab = ui_module.IEC46Tab


class IEC46TabVisualOnly(IEC46Tab):
    def _build_handlers(self):
        return {}


def main():
    root = tk.Tk()
    root.title("EMTEST-LGE - IEC 61000-4-6")
    root.geometry("900x600")

    parent = ttk.Frame(root)
    parent.pack(expand=True, fill="both")

    app = SimpleNamespace()
    IEC46TabVisualOnly(parent, app)

    root.mainloop()


if __name__ == "__main__":
    main()
