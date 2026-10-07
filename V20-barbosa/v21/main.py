import tkinter as tk
from tkinter import ttk, messagebox
import serial
import time
import serial.tools.list_ports
import threading
from tkinter import ttk, filedialog
from PIL import Image, ImageTk
from conexao_tab import conexaoTab
from iec44_tab import IEC44Tab
from iec45_tab import IEC45Tab
from iec46_tab import IEC46Tab
from iec411_tab import IEC411Tab

#from iec44_tab import build_4_4_tab
#from iec45_tab import build_placeholder_tab_iec45
#from iec46_tab import build_placeholder_tab_iec46
#from iec411_tab import build_placeholder_tab_iec411

class ConversorSerialApp:
    def __init__(self, master):
        self.master = master
        master.title("EMTEST-LGE")
        master.geometry("900x600")

        self.ucs_bool = True
        self.montar = False
        self.montar_4_5 = False
        self.lim = 0
        self.prmt_4_4 = False
        self.prmt_4_5 = False
        self.pause_uni = False
        self.pause_uni_4_5 = False
        self.pause_seq = False
        self.pause_seq_4_5 = False

        self.tempo_inicial = 0
        self.tempo_seq_inicial = 0
        self.tempo_decorrido = 0
        self.tempo_seq_decorrido = 0
        self.rodando = False
        self.rodando_seq = False
        self.varp0 = " "
        self.varp1 = " "
        self.varp2 = " "
        self.varp3 = " "
        self.varp4 = " "
        self.varp5 = " "
        self.varp6 = " "
        self.intervalo_seq = 0
        
        # Criando estilo personalizado para LabelFrame
        style = ttk.Style()
        style.configure("Custom.TLabelframe", background="#f0f0f0", borderwidth=3, relief="groove")
        style.configure("Custom.TLabelframe.Label", font=("Arial", 12, "bold"), foreground="#003366")

        # Criando o Notebook (TabView)
        self.notebook = ttk.Notebook(master)
        self.notebook.pack(expand=True, fill="both")

        # Criando as abas
        self.tab_conexao = ttk.Frame(self.notebook)
        self.tab_iec44 = ttk.Frame(self.notebook)
        self.tab_iec45 = ttk.Frame(self.notebook)
        self.tab_iec46 = ttk.Frame(self.notebook)
        self.tab_iec411 = ttk.Frame(self.notebook)

        # Adicionando as abas ao Notebook
        self.notebook.add(self.tab_conexao, text="Conexão")
        self.notebook.add(self.tab_iec44, text="IEC 61000-4-4")
        self.notebook.add(self.tab_iec45, text="IEC 61000-4-5")
        self.notebook.add(self.tab_iec46, text="IEC 61000-4-6")
        self.notebook.tab(3, state="disabled")  # Aba 4-6 desabilitada inicialmente
        self.notebook.add(self.tab_iec411, text="IEC 61000-4-11")

        # Construindo a aba Conexão
        #self.build_conexao_tab()
        #conexaoTab(self.tab_conexao, self)
        self.conexao = conexaoTab(self.tab_conexao, self)

        # Construindo a aba IEC 61000-4-4
        #self.build_4_4_tab()
        IEC44Tab(self.tab_iec44, self)

        # Construindo as outras abas (placeholder)        
        #self.build_placeholder_tab(self.tab_iec45, "Configurações para IEC 61000-4-5")
        #self.build_placeholder_tab(self.tab_iec46, "Configurações para IEC 61000-4-6")
        #self.build_placeholder_tab(self.tab_iec411, "Configurações para IEC 61000-4-11")
        IEC45Tab(self.tab_iec45, self)
        IEC46Tab(self.tab_iec46, self)
        IEC411Tab(self.tab_iec411, self)


        # -----------------------------------------------------------------------------------
# Inicialização
if __name__ == "__main__":
    root = tk.Tk()
    app = ConversorSerialApp(root)
    root.mainloop()