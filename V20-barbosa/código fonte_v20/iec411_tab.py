from tkinter import ttk
import tkinter as tk
from PIL import Image, ImageTk
import serial
import time
from tkinter import ttk, messagebox, filedialog
import threading
import queue
import re
from serial.serialutil import SerialException, PortNotOpenError
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import MaxNLocator
import csv
from datetime import datetime

class IEC411Tab:
    _CODE_RE = re.compile(r'^\s*([A-Z]{2})(?:,([^:;]*))?(?::([^;]*))?\s*;?\s*$', re.I)

    
    # aceita números com ponto ou vírgula decimal, com ou sem sinal, e opcional expoente
    NUM = r'[+-]?(?:\d+(?:[.,]\d+)?|\d*[.,]\d+)(?:[eE][+-]?\d+)?'

    RM_RE = re.compile(rf'^\s*RM\s*,\s*({NUM})\s*,\s*({NUM})\s*;?\s*$', re.IGNORECASE)

    def __init__(self, parent, app):
        self.app = app
        self.iec411_tab = parent
        self.build_4_11_tab()        
        self._cmd_queue = queue.Queue()
        self._serial_worker_started = False
        

        # --- sessão serial persistente ---
        self._ser = None
        
        self._q_serial_4_11 = None
        self._stop_serial_4_11 = None
        self._reader_4_11 = None

        
        self.after_timer_id = None        # after() do verificador de tempo
        self.after_consume_id = None      # after() do consumidor da fila
        self.inicio_4_11 = None 


        self._buf_4_11 = bytearray()
        self._rx_thread = None
        self._tx_thread = None
        self._tx_queue = queue.Queue()
        self._event_queue = queue.Queue()
        self._stop_evt = threading.Event()

        self._handlers = self._build_handlers()

        self.contador = 0
        self.soma_impulsos = 0
        self.varp4 = 0
        self.cont = 0
        self.cont_total = 0
        self.i_atual = 0
        
        self.tensoes = []
        self.correntes = []
        self.dados_medidos = []

        self._buffer_serial = ""
        
# --- CRIA janela e figura para o gráfico ---
        ### Corrente ###
        self.fig_corrente, self.ax_corrente = plt.subplots(figsize=(7,4))
        self.ax_corrente.set_title("Gráfico da corrente do impulso")
        self.ax_corrente.set_xlabel("Impulsos")
        self.ax_corrente.set_ylabel("Corrente (A)")
        self.ax_corrente.grid(True)
        self.ax_corrente.xaxis.set_major_locator(MaxNLocator(integer=True))
            # Linha do gráfico que vai ser atualizada
        self.linha_corrente, = self.ax_corrente.plot([], [], marker="o", label="Corrente (A)")
        self.ax_corrente.legend()
            # A janela Tkinter onde o gráfico ficará incorporado
        self.graph_window_corrente = None
        self.canvas_corrente = None

        ### Tensão ###
        self.fig_tensao, self.ax_tensao = plt.subplots(figsize=(7,4))
        self.ax_tensao.set_title("Gráfico da tensão do impulso")
        self.ax_tensao.set_xlabel("Impulsos")
        self.ax_tensao.set_ylabel("Tensão (V)")
        self.ax_tensao.grid(True)
        self.ax_tensao.xaxis.set_major_locator(MaxNLocator(integer=True))
            # Linha do gráfico que vai ser atualizada
        self.linha_tensao, = self.ax_tensao.plot([], [], marker="o", label="Tensão (V)")
        self.ax_tensao.legend()
            # A janela Tkinter onde o gráfico ficará incorporado
        self.graph_window_tensao = None
        self.canvas_tensao = None


    # Estilo e tag para destaque
        style_treeview = ttk.Style()
        style_treeview.map("Treeview",
          background=[("selected", "lightblue")],
          foreground=[("selected", "black")])
        style_treeview.configure("Treeview", rowheight=25)

    # Aba IEC 61000-4-5
    def build_4_11_tab(self):

        ### Frame para seleção de tensão de entrada
        frame_4_11_alimentacao = ttk.LabelFrame(self.iec411_tab, text="Alimentação", style="Custom.TLabelframe", padding=(10, 10))
        frame_4_11_alimentacao.place(x=20, y=20, width=125, height=130)
        self.alimentacao_var = tk.StringVar(value="60")
        rb_50hz = tk.Radiobutton(frame_4_11_alimentacao, text="50 Hz", variable=self.alimentacao_var, value="50")
        rb_60hz = tk.Radiobutton(frame_4_11_alimentacao, text="60 Hz", variable=self.alimentacao_var, value="60")
        rb_50hz.place(x=0, y=5)
        rb_60hz.place(x=53, y=5)
        
        label_u_nom = ttk.Label(frame_4_11_alimentacao, text="U_nominal (V):", foreground="red")
        label_u_nom.place(x=10, y=50)

        self.u_nom_var = tk.StringVar()
        entry_u_nom = ttk.Entry(frame_4_11_alimentacao, width=6, textvariable=self.u_nom_var)
        entry_u_nom.place(x=30, y=70)

        
        ### Frame para Aplicação única
        frame_4_11_unico = ttk.LabelFrame(self.iec411_tab, text="Aplicação única", style="Custom.TLabelframe", padding=(10, 10))
        frame_4_11_unico.place(x=150, y=20, width=475, height=130)
        
        tk.Label(frame_4_11_unico, text="Nível (%U):").place(x=1, y=1)
        
        tensao_4_11 = ["0", "40", "70", "80"]
        self.combo_tensao_4_11 = ttk.Combobox(frame_4_11_unico, values=tensao_4_11, width=8, state="readonly")
        self.combo_tensao_4_11.place(x=70, y=1)
        self.combo_tensao_4_11.set("0")

        tk.Label(frame_4_11_unico, text="Sincronismo (º):").place(x=160, y=1)

        sinc_4_11 = ["0", "45", "90", "135", "180", "225", "270", "315"]
        self.combo_sinc_4_11 = ttk.Combobox(frame_4_11_unico, values=sinc_4_11, width=8, state="readonly")
        self.combo_sinc_4_11.place(x=255, y=1)
        self.combo_sinc_4_11.set("0")

        tk.Label(frame_4_11_unico, text="Trigger:").place(x=1, y=25)

        trigger_4_11 = ["AUTO", "MANUAL"]
        self.combo_trigger_4_11 = ttk.Combobox(frame_4_11_unico, values=trigger_4_11, width=8, state="readonly")
        self.combo_trigger_4_11.place(x=70, y=25)
        self.combo_trigger_4_11.set("AUTO")

        tk.Label(frame_4_11_unico, text="Nº Repetições:").place(x=160, y=25)

        repeticao_4_11 = ["1", "2", "3", "4", "5", "10", "15", "20", "50", "100"]
        self.combo_repeticao_4_11 = ttk.Combobox(frame_4_11_unico, values=repeticao_4_11, width=8, state="readonly")
        self.combo_repeticao_4_11.place(x=255, y=25)
        self.combo_repeticao_4_11.set("3")

        tk.Label(frame_4_11_unico, text="Canal:").place(x=1, y=49)

        canal_4_11 = ["PF1", "PF2", "ΔU"]
        self.combo_canal_4_11 = ttk.Combobox(frame_4_11_unico, values=canal_4_11, width=8, state="readonly")
        self.combo_canal_4_11.place(x=70, y=49)
        self.combo_canal_4_11.set("ΔU")

        tk.Label(frame_4_11_unico, text="N° de ciclos:").place(x=160, y=49)

        n_ciclos_4_11 = ["0,5", "1", "10", "12", "25", "30", "250", "300"]
        self.combo_n_ciclos_4_11 = ttk.Combobox(frame_4_11_unico, values=n_ciclos_4_11, width=8, state="readonly")
        self.combo_n_ciclos_4_11.place(x=255, y=49)
        self.combo_n_ciclos_4_11.set("0,5")

        tk.Label(frame_4_11_unico, text="Intervalo (s):").place(x=160, y=73)

        tempo_4_11 = ["1", "3", "5", "10", "30", "60"]
        self.combo_tempo_4_11 = ttk.Combobox(frame_4_11_unico, values=tempo_4_11, width=8, state="readonly")
        self.combo_tempo_4_11.place(x=255, y=73)
        self.combo_tempo_4_11.set("10")

        self.btn_4_11_enviar = tk.Button(frame_4_11_unico, text="Enviar\nparâmetros", command=self.previa_envia_parametros_4_11, width=10, height=2, bg="#9EE8BE")
        self.btn_4_11_enviar.place(x=355, y=45)

        self.btn_4_11_fatores = tk.Button(frame_4_11_unico, text="Fatores de\ncorreção", command=self.abrir_fatores_correcao, width=10, height=2, bg="#FFF6BF")
        self.btn_4_11_fatores.place(x=355, y=0)

        #self.btn_4_11_v2 = tk.Button(frame_4_11_unico, text="V2", command=self.envia_v2, width=10, height=1, bg="#FFF6BF")
        #self.btn_4_11_v2.place(x=10, y=70)
        
        ### Frame para Aplicação sequencial
        frame_4_11_sequencial = ttk.LabelFrame(self.iec411_tab, text="Aplicação sequêncial", style="Custom.TLabelframe", padding=(10, 10))
        frame_4_11_sequencial.place(x=20, y=160, width=860, height=245)
        
        tk.Label(frame_4_11_sequencial, text="Nível (%U):").place(x=20, y=13)
        self.combo_seq_tensao_4_11 = ttk.Combobox(frame_4_11_sequencial, values=tensao_4_11, width=8, state="readonly")
        self.combo_seq_tensao_4_11.place(x=140, y=13)
        self.combo_seq_tensao_4_11.set("0")
        
        tk.Label(frame_4_11_sequencial, text="Sincronismo (º):").place(x=20, y=38)
        self.combo_seq_duracao_4_11 = ttk.Combobox(frame_4_11_sequencial, values=sinc_4_11, width=8, state="readonly")
        self.combo_seq_duracao_4_11.place(x=140, y=38)
        self.combo_seq_duracao_4_11.set("0")
        
        tk.Label(frame_4_11_sequencial, text="Canal:").place(x=20, y=63)
        self.combo_seq_canal_4_11 = ttk.Combobox(frame_4_11_sequencial, values=canal_4_11, width=8, state="readonly")
        self.combo_seq_canal_4_11.place(x=140, y=63)
        self.combo_seq_canal_4_11.set("ΔU")
        
        tk.Label(frame_4_11_sequencial, text="Trigger:").place(x=20, y=88)
        self.combo_seq_freq_4_11 = ttk.Combobox(frame_4_11_sequencial, values=trigger_4_11, width=8, state="readonly")
        self.combo_seq_freq_4_11.place(x=140, y=88)
        self.combo_seq_freq_4_11.set("AUTO")
        
        tk.Label(frame_4_11_sequencial, text="N° Repetições:").place(x=20, y=113)
        self.combo_seq_repeticao_4_11 = ttk.Combobox(frame_4_11_sequencial, values=repeticao_4_11, width=8, state="readonly")
        self.combo_seq_repeticao_4_11.place(x=140, y=113)
        self.combo_seq_repeticao_4_11.set("3")
        
        tk.Label(frame_4_11_sequencial, text="N° de ciclos:").place(x=20, y=138)
        self.combo_seq_n_ciclos_4_11 = ttk.Combobox(frame_4_11_sequencial, values=n_ciclos_4_11, width=8, state="readonly")
        self.combo_seq_n_ciclos_4_11.place(x=140, y=138)
        self.combo_seq_n_ciclos_4_11.set("0,5")
        
        tk.Label(frame_4_11_sequencial, text="Intervalo (s):").place(x=20, y=163)
        self.combo_seq_tempo_4_11 = ttk.Combobox(frame_4_11_sequencial, values=tempo_4_11, width=8, state="readonly")
        self.combo_seq_tempo_4_11.place(x=140, y=163)
        self.combo_seq_tempo_4_11.set("10")
        
        #self.tree = ttk.Treeview(frame_4_11_sequencial, columns=("ID", "Acoplamento", "Tensão", "Polaridade", "Duração", "Repetição", "Frequência", "T_Ensaio"), show="headings", height=7)
        self.tree = ttk.Treeview(frame_4_11_sequencial, columns=("Acoplamento", "Tensão", "Polaridade", "Sincronismo", "Repetições", "Trigger", "T_Ensaio"), show="headings", height=7)
        #self.tree.heading("ID", text="ID")
        self.tree.heading("Acoplamento", text="N.Ciclos.")
        self.tree.heading("Tensão", text="%U")
        self.tree.heading("Polaridade", text="Canal")
        self.tree.heading("Sincronismo", text="Sinc.(º)")
        self.tree.heading("Repetições", text="Rep.")
        self.tree.heading("Trigger", text="Trig.")
        self.tree.heading("T_Ensaio", text="T(s)")
        
        #self.tree.column("ID", width=50)
        self.tree.column("Acoplamento", width=65)
        self.tree.column("Tensão", width=65)
        self.tree.column("Polaridade", width=65)
        self.tree.column("Sincronismo", width=65)
        self.tree.column("Repetições", width=65)
        self.tree.column("Trigger", width=65)
        self.tree.column("T_Ensaio", width=65)
        self.tree.place(x=330, y=1)

        # Configura tag para destaque
        self.tree.tag_configure("destaque", background="yellow", foreground="black")

        # Configura tag para default
        self.tree.tag_configure("default", background="white", foreground="black")

        #self.scrollbar = tk.Scrollbar(frame_4_11_sequencial, orient=tk.VERTICAL)
        #self.scrollbar.place(x=340, y=1, height=200)

        self.scrollbar = ttk.Scrollbar(frame_4_11_sequencial, orient=tk.VERTICAL, command=self.tree.yview)
        self.scrollbar.place(x=310, y=1, height=200)
        self.tree.configure(yscrollcommand=self.scrollbar.set)

        self.btn_4_11_incluir = tk.Button(frame_4_11_sequencial, text="-->>", command=self.adicionar_item_4_11, width=7, height=1, bg="#9EE8BE")
        self.btn_4_11_incluir.place(x=230, y=14)
        self.btn_4_11_excluir = tk.Button(frame_4_11_sequencial, text="<<--", command=self.remover_item_4_11, width=7, height=1, bg="#B0B0B0", state="disabled")
        self.btn_4_11_excluir.place(x=230, y=49)
        self.btn_4_11_editar = tk.Button(frame_4_11_sequencial, text="Edit.Linha", command=self.editar_item_4_11, width=7, height=1, bg="#B0B0B0", state="disabled")
        self.btn_4_11_editar.place(x=230, y=84)
        self.btn_4_11_deletar = tk.Button(frame_4_11_sequencial, text="Del.Linha", command=self.deletar_item_4_11, width=7, height=1, bg="#B0B0B0", state="disabled")
        self.btn_4_11_deletar.place(x=230, y=119)
        self.btn_4_11_montar = tk.Button(frame_4_11_sequencial, text="Montar", command=self.previa_montar_4_11, width=7, height=1, bg="#B0B0B0", state="disabled")
        self.btn_4_11_montar.place(x=230, y=154)
        #self.btn_4_11_proximo = tk.Button(frame_4_11_sequencial, text="Próximo", command=self.iniciar_tempo_4_11, width=7, height=2)
        #self.btn_4_11_proximo.place(x=600, y=210)
        self.btn_4_11_salvar = tk.Button(frame_4_11_sequencial, text="Salvar", command=self.salvar_4_11, width=6, height=2, bg="#9EE8BE", state="normal")
        self.btn_4_11_salvar.place(x=790, y=20)
        self.btn_4_11_abrir = tk.Button(frame_4_11_sequencial, text="Abrir", command=self.abrir_4_11, width=6, height=2, bg="#9EE8BE")
        self.btn_4_11_abrir.place(x=790, y=70)
        self.btn_4_11_deletarTab = tk.Button(frame_4_11_sequencial, text="Del.Tab.", command=self.limpar_treeview, width=6, height=2, bg="#9EE8BE", state="normal")
        self.btn_4_11_deletarTab.place(x=790, y=120)

        ### Frame para controle
        frame_4_11_controle = ttk.LabelFrame(self.iec411_tab, text="Controle", style="Custom.TLabelframe", padding=(10, 10))
        frame_4_11_controle.place(x=630, y=20, width=250, height=130)

        self.img_play = Image.open("play.png").resize((40, 30))
        self.img_play = ImageTk.PhotoImage(self.img_play)
        self.img_play_lime = Image.open("play_lime.png").resize((40, 30))
        self.img_play_lime = ImageTk.PhotoImage(self.img_play_lime)
        self.img_stop = Image.open("stop.png").resize((40, 30))
        self.img_stop = ImageTk.PhotoImage(self.img_stop)
        self.img_stop_lime = Image.open("stop_lime.png").resize((40, 30))
        self.img_stop_lime = ImageTk.PhotoImage(self.img_stop_lime)
        self.img_continue = Image.open("continue.png").resize((40, 30))
        self.img_continue = ImageTk.PhotoImage(self.img_continue)
        self.img_continue_lime = Image.open("continue_lime.png").resize((40, 30))
        self.img_continue_lime = ImageTk.PhotoImage(self.img_continue_lime)
        self.img_pausar = Image.open("pause.png").resize((40, 30))
        self.img_pausar = ImageTk.PhotoImage(self.img_pausar)
        self.img_pausar_lime = Image.open("pause_lime.png").resize((40, 30))
        self.img_pausar_lime = ImageTk.PhotoImage(self.img_pausar_lime)

        
        self.btn_4_11_iniciar = tk.Button(frame_4_11_controle, image = self.img_play, command=self.iniciar_4_11, width=40, height=30)
        self.btn_4_11_iniciar.place(x=15, y=1)

        """self.btn_4_11_continuar = tk.Button(frame_4_11_controle, image = self.img_continue, command=self.continuar_4_11, width=40, height=30, state="disabled")
        self.btn_4_11_continuar.place(x=65, y=1)

        self.btn_4_11_pausar = tk.Button(frame_4_11_controle, image = self.img_pausar, command=self.pausar_4_11, width=40, height=30, state="normal")
        self.btn_4_11_pausar.place(x=115, y=1)"""

        self.btn_4_11_parar = tk.Button(frame_4_11_controle, image = self.img_stop_lime, command=self.parar_4_11, width=40, height=30)
        self.btn_4_11_parar.place(x=65, y=1)

        tk.Label(frame_4_11_controle, text="T. decorrido (hh:mm:ss):").place(x=1, y=45)

        self.label_tempo_decorrido = tk.Label(frame_4_11_controle, text="00:00:00", font=("Arial", 14), foreground="green")
        self.label_tempo_decorrido.place(x=150, y=45)

        tk.Label(frame_4_11_controle, text="Intervalo (hh:mm:ss):").place(x=1, y=68)

        self.label_tempo_parcial = tk.Label(frame_4_11_controle, text="00:00:00", font=("Arial", 14), foreground="blue")
        self.label_tempo_parcial.place(x=150, y=68)

        ### Área de resultado
        self.text_result_4_11 = tk.Text(self.iec411_tab, width=107, height=8.5)
        self.text_result_4_11.place(x=20, y=420)

        ### Tags para texto
        self.text_result_4_11.tag_config("Atenção", foreground="red", font=("Arial", 16, "bold"))
        self.text_result_4_11.tag_config("Sucesso", foreground="green", font=("Arial", 12, "bold"))
        self.text_result_4_11.tag_config("Normal", foreground="blue", font=("Arial", 12))

#------------------------------------------------------------------------------------------
#Funções
    def abrir_fatores_correcao(self):
        # ----------- Criar nova janela -----------
        janela = tk.Toplevel()
        janela.title("Fatores de Correção")
        janela.geometry("300x150")

        # ----------- Variáveis das Entry (StringVar) -----------
        self.fator1_var = tk.StringVar()
        self.fator2_var = tk.StringVar()
        self.fator3_var = tk.StringVar()

        # ----------- Ler valores do arquivo -----------
        try:
            with open("fatores_4_11.txt", "r", encoding="utf-8") as f:
                linhas = f.readlines()

                if len(linhas) >= 3:
                    self.fator1_var.set(linhas[0].strip())
                    self.fator2_var.set(linhas[1].strip())
                    self.fator3_var.set(linhas[2].strip())
                else:
                    self.fator1_var.set("0")
                    self.fator2_var.set("0")
                    self.fator3_var.set("0")

        except FileNotFoundError:
            # Se não existir, inicia com zeros
            self.fator1_var.set("0")
            self.fator2_var.set("0")
            self.fator3_var.set("0")

        # ----------- Label + Entry Fator 1 -----------
        ttk.Label(janela, text="Fator para U < 130 V:").place(x=10, y=20)
        ttk.Entry(janela, textvariable=self.fator1_var, width=15).place(x=140, y=20)

        # ----------- Label + Entry Fator 2 -----------
        ttk.Label(janela, text="Fator para U >= 130 V:").place(x=10, y=40)
        ttk.Entry(janela, textvariable=self.fator2_var, width=15).place(x=140, y=40)

        # ----------- Label + Entry Fator 3 -----------
        ttk.Label(janela, text="Fator de Transformação:").place(x=10, y=60)
        ttk.Entry(janela, textvariable=self.fator3_var, width=15).place(x=140, y=60)

        # ----------- Botão Salvar -----------
        ttk.Button(
            janela,
            text="Salvar",
            command=lambda: self.salvar_fatores(janela)
        ).place(x=120, y=100)


    def salvar_fatores(self, janela):
        try:
            with open("fatores_4_11.txt", "w", encoding="utf-8") as f:
                f.write(self.fator1_var.get() + "\n")
                f.write(self.fator2_var.get() + "\n")
                f.write(self.fator3_var.get() + "\n")

            messagebox.showinfo("Sucesso", "Valores salvos com sucesso!")
            janela.destroy()

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar arquivo:\n{e}")

    def calcula_nivel(self, nivel):
        nivel_u_str = self.u_nom_var.get()
        nivel_u_float = float(nivel_u_str.replace(",", "."))
        nivel_porcento = float(nivel)
        with open("fatores_4_11.txt", "r", encoding="utf-8") as f:
            linhas = f.readlines()
        if linhas:
            fator_menor130 = float(linhas[0].strip().replace(",", "."))
            fator_maior130 = float(linhas[1].strip().replace(",", "."))
            fator_transformacao = float(linhas[2].strip().replace(",", "."))
        else:
            messagebox.showwarning("Aviso", "Fatores de correção não encontrados!")
        if nivel_u_float < 130:
            v2 = float(((nivel_porcento/100.0) * nivel_u_float) / fator_menor130)
        elif nivel_u_float >= 130:
            v2 = float(((nivel_porcento/100.0) * nivel_u_float) / fator_maior130)
        else:
            messagebox.showwarning("Aviso", "Nível de tensão nominal (U) incorreto!")
        v2_int = int(v2)
        v2_variac = int(((v2_int * 4096) / 250)*fator_transformacao)
        print(f"Nivel porcento: {nivel_porcento}")
        print(f"Nivel_u_float: {nivel_u_float}")
        print(f"fator_menor: {fator_menor130}")
        print(f"fator_maior: {fator_maior130}")
        print(f"Nivel de U ajustado float: {v2}")
        print(f"Nivel de U ajustado inteiro: {v2_int}")
        return v2_variac
        
    def calcula_duracao(self):
        freq = float(self.alimentacao_var.get())
        n_ciclos = float(self.combo_n_ciclos_4_11.get().replace(",", "."))
        t = float(1 / freq)
        tempo_aplic = float(t * n_ciclos * 100000)
        tempo_aplic_int = int(tempo_aplic)
        """print(f"freq = {freq}")
        print(f"ciclos = {n_ciclos}")
        print(f"periodo = {t}")
        print(f"tempo float = {tempo_aplic}")
        print(f"tempo int= {tempo_aplic_int}")
        print(f"A duração, em ms, do dip é de: {tempo_aplic_int}")"""
        return tempo_aplic_int

    def calcula_duracao_seq(self, nciclos):
        freq = float(self.alimentacao_var.get())
        n_ciclos = float(nciclos.replace(",", "."))
        t = float(1 / freq)
        tempo_aplic = float(t * n_ciclos * 100000)
        tempo_aplic_int = int(tempo_aplic)
        """print(f"freq = {freq}")
        print(f"ciclos = {n_ciclos}")
        print(f"periodo = {t}")
        print(f"tempo float = {tempo_aplic}")
        print(f"tempo int= {tempo_aplic_int}")
        print(f"A duração, em ms, do dip é de: {tempo_aplic_int}")"""
        return tempo_aplic_int



    # grupos:
    # 1 = prefixo (ex: RR, RF, BS)
    # 2 = valor principal (ex: 00, 08, 18, 02, etc.)
    # 3 = qualificador opcional (se existir depois de ':')    
    def _parse_code(self, msg: str):
        """
        Retorna (code_base, params_dict, original)
        Ex.: "RR,08;" -> ("RR,08", {}, "RR,08;")
            "RF,.;"  -> ("RF,.", {}, "RF,.;")
            "RR,18:X;" -> ("RR,18", {"q":"X"}, "RR,18:X;")
        """
        m = type(self)._CODE_RE.match(msg.strip())
        if not m:
            return (None, {}, msg)
        prefix = m.group(1).upper()
        val = (m.group(2) or "").upper()
        qual = (m.group(3) or "").upper()

        code_base = prefix if not val else f"{prefix},{val}"
        params = {}
        if qual:
            params["q"] = qual
        return (code_base, params, msg)
    
    

    def _tentar_parse_rm(self, line: str):
        m = type(self).RM_RE.match(line.strip())
        if not m:
            return None
        u = float(m.group(1).replace(',', '.'))
        i = float(m.group(2).replace(',', '.'))
        return u, i


    
    def _build_handlers(self):
        return {
            "RR,00": self._on_rr_00_teste_finalizado,
            #"RR,02": self._on_rr_02_ready_for_trigger,
            #"RR,05": self._on_rr_05_fail1,
            #"RR,06": self._on_rr_06_running_stopped,
            #"RR,07": self._on_rr_07_fail2,
            #"RR,08": self._on_rr_08_overtemp,
            #"RR,10": self._on_rr_10_string_error,
            #"RR,11": self._on_rr_11_test_not_possible,
            #"RR,13": self._on_rr_13_unknown_parameter,
            #"RR,14": self._on_rr_13_unknown_parameter,
            #"RR,15": self._on_rr_15_checksum_error,
            #"RR,16": self._on_rr_16_sync_error,
            #"RR,18": self._on_rr_18_overcurrent,
            #"RR,20": self._on_rr_20_not_correctable,
            #"RF,.":  self._on_rf_feedback_freq,
            #"BS,.":  self._on_bs_feedback_bank,
            # adicione outros conforme a tabela do fabricante
        }
    
    def _handle_device_message(self, msg: str):
        # 1) tentar VCS (RM,U,I;)
        out = self._tentar_parse_rm(msg)
        if out is not None:
            u, i = out
            self._on_vcs_feedback(u, i, raw=msg)  # atualiza UI/lógica
            return

        # 2) restante do pipeline (RR, RF, BS…)
        code_base, params, original = self._parse_code(msg)
        if code_base:
            handler = self._handlers.get(code_base)
            if handler:
                handler(params, original)
                return

        self._log(f"[RX ?] {msg}")

    def _on_vcs_feedback(self, u: float, i: float, raw: str):
        # Ex.: atualizar labels
        try:
            self.lbl_u.config(text=f"U: {u:.2f} V")
            self.lbl_i.config(text=f"I: {i:.3f} A")
        except Exception:
            pass
        # Log leve
        self._log(f"VCS -> U={u:.3f} V, I={i:.3f} A")

    def envia_v2(self, v2):                    
        try:
            cfg = self._capturar_config_serial()
            self._ser = serial.Serial(**cfg)
            # Envia comando
            #self._ser.write(self.app.conexao.comando('BS,2;'))
            #time.sleep(2)
            #self._ser.write(self.app.conexao.comando('PC;'))
            #time.sleep(1)
            #self._ser.write(self.app.conexao.comando('BS,3;'))
            #time.sleep(2)
            self._ser.write(self.app.conexao.comando('PWM='+v2+'\n'))
            time.sleep(2)
            self._ser.close()
            #ucs_bool = True
            #t_total = self.tempo_total_uni_4_11()
            #horas = t_total // 3600
            #minutos = (t_total % 3600) // 60
            #segundos = t_total % 60
            #self.text_result_4_11.insert(tk.END, f"Parâmetros da Aplicação Única enviados! \nClique em 'Iniciar' para começar o ensaio.", "Normal")
            #self.text_result_4_11.insert(tk.END, f"\nA estimativa de duração total é de {horas:02}:{minutos:02}:{segundos:02}", "Normal")
            #time.sleep(3)
        except Exception as e:
            return f"Erro: {e}"

    def previa_envia_parametros_4_11(self):
        self.envia_parametros_4_11()
        self.text_result_4_11.delete("1.0", tk.END)
        self.text_result_4_11.insert(tk.END, f"Aguarde!", "Atenção")
        self.text_result_4_11.insert(tk.END, f"\nCarregando configurações do gerador.", "Normal")
        self.text_result_4_11.update_idletasks()  # força atualizar a tela
    
    
    def envia_parametros_4_11(self):
        #threading.Thread(target=self.text_result_4_11.delete("1.0", tk.END), daemon=True).start()
        #threading.Thread(target=self.text_result_4_11.insert(tk.END, "Aguarde"), daemon=True).start()
        #time.sleep(3)
        #self.text_result_4_11.after(0, lambda: messagebox.showwarning("Aguarde", f"Aguarde"))
        self.app.prmt_4_11 = True
        self.app.montar = False
        self.limpar_treeview()
        if self.app.ucs_bool is True:
            if self.u_nom_var.get() != '':
                string_comando = "PN,"

                string_comando += self.combo_sinc_4_11.get()+","

                send_n_ciclos_4_11 = str(self.calcula_duracao())
                string_comando += send_n_ciclos_4_11+","

                intervalo_4_11 = int(self.combo_tempo_4_11.get()) *100
                string_comando += str(intervalo_4_11)+","

                if self.combo_canal_4_11.get() == "PF1":
                    send_canal_4_11 = "0"
                elif self.combo_canal_4_11.get() == "PF2":
                    send_canal_4_11 = "1"
                elif self.combo_canal_4_11.get() == "ΔU":
                    send_canal_4_11 = "2"
                else:
                    print("Canal incorreto!")
                string_comando += send_canal_4_11+","

                send_nivel_ajustado_4_11 = str(self.calcula_nivel(self.combo_tensao_4_11.get()))
                self.envia_v2(send_nivel_ajustado_4_11)
                string_comando += "0,"

                if self.combo_trigger_4_11.get() == "AUTO":
                    send_trigger_4_11 = "0"
                elif self.combo_trigger_4_11.get() == "MANUAL":
                    send_trigger_4_11 = "1"
                else:
                    print("Trigger incorreto!")
                string_comando += send_trigger_4_11+","

                string_comando += self.combo_repeticao_4_11.get()+";"
                print(string_comando)

                try:
                    cfg = self._capturar_config_serial()
                    self._ser = serial.Serial(**cfg)
                    # Envia comando
                    #self._ser.write(self.app.conexao.comando('BS,2;'))
                    #time.sleep(2)
                    #self._ser.write(self.app.conexao.comando('PC;'))
                    #time.sleep(1)
                    self._ser.write(self.app.conexao.comando('BS,3;'))
                    time.sleep(2)
                    self._ser.write(self.app.conexao.comando(string_comando))
                    #time.sleep(1)
                    self._ser.close()
                    #ucs_bool = True
                    t_total = self.tempo_total_uni_4_11()
                    horas = t_total // 3600
                    minutos = (t_total % 3600) // 60
                    segundos = t_total % 60
                    self.text_result_4_11.delete("1.0", tk.END)
                    self.text_result_4_11.insert(tk.END, f"Parâmetros da Aplicação Única enviados! \nClique em 'Iniciar' para começar o ensaio.", "Normal")
                    self.text_result_4_11.insert(tk.END, f"\nA estimativa de duração total é de {horas:02}:{minutos:02}:{segundos:02}", "Normal")
                    #time.sleep(3)
                except Exception as e:
                    return f"Erro: {e}"
            else:
                self.text_result_4_11.delete("1.0", tk.END)
                messagebox.showwarning("Aviso", "Tensão nominal não informada!")
        else:
            messagebox.showwarning("Aviso", "Gerador desconectado!\nVerifique conexão serial.")
        return
    
    
    def envia_comando(self, string_cmd: str):
        """Enfileira comando para TX (não bloqueia a UI)."""
        if not self.app.ucs_bool:
            messagebox.showwarning("Aviso", "Gerador desconectado!\nVerifique conexão serial.")
            return
        self.iniciar_sessao_serial()
        if getattr(self, "_ser", None) is None:
            return
        if not string_cmd:
            return
        self._tx_queue.put(string_cmd)

    def iniciar_4_11(self):
        if self.app.ucs_bool is not True:
            messagebox.showwarning("Aviso", "Gerador desconectado!\nVerifique conexão serial.")
            return

        # --- CASO 1: aplicação única ---
        if self.app.montar is False and self.app.prmt_4_11 is True:
            try:
                config = self._capturar_config_serial()

                # (Opcional) Atualizações rápidas de UI antes de enviar, para dar feedback imediato
                self.text_result_4_11.delete("1.0", tk.END)
                self.text_result_4_11.insert(tk.END, "Enviando comando para o gerador...", "Normal")

                # Dispara worker (não congela a UI)
                threading.Thread(target=self._worker_enviar_AA_4_11, args=(config, "uni"), daemon=True).start()

            except Exception as e:
                return f"Erro: {e}"

            return

        # --- CASO 2: aplicação sequencial ---
        if self.app.montar is True and self.app.prmt_4_11 is False:
            try:
                config = self._capturar_config_serial()

                self.text_result_4_11.delete("1.0", tk.END)
                self.text_result_4_11.insert(tk.END, "Enviando comando para o gerador...", "Normal")

                threading.Thread(target=self._worker_enviar_AA_4_11, args=(config, "seq"), daemon=True).start()

            except Exception as e:
                return f"Erro: {e}"

            return

    def _capturar_config_serial(self):
        porta = self.app.conexao.combo_porta.get()
        baudrate = int(self.app.conexao.combo_baudrate.get())
        paridade = self.app.conexao.combo_paridade.get()
        data_bits = int(self.app.conexao.combo_data_bits.get())
        stop_bits = float(self.app.conexao.combo_stop_bits.get())
        timeout_user = float(self.app.conexao.combo_timeout_user.get())

        # ⚠️ Se o combo for em milissegundos, converta:
        # timeout_user = timeout_user / 1000.0

        paridade_map = {
            "None": serial.PARITY_NONE,
            "Even": serial.PARITY_EVEN,
            "Odd": serial.PARITY_ODD,
            "Mark": serial.PARITY_MARK,
            "Space": serial.PARITY_SPACE
        }

        # PySerial aceita ints, mas você pode preferir as constantes:
        bytesize_map = {5: serial.FIVEBITS, 6: serial.SIXBITS, 7: serial.SEVENBITS, 8: serial.EIGHTBITS}
        stopbits_map = {1: serial.STOPBITS_ONE, 1.5: serial.STOPBITS_ONE_POINT_FIVE, 2: serial.STOPBITS_TWO}

        return {
            "port": porta,
            "baudrate": baudrate,
            "bytesize": bytesize_map.get(data_bits, serial.EIGHTBITS),
            "parity": paridade_map[paridade],
            "stopbits": stopbits_map.get(stop_bits, serial.STOPBITS_ONE),
            "timeout": timeout_user,           # segundos!
            "write_timeout": timeout_user      # segundos!
        }

    
    
    def iniciar_sessao_serial(self):
        """Abre porta, inicializa threads RX/TX e bomba de eventos (se ainda não estiverem ativas)."""
        if getattr(self, "_ser", None):
            return
        try:
            cfg = self._capturar_config_serial()
            self._ser = serial.Serial(**cfg)
        except Exception as e:
            messagebox.showwarning("Erro", f"Não foi possível abrir porta: {e}")
            return

        if not hasattr(self, "_tx_queue"):
            self._tx_queue = queue.Queue()
        if not hasattr(self, "_event_queue"):
            self._event_queue = queue.Queue()
        if not hasattr(self, "_stop_evt"):
            self._stop_evt = threading.Event()

        self._stop_evt.clear()

        # Thread TX
        threading.Thread(target=self._tx_loop, daemon=True).start()
        # Thread RX (se você quiser receber respostas/eventos do 4.5)
        threading.Thread(target=self._rx_loop, daemon=True).start()

        # Bomba de eventos para UI (se já não estiver ativa)
        self._agendar_pump_ui()


    
    def parar_sessao_serial(self):
        """Use apenas ao finalizar ensaio, trocar porta, fechar app, ou erro crítico."""
        if not getattr(self, "_ser", None):
            return
        self._stop_evt.set()
        try:
            self._tx_queue.put_nowait(None)  # acorda TX
        except:
            pass
        try:
            self._ser.close()
        except:
            pass
        self._ser = None


    
    def _rx_loop(self):
        while not self._stop_evt.is_set():
            try:
                line = self._ser.readline()
                if not line:
                    continue
                txt = line.decode("ascii", errors="replace").strip()
                if not txt:
                    continue
                self._event_queue.put(("DEVICE_MSG", txt))
            except Exception as e:
                self._event_queue.put(("ERROR", f"RX erro: {e}"))


    
    def _tx_loop(self):
        while not self._stop_evt.is_set():
            try:
                item = self._tx_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if item is None:
                break
            try:
                payload = self.app.conexao.comando(item)  # seu método atual de formar bytes
                self._ser.write(payload)
                self._ser.flush()
                # log leve opcional na UI
                self._log(f"[TX] {item}")
            except Exception as e:
                # volta para UI via fila de eventos
                self._event_queue.put(("ERROR", f"TX erro ao enviar '{item}': {e}"))
            finally:
                self._tx_queue.task_done()


    
    def _agendar_pump_ui(self):
        """Chame uma vez no iniciar_sessao_serial; repete sozinho com after()."""
        try:
            while True:
                typ, payload = self._event_queue.get_nowait()
                if typ == "DEVICE_MSG":
                    self._handle_device_message(payload)   # seu dispatcher
                elif typ == "ERROR":
                    self._log(payload)
        except queue.Empty:
            pass
        # roda de novo em 50ms
        self.iec411_tab.after(50, self._agendar_pump_ui)


    
    def _log(self, txt: str):
        try:
            self.text_result_4_11.insert(tk.END, txt + "\n", "Normal")
            self.text_result_4_11.see(tk.END)
        except Exception:
            pass


    def _worker_enviar_AA_4_11(self, config, modo):
        """
        Roda fora da UI thread.
        modo: "uni" ou "seq"
        """
        try:
            with serial.Serial(**config) as s:
                s.write(self.app.conexao.comando('AA;'))
                #time.sleep(1)

        except Exception as e:
            # volta pro Tkinter para mostrar erro (UI)
            self.text_result_4_11.after(0, lambda: messagebox.showwarning("Erro", f"Falha na serial: {e}"))
            return

        # Ao terminar o envio com sucesso, voltar para UI thread
        self.text_result_4_11.after(0, lambda: self._apos_enviar_AA_4_11(modo))  
        
    def _apos_enviar_AA_4_11(self, modo):
        """
        Roda na UI thread depois que o comando AA; foi enviado e o worker terminou.
        """
                

        # UI comum aos dois modos
        self.btn_4_11_iniciar.config(image=self.img_play_lime)
        self.btn_4_11_iniciar.config(state="disabled")
        self.btn_4_11_incluir.config(state="disabled", bg="#B0B0B0")
        self.btn_4_11_excluir.config(state="disabled", bg="#B0B0B0")
        self.btn_4_11_deletar.config(state="disabled", bg="#B0B0B0")
        self.btn_4_11_montar.config(state="disabled", bg="#B0B0B0")
        self.btn_4_11_enviar.config(state="disabled", bg="#B0B0B0")
        #self.btn_4_11_montar_pp.config(state="disabled", bg="#B0B0B0")
        self.btn_4_11_editar.config(state="disabled", bg="#B0B0B0")
        self.btn_4_11_abrir.config(state="disabled", bg="#B0B0B0")
        self.btn_4_11_salvar.config(state="disabled", bg="#B0B0B0")
        self.btn_4_11_deletarTab.config(state="disabled", bg="#B0B0B0")
        self.btn_4_11_parar.config(image=self.img_stop)
        #self.btn_4_11_pausar.config(state="normal")

        # Agora separa a lógica de cada modo
        if modo == "uni":
            # (Re)inicia/organiza contador (sem bloquear)
            self.parar_tempo_4_11()
            self.iniciar_tempo_4_11()
            self.app.prmt_4_11 = True
            self.app.montar = False
            self.app.pause_uni = True
            self.app.pause_seq = False
            self.verificar_tempo_4_11()
            self.dados_medidos.append({"Data/Hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "V nominal": self.u_nom_var.get(), "Frequencia": self.alimentacao_var.get(), 
                                           "U%": self.combo_tensao_4_11.get(), "Sincronismo": self.combo_sinc_4_11.get(), "N ciclos": self.combo_n_ciclos_4_11.get(),
                                          "Intervalo": self.combo_tempo_4_11.get(), "N repeticoes": self.combo_repeticao_4_11.get(), "Canal": self.combo_canal_4_11.get(),
                                          "Trigger": self.combo_trigger_4_11.get()})
            
            t_total = self.tempo_total_uni_4_11()
            horas = t_total // 3600
            minutos = (t_total % 3600) // 60
            segundos = t_total % 60

            t_intervalo = int(self.combo_tempo_4_11.get())
            horas_i = t_intervalo // 3600
            minutos_i = (t_intervalo % 3600) // 60
            segundos_i = t_intervalo % 60

            self.text_result_4_11.delete("1.0", tk.END)
            self.text_result_4_11.insert(tk.END, f"Aplicação única iniciada! \nA estimativa de duração total é de {horas:02}:{minutos:02}:{segundos:02}", "Normal")
            self.label_tempo_parcial.config(text=f"{horas_i:02}:{minutos_i:02}:{segundos_i:02}") 
            return

        if modo == "seq":
            if self.cont > 0:
                self.pausar_tempo_4_11()
                self.retomar_tempo_4_11()
            else:
                self.parar_tempo_4_11()
                self.iniciar_tempo_4_11()
            #self.intervalo_seq = (int(self.busca_item_4_11(0, 6)) * 1000) #- 1000
            self.app.prmt_4_11 = False
            self.app.montar = True
            self.app.pause_uni = False
            self.app.pause_seq = True
            self.verificar_tempo_4_11()
            self.dados_medidos.append({"Data/Hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "V nominal": self.u_nom_var.get(),
                                       "Frequencia": self.alimentacao_var.get(), "U%": self.busca_item_4_11(self.i_atual, 1),
                                       "Sincronismo": self.busca_item_4_11(self.i_atual, 3), "N ciclos": self.busca_item_4_11(self.i_atual, 0),
                                  "Intervalo": self.busca_item_4_11(self.i_atual, 6), "N repeticoes": self.busca_item_4_11(self.i_atual, 4),
                                       "Canal": self.busca_item_4_11(self.i_atual, 2), "Trigger": self.busca_item_4_11(self.i_atual, 5)})
                        
            #self.iec411_tab.after(0, lambda: self.proximo_4_11(0))

            #self.iniciar_seq_tempo_4_11()
            #self.verificar_seq_tempo_4_11()

            #self.app.pause_seq = True

            t_total = self.tempo_total_4_11()
            horas = t_total // 3600
            minutos = (t_total % 3600) // 60
            segundos = t_total % 60

            t_intervalo = int(self.busca_item_4_11(0, 6))
            horas_i = t_intervalo // 3600
            minutos_i = (t_intervalo % 3600) // 60
            segundos_i = t_intervalo % 60

            self.text_result_4_11.delete("1.0", tk.END)
            self.text_result_4_11.insert(tk.END, f"Aplicação sequencial iniciada! \nA estimativa de duração total é de {horas:02}:{minutos:02}:{segundos:02}", "Normal")
            self.label_tempo_parcial.config(text=f"{horas_i:02}:{minutos_i:02}:{segundos_i:02}")
            return    
    
    def parar_4_11(self, por_tempo: bool = False):

        #print("\n=== INICIANDO PARADA 4_11 ===")
        # 1) Cancelar afters
        for attr in ("after_timer_id", "after_consume_id"):
            after_id = getattr(self, attr, None)
            if after_id:
                try:
                    self.iec411_tab.after_cancel(after_id)
                except:
                    pass
                setattr(self, attr, None)

        # 2) Sinaliza a thread leitora para parar
        try:
            if self._stop_serial_4_11:
                #print("Sinalizando thread leitora para parar...")
                self._stop_serial_4_11.set()
        except:
            pass

        # 3) Fecha porta para forçar read() a quebrar
        try:
            if self._ser and self._ser.is_open:
                #print("Fechando porta para quebrar leitura...")
                self._ser.close()
        except:
            pass

        # 4) Aguarda thread sair
        try:
            if self._reader_4_11 and self._reader_4_11.is_alive():
                #print("Aguardando thread leitora terminar...")
                self._reader_4_11.join(timeout=1.0)
                #print("Thread leitora finalizada (ou timeout).")
        except:
            pass
        finally:
            self._reader_4_11 = None

        # 5) Thread auxiliar que finaliza serial + envia AS
        def _finalizar_serial_e_ui():

            #print("=== THREAD FINALIZADORA INICIOU ===")
            self.cont_total = 0
            try:
                # Reabre porta só para enviar AS:
                try:
                    self._abrir_porta_once()
                    time.sleep(0.1)
                except Exception as e:
                    print(f"Falha ao reabrir porta para enviar AS: {e}")

                if self._ser and self._ser.is_open:
                    try:
                        cmd = self.app.conexao.comando("AS;")
                        #print(f"ENVIANDO AS -> {cmd}")
                        self._ser.write(cmd)
                        self._ser.flush()
                        time.sleep(0.2)
                    except Exception as e:
                        print(f"ERRO AO ENVIAR AS: {e}")

                # Fecha porta
                try:
                    #print("Fechando porta após enviar AS...")
                    self._ser.close()
                except:
                    pass

            finally:
                def _fim_ui():
                    self.text_result_4_11.delete("1.0", tk.END)
                    self.text_result_4_11.insert(tk.END, "Ensaio parado!" if not por_tempo else "Ensaio finalizado!", "Sucesso")
                    self.parar_tempo_4_11()
                    self.salvar_dados_csv()                    
                    self.dados_medidos.clear()

                    #self.cont = 0

                    self.btn_4_11_iniciar.config(image=self.img_play, state="normal")
                    self.btn_4_11_parar.config(image=self.img_stop_lime)
                    #self.btn_4_11_pausar.config(state="normal", image=self.img_pausar)
                    #self.btn_4_11_continuar.config(state="disabled", image=self.img_continue)
                    self.btn_4_11_enviar.config(state="normal", bg="#9EE8BE")
                    self.btn_4_11_incluir.config(state="normal", bg="#9EE8BE")
                    #self.btn_4_11_montar_pp.config(state="normal", bg="#9EE8BE")
                    self.btn_4_11_salvar.config(state="normal", bg="#9EE8BE")
                    self.btn_4_11_abrir.config(state="normal", bg="#9EE8BE")
                    self.btn_4_11_deletarTab.config(state="normal", bg="#9EE8BE")

                    if self.tree.get_children():
                        self.btn_4_11_incluir.config(state="normal", bg="#9EE8BE")
                        self.btn_4_11_excluir.config(state="normal", bg="#9EE8BE")
                        self.btn_4_11_editar.config(state="normal", bg="#9EE8BE")
                        self.btn_4_11_deletar.config(state="normal", bg="#9EE8BE")
                        self.btn_4_11_montar.config(state="normal", bg="#9EE8BE")

                self.iec411_tab.after(0, _fim_ui)
                self.app.montar = False
                self.app.prmt_4_11 = False
                self.app.pause_uni = False
                self.app.pause_seq = False
                self.cont = 0
                self.i_atual = 0
                self.envia_v2("0")

        # 6) Disparar finalizador
        threading.Thread(target=_finalizar_serial_e_ui, daemon=True).start()

    def parar_seq_4_11(self, por_tempo: bool = False):

        

        # 5) Thread auxiliar que finaliza serial + envia AS
        def _finalizar_serial_e_ui():

            #print("=== THREAD FINALIZADORA INICIOU ===")
            self.cont_total = 0
            try:
                # Reabre porta só para enviar AS:
                try:
                    self._abrir_porta_once()
                    time.sleep(0.1)
                except Exception as e:
                    print(f"Falha ao reabrir porta para enviar AS: {e}")

                if self._ser and self._ser.is_open:
                    try:
                        cmd = self.app.conexao.comando("AS;")
                        #print(f"ENVIANDO AS -> {cmd}")
                        self._ser.write(cmd)
                        self._ser.flush()
                        time.sleep(0.2)
                    except Exception as e:
                        print(f"ERRO AO ENVIAR AS: {e}")

                # Fecha porta
                try:
                    #print("Fechando porta após enviar AS...")
                    self._ser.close()
                except:
                    pass

            finally:
                def _fim_ui():
                    self.text_result_4_11.delete("1.0", tk.END)
                    self.text_result_4_11.insert(tk.END, "Ensaio parado!" if not por_tempo else "Ensaio finalizado!", "Sucesso")
                    self.parar_tempo_4_11()
                    

                    #self.cont = 0

                    self.btn_4_11_iniciar.config(image=self.img_play, state="normal")
                    self.btn_4_11_parar.config(image=self.img_stop_lime)
                    #self.btn_4_11_pausar.config(state="normal", image=self.img_pausar)
                    #self.btn_4_11_continuar.config(state="disabled", image=self.img_continue)
                    self.btn_4_11_enviar.config(state="normal", bg="#9EE8BE")
                    self.btn_4_11_incluir.config(state="normal", bg="#9EE8BE")
                    #self.btn_4_11_montar_pp.config(state="normal", bg="#9EE8BE")
                    self.btn_4_11_salvar.config(state="normal", bg="#9EE8BE")
                    self.btn_4_11_abrir.config(state="normal", bg="#9EE8BE")
                    self.btn_4_11_deletarTab.config(state="normal", bg="#9EE8BE")

                    if self.tree.get_children():
                        self.btn_4_11_incluir.config(state="normal", bg="#9EE8BE")
                        self.btn_4_11_excluir.config(state="normal", bg="#9EE8BE")
                        self.btn_4_11_editar.config(state="normal", bg="#9EE8BE")
                        self.btn_4_11_deletar.config(state="normal", bg="#9EE8BE")
                        self.btn_4_11_montar.config(state="normal", bg="#9EE8BE")

                self.iec411_tab.after(0, _fim_ui)
                self.app.montar = True
                self.app.prmt_4_11 = False
                self.app.pause_uni = False
                self.app.pause_seq = True
                

        # 6) Disparar finalizador
        threading.Thread(target=_finalizar_serial_e_ui, daemon=True).start()


    def pausar_seq_4_11(self):
        if self.app.pause_seq is True:
            self.app.montar = True
            self.app.prmt_4_11 = False
        elif self.app.pause_uni is True:
            self.app.montar = False
            self.app.prmt_4_11 = True

        # 1) Cancelar afters (timer e consumo)
        if getattr(self, "after_timer_id", None):
            try:
                self.iec411_tab.after_cancel(self.after_timer_id)
            except Exception:
                pass
            self.after_timer_id = None

        if getattr(self, "after_consume_id", None):
            try:
                self.iec411_tab.after_cancel(self.after_consume_id)
            except Exception:
                pass
            self.after_consume_id = None

        # 2) Sinalizar thread de leitura para parar e aguardar saída
        try:
            if self._stop_serial_4_11:
                self._stop_serial_4_11.set()
        except Exception:
            pass

        try:
            if self._reader_4_11 and self._reader_4_11.is_alive():
                self._reader_4_11.join(timeout=1.0)  # espera curta
        except Exception:
            pass
        finally:
            self._reader_4_11 = None

        # 3) Enviar "AS;" pela MESMA porta (se aberta) sem travar a UI, e fechar
        def _finalizar_serial_e_ui():
            try:
                if getattr(self, "_ser", None) and self._ser.is_open:
                    # write_timeout curto para evitar travar
                    try:
                        self._ser.write_timeout = min(float(self._ser.write_timeout or 0.5), 0.5)
                    except Exception:
                        pass
                    # Tenta enviar 'AS;' (se falhar, apenas loga)
                    try:
                        self._ser.write(self.app.conexao.comando('AS;'))
                        time.sleep(0.2)  # estamos em thread auxiliar, ok aguardar um pouco
                    except Exception as exw:
                        print(f"Falha ao enviar 'AS;': {exw}")

                # Fecha a porta com segurança
                try:
                    self._fechar_porta()
                except Exception as exf:
                    print(f"Erro ao fechar porta: {exf}")

            finally:
                # 4) Atualiza UI de volta na thread do Tkinter
                def _fim_ui():
                    self.text_result_4_11.delete("1.0", tk.END)
                    self.text_result_4_11.insert(tk.END, "Aguarde!", "Atenção")
                    self.text_result_4_11.update_idletasks()
                    
                self.iec411_tab.after(0, _fim_ui)

        # Se o gerador estiver desconectado e isso for um "parar por tempo", finalize silenciosamente
        if not self.app.ucs_bool:
            messagebox.showwarning("Aviso", "Gerador desconectado!\nVerifique conexão serial.")
            # Mesmo assim tente fechar a porta, se existir
            try:
                self._fechar_porta()
            except Exception:
                pass
            return

        # Dispare o finalizador em thread para não travar a UI
        threading.Thread(target=_finalizar_serial_e_ui, daemon=True).start()


    def pausar_4_11(self):
        if self.app.pause_seq is True:
            self.app.montar = True
            self.app.prmt_4_11 = False
        elif self.app.pause_uni is True:
            self.app.montar = False
            self.app.prmt_4_11 = True

        # 1) Cancelar afters (timer e consumo)
        if getattr(self, "after_timer_id", None):
            try:
                self.iec411_tab.after_cancel(self.after_timer_id)
            except Exception:
                pass
            self.after_timer_id = None

        if getattr(self, "after_consume_id", None):
            try:
                self.iec411_tab.after_cancel(self.after_consume_id)
            except Exception:
                pass
            self.after_consume_id = None

        # 2) Sinalizar thread de leitura para parar e aguardar saída
        try:
            if self._stop_serial_4_11:
                self._stop_serial_4_11.set()
        except Exception:
            pass

        try:
            if self._reader_4_11 and self._reader_4_11.is_alive():
                self._reader_4_11.join(timeout=1)  # espera curta
        except Exception:
            pass
        finally:
            self._reader_4_11 = None

        # 3) Enviar "AS;" pela MESMA porta (se aberta) sem travar a UI, e fechar
        def _finalizar_serial_e_ui():
            try:
                if getattr(self, "_ser", None) and self._ser.is_open:
                    # write_timeout curto para evitar travar
                    try:
                        self._ser.write_timeout = min(float(self._ser.write_timeout or 0.5), 0.5)
                    except Exception:
                        pass
                    # Tenta enviar 'AS;' (se falhar, apenas loga)
                    try:
                        self._ser.write(self.app.conexao.comando('AS;'))
                        #time.sleep(0.2)  # estamos em thread auxiliar, ok aguardar um pouco
                    except Exception as exw:
                        print(f"Falha ao enviar 'AS;': {exw}")

                # Fecha a porta com segurança
                try:
                    self._fechar_porta()
                except Exception as exf:
                    print(f"Erro ao fechar porta: {exf}")

            finally:
                # 4) Atualiza UI de volta na thread do Tkinter
                def _fim_ui():
                    self.text_result_4_11.delete("1.0", tk.END)
                    self.text_result_4_11.insert(tk.END, "Ensaio pausado!")
                    self.pausar_tempo_4_11()

                    self.btn_4_11_iniciar.config(image=self.img_play)
                    self.btn_4_11_parar.config(image=self.img_stop)
                    #self.btn_4_11_pausar.config(image=self.img_pausar_lime, state="normal")
                    #self.btn_4_11_continuar.config(state="normal", image=self.img_continue)
                    self.btn_4_11_iniciar.config(state="disabled")
                self.iec411_tab.after(0, _fim_ui)

        # Se o gerador estiver desconectado e isso for um "parar por tempo", finalize silenciosamente
        if not self.app.ucs_bool:
            messagebox.showwarning("Aviso", "Gerador desconectado!\nVerifique conexão serial.")
            # Mesmo assim tente fechar a porta, se existir
            try:
                self._fechar_porta()
            except Exception:
                pass
            return

        # Dispare o finalizador em thread para não travar a UI
        threading.Thread(target=_finalizar_serial_e_ui, daemon=True).start()

    def continuar_4_11(self):
        if self.app.ucs_bool is not True:
            messagebox.showwarning("Aviso", "Gerador desconectado!\nVerifique conexão serial.")
            return

        # --- CASO 1: aplicação única ---
        if self.app.montar is False and self.app.prmt_4_11 is True:
            try:
                config = self._capturar_config_serial()

                # (Opcional) Atualizações rápidas de UI antes de enviar, para dar feedback imediato
                self.text_result_4_11.delete("1.0", tk.END)
                self.text_result_4_11.insert(tk.END, "Enviando comando para o gerador...")

                # Dispara worker (não congela a UI)
                threading.Thread(target=self._worker_enviar_AW_4_11, args=(config, "uni"), daemon=True).start()
                #self.btn_4_11_continuar.config(image=self.img_continue_lime)
                #self.btn_4_11_pausar.config(image=self.img_pausar, state="normal")

            except Exception as e:
                return f"Erro: {e}"

            return

        # --- CASO 2: aplicação sequencial ---
        if self.app.montar is True and self.app.prmt_4_11 is False:
            try:
                config = self._capturar_config_serial()

                # (Opcional) Atualizações rápidas de UI antes de enviar, para dar feedback imediato
                self.text_result_4_11.delete("1.0", tk.END)
                self.text_result_4_11.insert(tk.END, "Enviando comando para o gerador...")

                # Dispara worker (não congela a UI)
                threading.Thread(target=self._worker_enviar_AW_4_11, args=(config, "seq"), daemon=True).start()
                #self.btn_4_11_continuar.config(image=self.img_continue_lime)
                #self.btn_4_11_pausar.config(image=self.img_pausar, state="normal")

            except Exception as e:
                return f"Erro: {e}"

            return

    def _worker_enviar_AW_4_11(self, config, modo):
        """
        Roda fora da UI thread.
        modo: "uni" ou "seq"
        """
        try:
            with serial.Serial(**config) as s:
                s.write(self.app.conexao.comando('AW;'))
                #time.sleep(1)

        except Exception as e:
            # volta pro Tkinter para mostrar erro (UI)
            self.text_result_4_11.after(0, lambda: messagebox.showwarning("Erro", f"Falha na serial: {e}"))
            return

        # Ao terminar o envio com sucesso, voltar para UI thread
        self.text_result_4_11.after(0, lambda: self._apos_enviar_AW_4_11(modo))

    def _apos_enviar_AW_4_11(self, modo):
        """
        Roda na UI thread depois que o comando AW; foi enviado e o worker terminou.
        """
        # (Re)inicia/organiza contador (sem bloquear)
        self.pausar_tempo_4_11()
        self.retomar_tempo_4_11()
        

        # UI comum aos dois modos
        self.btn_4_11_iniciar.config(image=self.img_play_lime)
        self.btn_4_11_iniciar.config(state="disabled")
        self.btn_4_11_incluir.config(state="disabled", bg="#B0B0B0")
        self.btn_4_11_excluir.config(state="disabled", bg="#B0B0B0")
        self.btn_4_11_deletar.config(state="disabled", bg="#B0B0B0")
        self.btn_4_11_montar.config(state="disabled", bg="#B0B0B0")
        self.btn_4_11_enviar.config(state="disabled", bg="#B0B0B0")
        #self.btn_4_11_montar_pp.config(state="disabled", bg="#B0B0B0")
        self.btn_4_11_editar.config(state="disabled", bg="#B0B0B0")
        self.btn_4_11_abrir.config(state="disabled", bg="#B0B0B0")
        self.btn_4_11_salvar.config(state="disabled", bg="#B0B0B0")
        self.btn_4_11_deletarTab.config(state="disabled", bg="#B0B0B0")
        self.btn_4_11_parar.config(image=self.img_stop)
        #self.btn_4_11_pausar.config(state="normal")
        self.btn_4_11_iniciar.config(image=self.img_play)

        # Agora separa a lógica de cada modo
        if modo == "uni":
            self.app.prmt_4_11 = True
            self.app.pause_uni = True
            self.app.pause_seq = False
            self.app.montar = False
            self.verificar_tempo_4_11()

            t_total = self.tempo_total_uni_4_11()
            horas = t_total // 3600
            minutos = (t_total % 3600) // 60
            segundos = t_total % 60

            t_intervalo = int(self.combo_tempo_4_11.get())
            horas_i = t_intervalo // 3600
            minutos_i = (t_intervalo % 3600) // 60
            segundos_i = t_intervalo % 60

            self.text_result_4_11.delete("1.0", tk.END)
            self.text_result_4_11.insert(tk.END, f"Aplicação retomada! \nA estimativa de duração total é de {horas:02}:{minutos:02}:{segundos:02}")
            self.label_tempo_parcial.config(text=f"{horas_i:02}:{minutos_i:02}:{segundos_i:02}") 
            return

        if modo == "seq":
            #self.intervalo_seq = (int(self.busca_item_4_11(0, 6)) * 1000) #- 1000
            self.app.prmt_4_11 = False
            self.app.pause_uni = False
            self.app.pause_seq = True
            self.app.montar = True
            self.verificar_tempo_4_11()

            #self.iec411_tab.after(0, lambda: self.proximo_4_11(self.i_atual))

            #self.iniciar_seq_tempo_4_11()
            #self.verificar_seq_tempo_4_11()

            #self.app.pause_seq = True

            t_total = self.tempo_total_4_11()
            horas = t_total // 3600
            minutos = (t_total % 3600) // 60
            segundos = t_total % 60

            self.text_result_4_11.delete("1.0", tk.END)
            self.text_result_4_11.insert(tk.END, f"Aplicação sequencial iniciada! \nA estimativa de duração total é de {horas:02}:{minutos:02}:{segundos:02}")
            return 
    
   

    def adicionar_item_4_11(self):
        if self.combo_seq_freq_4_11.get() == "5" and self.combo_seq_duracao_4_11.get() == "0.8":
            self.combo_seq_duracao_4_11.set("15")
            messagebox.showwarning("Aviso", "Atenção!\n* Para a frequência de 5 KHz, a duração deve ser de 15 ms.\n* Para a frequência de 100 kHz, a duração deve ser de 0,8 ms.")
        elif self.combo_seq_freq_4_11.get() == "100" and self.combo_seq_duracao_4_11.get() == "15":
            self.combo_seq_duracao_4_11.set("0.8")
            messagebox.showwarning("Aviso", "Atenção!\n* Para a frequência de 5 KHz, a duração deve ser de 15 ms.\n* Para a frequência de 100 kHz, a duração deve ser de 0,8 ms.")
        else:
            self.combo_seq_duracao_4_11 = self.combo_seq_duracao_4_11
            self.combo_seq_freq_4_11 = self.combo_seq_freq_4_11
            
        acoplamento = self.combo_seq_n_ciclos_4_11.get().strip()
        amplitude = self.combo_seq_tensao_4_11.get().strip()
        duracao = self.combo_seq_duracao_4_11.get().strip()
        pol = self.combo_seq_canal_4_11.get().strip()
        freq = self.combo_seq_freq_4_11.get().strip()
        repeticao = self.combo_seq_repeticao_4_11.get().strip()
        tempo = self.combo_seq_tempo_4_11.get().strip()
        if acoplamento and amplitude and duracao and pol and freq and repeticao and tempo:
            self.tree.insert("", tk.END, values=(acoplamento, amplitude, pol, duracao, repeticao, freq, tempo))
            #item_id = self.tree.insert("", tk.END, values=(acoplamento, amplitude, pol, duracao, repeticao, freq, tempo))
            #self.tree.set(item_id, "ID", item_id)
            self.tempo_total_4_11()
            self.btn_4_11_excluir.config(state="normal", bg="#9EE8BE")
            self.btn_4_11_deletar.config(state="normal", bg="#9EE8BE")
            self.btn_4_11_montar.config(state="normal", bg="#9EE8BE")
            self.btn_4_11_salvar.config(state="normal", bg="#9EE8BE")
            self.btn_4_11_deletarTab.config(state="normal", bg="#9EE8BE")
            self.btn_4_11_editar.config(state="normal", bg="#9EE8BE")
        else:
            messagebox.showwarning("Aviso", "Erro no preenchimento dos dados!")
        itens = self.tree.get_children()
        if itens:
            self.combo_seq_tempo_4_11.config(state="disabled")
        else:
            self.combo_seq_tempo_4_11.config(state="normal")
            
    def deletar_item_4_11(self):
        selecionados = self.tree.selection()
        self.text_result_4_11.delete("1.0", tk.END)
        if selecionados:
            # Apaga os itens selecionados
            for item_id in selecionados:
                self.tree.delete(item_id)

            # Limpa o texto associado
            self.text_result_4_11.delete("1.0", tk.END)

            if len(self.tree.get_children()) < 2:
                self.combo_seq_tempo_4_11.config(state="normal")

            # Agora verifica se a Treeview ficou vazia
            if  len(self.tree.get_children()) < 1:
                # Desabilita e pinta os botões
                self.btn_4_11_excluir.config(state="disabled", bg="#B0B0B0")
                self.btn_4_11_deletar.config(state="disabled", bg="#B0B0B0")
                self.btn_4_11_montar.config(state="disabled", bg="#B0B0B0")
                #self.btn_4_11_montar_pp.config(state="normal", bg="#9EE8BE")
                self.btn_4_11_editar.config(state="disabled", bg="#B0B0B0")
                self.btn_4_11_enviar.config(state="normal", bg="#9EE8BE")
                #self.btn_4_11_salvar.config(state="disabled", bg="red")
                #self.btn_4_11_deletarTab.config(state="disabled", bg="red")
        else:
            messagebox.showwarning("Aviso", "Nenhuma linha selecionada!")        

    def limpar_treeview(self):
        itens = self.tree.get_children()
        self.text_result_4_11.delete("1.0", tk.END)
        for item in itens:
            self.tree.delete(item)
        self.combo_seq_tempo_4_11.config(state="normal")
        self.btn_4_11_excluir.config(state="disabled", bg="#B0B0B0")
        self.btn_4_11_deletar.config(state="disabled", bg="#B0B0B0")
        self.btn_4_11_montar.config(state="disabled", bg="#B0B0B0")
        self.btn_4_11_editar.config(state="disabled", bg="#B0B0B0")
        self.btn_4_11_enviar.config(state="normal", bg="#9EE8BE")
        #self.btn_4_11_montar_pp.config(state="normal", bg="#9EE8BE")
                    
    def remover_item_4_11(self):
        selecionados = self.tree.selection()
        self.text_result_4_11.delete("1.0", tk.END)
        if selecionados:
            item_id = selecionados[0]  # Pega o primeiro selecionado
            valores = self.tree.item(item_id, "values")  # Tupla com os valores da linha
            self.combo_seq_n_ciclos_4_11.set(valores[0])
            self.combo_seq_tensao_4_11.set(valores[1])
            self.combo_seq_canal_4_11.set(valores[2])
            self.combo_seq_duracao_4_11.set(valores[3])
            self.combo_seq_repeticao_4_11.set(valores[4])
            self.combo_seq_freq_4_11.set(valores[5])
            self.combo_seq_tempo_4_11.set(valores[6])

            # Remove a linha do Treeview
            self.tree.delete(item_id)

            if len(self.tree.get_children()) < 2:
                self.combo_seq_tempo_4_11.config(state="normal")

            if  len(self.tree.get_children()) < 1:
                # Desabilita e pinta os botões
                self.btn_4_11_excluir.config(state="disabled", bg="#B0B0B0")
                self.btn_4_11_deletar.config(state="disabled", bg="#B0B0B0")
                self.btn_4_11_montar.config(state="disabled", bg="#B0B0B0")
                #self.btn_4_11_montar_pp.config(state="normal", bg="#9EE8BE")
                self.btn_4_11_editar.config(state="disabled", bg="#B0B0B0")
                self.btn_4_11_enviar.config(state="normal", bg="#9EE8BE")
                #self.btn_4_11_salvar.config(state="disabled", bg="red")
                #self.btn_4_11_deletarTab.config(state="disabled", bg="red")
        else:
            messagebox.showwarning("Aviso", "Nenhuma linha selecionada!")

    def editar_item_4_11(self):
        selecionados = self.tree.selection()
        self.text_result_4_11.delete("1.0", tk.END)
        if selecionados:
            acoplamento = self.combo_seq_n_ciclos_4_11.get().strip()
            amplitude = self.combo_seq_tensao_4_11.get().strip()
            duracao = self.combo_seq_duracao_4_11.get().strip()
            pol = self.combo_seq_canal_4_11.get().strip()
            freq = self.combo_seq_freq_4_11.get().strip()
            repeticao = self.combo_seq_repeticao_4_11.get().strip()
            tempo = self.combo_seq_tempo_4_11.get().strip()
            if acoplamento and amplitude and duracao and pol and freq and repeticao and tempo:
                item_id = selecionados[0]
                self.tree.item(item_id, values=(acoplamento, amplitude, pol, duracao, repeticao, freq, tempo))
        else:
            messagebox.showwarning("Aviso", "Nenhuma linha selecionada!")        

    def busca_item_4_11(self, id, coluna):    
        item_id = self.tree.get_children()[id]
        valores = self.tree.item(item_id, "values")
        valor = valores[coluna]
        #print(type(valor))
        return valor

    def tempo_total_uni_4_11(self):
        soma = 0
        if int(self.combo_repeticao_4_11.get()) > 1:
            soma = (int(self.combo_tempo_4_11.get())+int(self.calcula_duracao()/100000)) * (int(self.combo_repeticao_4_11.get()) - 1) + int(self.calcula_duracao()/100000)
        else:
            soma = 10
        return soma
            
    def tempo_total_4_11(self):
        soma = 0
        total = 0
        itens = self.tree.get_children()  # Lista de IDs
        intervalo = int(self.busca_item_4_11(0, 6))
        n_impulsos = self.impulsos_totais()
        total = ((n_impulsos) * (intervalo + int(self.calcula_duracao_seq(self.busca_item_4_11(0, 0))/100000) + 4)) - intervalo
                
        return total

    def impulsos_totais(self):
        soma = 0
        itens = self.tree.get_children()
        for i in range(len(itens)):
            n_impulsos = int(self.busca_item_4_11(i, 4))
            soma += n_impulsos
        return soma
        
    def proximo_4_11(self, i):
        
        itens = self.tree.get_children()
        self.app.montar = True
        for j in range(len(itens)):
            item_id = itens[j]
            self.tree.item(item_id, tags=("default",))
            if j == i:
                self.tree.item(item_id, tags=("destaque",))
                self.tree.see(item_id)
        #time.sleep(10)

        if i >= len(itens):
            print("Parou no próximo_4_11!")
            self.parar_4_11()
            self.text_result_4_11.delete("1.0", tk.END)
            self.text_result_4_11.insert(tk.END, f"Ensaio finalizado!", "Sucesso")
            #self.salvar_dados_csv()
            return  # terminou todos os itens

        else:
                
            string = "PN,"
            
            #Adiciona o angulo de sincronismo
            string += self.busca_item_4_11(i, 3)+","

            #Adiciona o n° de ciclos
            if self.busca_item_4_11(i, 0) == "0,5":
                var0 = "0,5"
            elif self.busca_item_4_11(i, 0) == "1":
                var0 = "1"
            elif self.busca_item_4_11(i, 0) == "10":
                var0 = "10"
            elif self.busca_item_4_11(i, 0) == "12":
                var0 = "12"
            elif self.busca_item_4_11(i, 0) == "25":
                var0 = "25"
            elif self.busca_item_4_11(i, 0) == "30":
                var0 = "30"
            elif self.busca_item_4_11(i, 0) == "250":
                var0 = "250"
            elif self.busca_item_4_11(i, 0) == "300":
                var0 = "300"
            else:
                messagebox.showwarning("Aviso", "N° de ciclos incorreto!")
            duracao = str(self.calcula_duracao_seq(var0))
            string += duracao+","

            #Adiciona o intervalo
            intervalo_4_11_seq = int(self.busca_item_4_11(i, 6))*100
            string += str(intervalo_4_11_seq)+","

            #Adiciona o canal
            if self.busca_item_4_11(i, 2) == "PF1":
                send_canal_4_11 = "0"
            elif self.busca_item_4_11(i, 2) == "PF2":
                send_canal_4_11 = "1"
            elif self.busca_item_4_11(i, 2) == "ΔU":
                send_canal_4_11 = "2"
            else:
                print("Canal incorreto!")
            string += send_canal_4_11+","

            #Adiciona o valor da tensão de queda. Neste caso, como o gerador não recebe este dado, fica sempre = 0
            #Quem recebe o valor de V2 é o microcontrolador, que envia a tensão (0 V a 10 V) diretamente para o variac
            send_nivel_ajustado_4_11 = str(self.calcula_nivel(self.busca_item_4_11(i, 1)))
            
            string += "0,"

            #Adiciona o trigger
            if self.busca_item_4_11(i, 5) == "AUTO":
                send_trigger_4_11 = "0"
            elif self.busca_item_4_11(i, 5) == "MANUAL":
                send_trigger_4_11 = "1"
            else:
                print("Trigger incorreto!")
            string += send_trigger_4_11+","

            #Adiciona o n° de repetições
            string += self.busca_item_4_11(i, 4)+";"
            print(string)
            
            delay = intervalo_4_11_seq*10

            self.iec411_tab.after(delay, lambda: self._executar_envio(string, send_nivel_ajustado_4_11))
            return


    def _executar_envio(self, string, nivel_v):
        if not self.app.montar:
            print("Aplicação interrompida!")
            return

        #self.retomar_tempo_4_11()
        self.envia_v2(nivel_v)

        try:
            cfg = self._capturar_config_serial()
            self._ser = serial.Serial(**cfg)

            # Aguarda 2 segundos
            self.iec411_tab.after(
                2000,
                lambda: self._enviar_comando_principal(string)
            )

        except Exception as e:
            print(f"Erro: {e}")

    def _enviar_comando_principal(self, string):
        try:
            self._ser.write(self.app.conexao.comando(string))

            # Aguarda 3 segundos
            self.iec411_tab.after(3000, self._enviar_aa)

        except Exception as e:
            print(f"Erro: {e}")

    def _enviar_aa(self):
        try:
            self._ser.write(self.app.conexao.comando('AA;'))

            # Aguarda 1 segundo
            self.iec411_tab.after(1000, self._finalizar_envio)

        except Exception as e:
            print(f"Erro: {e}")

    def _finalizar_envio(self):
        try:
            self._ser.close()

            self.parar_leitura_4_11()

            t_total = self.tempo_total_4_11()
            horas = t_total // 3600
            minutos = (t_total % 3600) // 60
            segundos = t_total % 60

            self.text_result_4_11.delete("1.0", tk.END)
            self.text_result_4_11.insert(
                tk.END,
                "Parâmetros enviados!\n",
                "Sucesso"
            )

            self.text_result_4_11.insert(
                tk.END,
                f"Duração estimada: {horas:02}:{minutos:02}:{segundos:02}",
                "Normal"
            )

            self.verificar_tempo_4_11()

        except Exception as e:
            print(f"Erro: {e}")

    """def _executar_envio(self, string, nivel_v):
        if self.app.montar is True:
            self.retomar_tempo_4_11()
            self.envia_v2(nivel_v)
            try:
                
                cfg = self._capturar_config_serial()
                self._ser = serial.Serial(**cfg)

                #self._ser.write(self.app.conexao.comando('BS,3;'))
                time.sleep(2)
                self._ser.write(self.app.conexao.comando(string))
                time.sleep(3)
                self._ser.write(self.app.conexao.comando('AA;'))
                time.sleep(1)

                self._ser.close()

                self.parar_leitura_4_11()

                t_total = self.tempo_total_4_11()
                horas = t_total // 3600
                minutos = (t_total % 3600) // 60
                segundos = t_total % 60

                self.text_result_4_11.delete("1.0", tk.END)
                self.text_result_4_11.insert(tk.END, "Parâmetros enviados!\n", "Sucesso")
                self.text_result_4_11.insert(
                    tk.END,
                    f"Duração estimada: {horas:02}:{minutos:02}:{segundos:02}", "Normal"
                )

            except Exception as e:
                print(f"Erro: {e}")

            self.verificar_tempo_4_11()
        else:
            print("Aplicação interrompida!")"""

    def tempo_adicional_4_11(self):
        itens = self.tree.get_children()
        if not itens:
            return 0

        # valores "prev" da primeira linha
        prev = [self.busca_item_4_11(0, j) for j in range(7)]
        t_add = 0

        # percorre a partir da segunda linha
        for i in range(1, len(itens)):
            for j in range(7):
                val = self.busca_item_4_11(i, j)
                if val != prev[j]:
                    t_add += 2
                    prev[j] = val  # atualiza o "prev" para a próxima comparação
            t_add = t_add

        return t_add

    def previa_montar_4_11(self):
        self.montar_4_11()
        self.text_result_4_11.delete("1.0", tk.END)
        self.text_result_4_11.insert(tk.END, f"Aguarde!", "Atenção")
        self.text_result_4_11.insert(tk.END, f"\nCarregando configurações do gerador.", "Normal")
        self.text_result_4_11.update_idletasks()  # força atualizar a tela

    def montar_4_11(self):
        if self.u_nom_var.get() != '':
            t_add = self.tempo_adicional_4_11()
            if not self.tree.get_children():
                messagebox.showwarning("Aviso", "Sequência de testes não preenchida!")
                self.app.montar = False
            else:
                self.app.montar = True
                self.app.prmt_4_11 = False
            
            t_total = self.tempo_total_4_11() #+ t_add

            string = "PN,"
            
            #Adiciona o angulo de sincronismo
            string += self.busca_item_4_11(0, 3)+","

            #Adiciona o n° de ciclos
            if self.busca_item_4_11(0, 0) == "0,5":
                var0 = "0,5"
            elif self.busca_item_4_11(0, 0) == "1":
                var0 = "1"
            elif self.busca_item_4_11(0, 0) == "10":
                var0 = "10"
            elif self.busca_item_4_11(0, 0) == "12":
                var0 = "12"
            elif self.busca_item_4_11(0, 0) == "25":
                var0 = "25"
            elif self.busca_item_4_11(0, 0) == "30":
                var0 = "30"
            elif self.busca_item_4_11(0, 0) == "250":
                var0 = "250"
            elif self.busca_item_4_11(0, 0) == "300":
                var0 = "300"
            else:
                messagebox.showwarning("Aviso", "N° de ciclos incorreto!")
            duracao = str(self.calcula_duracao_seq(var0))
            string += duracao+","

            #Adiciona o intervalo
            intervalo_4_11_seq = int(self.busca_item_4_11(0, 6))*100
            string += str(intervalo_4_11_seq)+","

            #Adiciona o canal
            if self.busca_item_4_11(0, 2) == "PF1":
                send_canal_4_11 = "0"
            elif self.busca_item_4_11(0, 2) == "PF2":
                send_canal_4_11 = "1"
            elif self.busca_item_4_11(0, 2) == "ΔU":
                send_canal_4_11 = "2"
            else:
                print("Canal incorreto!")
            string += send_canal_4_11+","

            #Adiciona o valor da tensão de queda. Neste caso, como o gerador não recebe este dado, fica sempre = 0
            #Quem recebe o valor de V2 é o microcontrolador, que envia a tensão (0 V a 10 V) diretamente para o variac
            send_nivel_ajustado_4_11 = str(self.calcula_nivel(self.busca_item_4_11(0, 1)))
            self.envia_v2(send_nivel_ajustado_4_11)
            string += "0,"

            #Adiciona o trigger
            if self.busca_item_4_11(0, 5) == "AUTO":
                send_trigger_4_11 = "0"
            elif self.busca_item_4_11(0, 5) == "MANUAL":
                send_trigger_4_11 = "1"
            else:
                print("Trigger incorreto!")
            string += send_trigger_4_11+","

            #Adiciona o n° de repetições
            string += self.busca_item_4_11(0, 4)+";"
            print(string)
            
            try:
                cfg = self._capturar_config_serial()
                self._ser = serial.Serial(**cfg)
                # Envia comando
                self._ser.write(self.app.conexao.comando('BS,3;'))
                time.sleep(2)
                self._ser.write(self.app.conexao.comando(string))
                #time.sleep(1)
                self._ser.close()
                #ucs_bool = True
                t_total = self.tempo_total_4_11()
                horas = t_total // 3600
                minutos = (t_total % 3600) // 60
                segundos = t_total % 60
                self.text_result_4_11.delete("1.0", tk.END)
                self.text_result_4_11.insert(tk.END, f"Parâmetros da Aplicação Sequencial enviados! \nClique em 'Iniciar' para começar o ensaio.", "Normal")
                self.text_result_4_11.insert(tk.END, f"\nA estimativa de duração total é de {horas:02}:{minutos:02}:{segundos:02}", "Normal")
                #time.sleep(3)
            except Exception as e:
                return f"Erro: {e}"
        else:
            self.text_result_4_11.delete("1.0", tk.END)
            messagebox.showwarning("Aviso", "Tensão nominal não informada!")

    def zerar_variac(self):
        if self.u_nom_var.get() != '':
            
            string = "PN,0,500,1000,2,0,0,1;"
            print(string)
            
            try:
                cfg = self._capturar_config_serial()
                self._ser = serial.Serial(**cfg)
                # Envia comando
                self._ser.write(self.app.conexao.comando('BS,3;'))
                time.sleep(2)
                self._ser.write(self.app.conexao.comando(string))
                time.sleep(2)
                self._ser.write(self.app.conexao.comando('AA;'))
                time.sleep(3)
                self._ser.write(self.app.conexao.comando('AS;'))
                self._ser.close()
                #ucs_bool = True
                
                #time.sleep(3)
            except Exception as e:
                return f"Erro: {e}"
        else:
            self.text_result_4_11.delete("1.0", tk.END)
            messagebox.showwarning("Aviso", "Tensão nominal não informada!")

    def montar_4_11_pp(self):
        self.limpar_treeview()
        acoplamento = self.modo_n_ciclos_4_11.get()
        amplitude = self.nivel_tensao_4_11.get()
        if amplitude == "1000":
            amplitude_dif = "500"
        if amplitude == "2000":
            amplitude_dif = "1000"
        if amplitude == "4000":
            amplitude_dif = "2000"
        
        if acoplamento == "Com PE" and (amplitude == "1000" or amplitude == "2000" or amplitude == "4000"):
            self.tree.insert("", tk.END, values=("L x PE", amplitude, "+", "0", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("L x PE", amplitude, "-", "0", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("L x PE", amplitude, "+", "90", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("L x PE", amplitude, "-", "90", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("L x PE", amplitude, "+", "180", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("L x PE", amplitude, "-", "180", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("L x PE", amplitude, "+", "270", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("L x PE", amplitude, "-", "270", "5", "AUTO", "60"))

            self.tree.insert("", tk.END, values=("N x PE", amplitude, "+", "0", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("N x PE", amplitude, "-", "0", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("N x PE", amplitude, "+", "90", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("N x PE", amplitude, "-", "90", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("N x PE", amplitude, "+", "180", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("N x PE", amplitude, "-", "180", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("N x PE", amplitude, "+", "270", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("N x PE", amplitude, "-", "270", "5", "AUTO", "60"))

            self.tree.insert("", tk.END, values=("L x N", amplitude_dif, "+", "0", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("L x N", amplitude_dif, "-", "0", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("L x N", amplitude_dif, "+", "90", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("L x N", amplitude_dif, "-", "90", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("L x N", amplitude_dif, "+", "180", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("L x N", amplitude_dif, "-", "180", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("L x N", amplitude_dif, "+", "270", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("L x N", amplitude_dif, "-", "270", "5", "AUTO", "60"))

        elif acoplamento == "Com PE" and (amplitude == "250" or amplitude == "500"):
            self.tree.insert("", tk.END, values=("L x PE", amplitude, "+", "0", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("L x PE", amplitude, "-", "0", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("L x PE", amplitude, "+", "90", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("L x PE", amplitude, "-", "90", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("L x PE", amplitude, "+", "180", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("L x PE", amplitude, "-", "180", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("L x PE", amplitude, "+", "270", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("L x PE", amplitude, "-", "270", "5", "AUTO", "60"))

            self.tree.insert("", tk.END, values=("N x PE", amplitude, "+", "0", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("N x PE", amplitude, "-", "0", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("N x PE", amplitude, "+", "90", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("N x PE", amplitude, "-", "90", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("N x PE", amplitude, "+", "180", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("N x PE", amplitude, "-", "180", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("N x PE", amplitude, "+", "270", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("N x PE", amplitude, "-", "270", "5", "AUTO", "60"))

            self.tree.insert("", tk.END, values=("L x N", amplitude, "+", "0", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("L x N", amplitude, "-", "0", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("L x N", amplitude, "+", "90", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("L x N", amplitude, "-", "90", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("L x N", amplitude, "+", "180", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("L x N", amplitude, "-", "180", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("L x N", amplitude, "+", "270", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("L x N", amplitude, "-", "270", "5", "AUTO", "60"))
            
        elif acoplamento == "Sem PE":
            self.tree.insert("", tk.END, values=("L x N", amplitude, "+", "0", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("L x N", amplitude, "-", "0", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("L x N", amplitude, "+", "90", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("L x N", amplitude, "-", "90", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("L x N", amplitude, "+", "180", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("L x N", amplitude, "-", "180", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("L x N", amplitude, "+", "270", "5", "AUTO", "60"))
            self.tree.insert("", tk.END, values=("L x N", amplitude, "-", "270", "5", "AUTO", "60"))
        else: 
            messagebox.showwarning("Aviso", "Erro na montagem da sequência!")
        self.montar_4_11()
        self.btn_4_11_editar.config(state="normal", bg="#9EE8BE")
        self.btn_4_11_incluir.config(state="normal", bg="#9EE8BE")
        self.btn_4_11_excluir.config(state="normal", bg="#9EE8BE")
        self.btn_4_11_deletar.config(state="normal", bg="#9EE8BE")

    def informacoes_4_11_pp(self):
        messagebox.showwarning("Aviso", "As aplicações pré programadas são definidas com o padrão comum da IEC 61000-4-5, com os seguintes parâmetros:" \
        "\n\n*Tempo de aplicação do ensaio: 1 minuto" \
        "\n*Trigger: AUTO" \
        "\n*N° de repetições: 5" \
        "\n*Amplitude: Segue tabela da IEC 61000-4-5. Para os níveis de 240 V e 500 V, o modo diferencial fica com o mesmo nível de tensão." \
        "\n*Sincronismo: de 0° a 270° (com passos de 90°)." \
        "\n\nPara casos onde estes parâmetros devem ser ajustados, utilize a edição da sequência de ensaios no frame 'Aplicação sequencial'.")

    def salvar_4_11(self):
        itens = self.tree.get_children()
        if itens:
            # abre diálogo para escolher nome/local
            arquivo = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Arquivo texto", "*.txt"), ("Todos os arquivos", "*.*")]
            )
            if not arquivo:  # usuário cancelou
                return

            with open(arquivo, "w", encoding="utf-8") as f:
                for item in self.tree.get_children():
                    valores = self.tree.item(item, "values")
                    linha = ";".join(valores)
                    f.write(linha + "\n")
        else:
            messagebox.showwarning("Aviso", "Sequência não preenchida!")

    def abrir_4_11(self):
        # abre diálogo para escolher arquivo
        arquivo = filedialog.askopenfilename(
            filetypes=[("Arquivo texto", "*.txt"), ("Todos os arquivos", "*.*")]
        )
        if not arquivo:  # usuário cancelou
            return

        # limpa Treeview antes de carregar
        for item in self.tree.get_children():
            self.tree.delete(item)

        with open(arquivo, "r", encoding="utf-8") as f:
            for linha in f:
                valores = linha.strip().split(";")
                self.tree.insert("", "end", values=valores)
            if  len(self.tree.get_children()) < 1:
                # Desabilita e pinta os botões
                self.btn_4_11_excluir.config(state="disabled", bg="#B0B0B0")
                self.btn_4_11_deletar.config(state="disabled", bg="#B0B0B0")
                self.btn_4_11_montar.config(state="disabled", bg="#B0B0B0")
                self.btn_4_11_editar.config(state="disabled", bg="#B0B0B0")
                #self.btn_4_11_salvar.config(state="disabled", bg="red")
                #self.btn_4_11_deletarTab.config(state="disabled", bg="red")
            else:
                self.btn_4_11_excluir.config(state="normal", bg="#9EE8BE")
                self.btn_4_11_deletar.config(state="normal", bg="#9EE8BE")
                self.btn_4_11_montar.config(state="normal", bg="#9EE8BE")
                self.btn_4_11_editar.config(state="normal", bg="#9EE8BE")
                #self.btn_4_11_salvar.config(state="normal", bg="lime")
                #self.btn_4_11_deletarTab.config(state="normal", bg="lime")
                t_add = self.tempo_adicional_4_11()
                t_total = self.tempo_total_4_11()# + t_add

                horas = t_total // 3600           
                minutos = (t_total % 3600) // 60            
                segundos = t_total % 60            
            
                self.text_result_4_11.delete("1.0", tk.END)
                self.text_result_4_11.insert(tk.END, f"Arquivo {arquivo} aberto! \nA estimativa de duração é de {horas:02}:{minutos:02}:{segundos:02}\nClique em 'Montar' para preparar o ensaio.", "Normal")
        
        
    def atualizar_tempo_4_11(self):
        if self.rodando:
            agora = time.time()
            self.tempo_decorrido = agora - self.tempo_inicial
            horas = int(self.tempo_decorrido // 3600)            
            minutos = int((self.tempo_decorrido % 3600) // 60)            
            segundos = int(self.tempo_decorrido % 60)            
            self.label_tempo_decorrido.config(text=f"{horas:02}:{minutos:02}:{segundos:02}")            
            self.iec411_tab.after(1000, lambda:self.atualizar_tempo_4_11())

    def atualizar_seq_tempo_4_11(self):
        if self.rodando_seq:
            agora = time.time()            
            self.tempo_seq_decorrido = agora - self.tempo_seq_inicial           
            horas_seq = int(float(self.busca_item_4_11(0, 6)) // 3600)            
            minutos_seq = int((float(self.busca_item_4_11(0, 6)) % 3600) // 60)           
            segundos_seq = int(float(self.busca_item_4_11(0, 6)) % 60)            
            self.label_tempo_parcial.config(text=f"{horas_seq:02}:{minutos_seq:02}:{segundos_seq:02}")
            self.iec411_tab.after(1000, lambda:self.atualizar_seq_tempo_4_11())
            
    def iniciar_tempo_4_11(self):
        if not self.rodando:
            self.tempo_inicial = time.time()
            #self.tempo_seq_inicial = time.time()
            self.rodando = True
            self.atualizar_tempo_4_11()

    def iniciar_seq_tempo_4_11(self):
        if not self.rodando_seq:            
            self.tempo_seq_inicial = time.time()
            self.rodando_seq = True
            self.atualizar_seq_tempo_4_11()
    
    def pausar_tempo_4_11(self):
        if self.rodando:
            self.rodando = False
            self.tempo_decorrido = time.time() - self.tempo_inicial

    def pausar_seq_tempo_4_11(self):
        if self.rodando_seq:
            self.rodando_seq = False
            self.tempo_seq_decorrido = time.time() - self.tempo_seq_inicial
                
    def retomar_tempo_4_11(self):
        if not self.rodando:
            self.tempo_inicial = time.time() - self.tempo_decorrido
            #self.tempo_seq_inicial = time.time() - self.tempo_seq_decorrido
            self.rodando = True
            self.atualizar_tempo_4_11()

    def retomar_seq_tempo_4_11(self):
        if not self.rodando_seq:
            self.tempo_seq_inicial = time.time() - self.tempo_seq_decorrido
            self.rodando_seq = True
            self.atualizar_seq_tempo_4_11()
    
    def parar_tempo_4_11(self):
        self.rodando = False
        self.rodando_seq = False
        self.tempo_decorrido = 0
        self.tempo_seq_decorrido = 0
        self.label_tempo_decorrido.config(text="00:00:00")
        self.label_tempo_parcial.config(text="00:00:00")

    def parar_seq_tempo_4_11(self):
        self.rodando_seq = False
        self.tempo_seq_decorrido = 0
        self.label_tempo_parcial.config(text="00:00:00")

    def _abrir_porta_once(self):
        if self._ser and self._ser.is_open:
            return
        cfg = self._capturar_config_serial()

        # ⚠️ Converter timeout se vier em ms:
        # cfg["timeout"] = float(cfg["timeout"]) / 1000.0
        cfg["timeout"] = min(float(cfg.get("timeout", 1.0)), 0.1)  # 100ms no máximo

        try:
            self._ser = serial.Serial(**cfg)
            self._ser.reset_input_buffer()
        except Exception as e:
            print(f"Erro abrindo porta: {e}")
            self._ser = None

    def _fechar_porta(self):
        try:
            if self._ser and self._ser.is_open:
                self._ser.close()
        except Exception:
            pass
    
    def _leitor_serial_4_11(self):
        buf = bytearray()

        # impede bloqueio eterno
        try:
            if self._ser:
                self._ser.timeout = 0.1
        except:
            pass

        while not self._stop_serial_4_11.is_set():
            try:
                if not (self._ser and self._ser.is_open):
                    self._abrir_porta_once()
                    time.sleep(0.1)
                    continue

                n = self._ser.in_waiting if hasattr(self._ser, "in_waiting") else 0

                if n > 0:
                    chunk = self._ser.read(n)
                    if chunk:
                        buf.extend(chunk)
                        while b"\n" in buf:
                            line, _, buf = buf.partition(b"\n")
                            if line.endswith(b"\r"):
                                line = line[:-1]
                            self._q_serial_4_11.put(line)

                else:
                    # read não bloqueia
                    chunk = self._ser.read(1)
                    if chunk:
                        buf.extend(chunk)
                    time.sleep(0.01)

            except Exception as e:
                self._q_serial_4_11.put(e)
                time.sleep(0.1)

    def _consumir_queue_4_11(self):
        if self.app.prmt_4_11 is False and self.app.montar is True:
            t_total = self.tempo_total_4_11()
            horas = t_total // 3600
            minutos = (t_total % 3600) // 60
            segundos = t_total % 60
        if self.app.prmt_4_11 is True and self.app.montar is False:
            t_total = self.tempo_total_uni_4_11()
            horas = t_total // 3600
            minutos = (t_total % 3600) // 60
            segundos = t_total % 60
        itens = self.tree.get_children()
        try:
            while True:
                item = self._q_serial_4_11.get_nowait()
                if isinstance(item, Exception):
                    print(f"Serial: {item}")
                    continue

                chunk = item.decode("ascii", errors="ignore")
                self._buffer_serial += chunk

                if "cont" in self._buffer_serial.lower():
                    self.cont += 1
                    if self.app.prmt_4_11 is False and self.app.montar is True:
                        if self.cont < (int(self.busca_item_4_11(0, 4)) - 1):
                                            
                            print(f"self.cont = {self.cont}")

                            self._buffer_serial = ""
                        
                        else:
                            self.cont = 0
                            self.cont_total += 1
                            print(f"self.cont = {self.cont}")
                            print(f"self.cont_total = {self.cont_total}")
                            self._buffer_serial = ""
                            #if self.app.prmt_4_11 is False and self.app.montar is True:
                            cont_total_atual = self.cont_total
                            self.dados_medidos.append({"Data/Hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "V nominal": self.u_nom_var.get(),
                                       "Frequencia": self.alimentacao_var.get(), "U%": self.busca_item_4_11(self.cont_total-1, 1),
                                       "Sincronismo": self.busca_item_4_11(self.cont_total-1, 3), "N ciclos": self.busca_item_4_11(self.cont_total-1, 0),
                                  "Intervalo": self.busca_item_4_11(self.cont_total-1, 6), "N repeticoes": self.busca_item_4_11(self.cont_total-1, 4),
                                       "Canal": self.busca_item_4_11(self.cont_total-1, 2), "Trigger": self.busca_item_4_11(self.cont_total-1, 5)})
                            duracao = int(self.calcula_duracao_seq(self.busca_item_4_11(cont_total_atual-1, 0))/100)

                            self.iec411_tab.after(duracao, lambda c=cont_total_atual: self._pausar_e_proximo_4_11(c))

                            #else:
                                #print("IGNORADO")
                    if self.app.prmt_4_11 is True and self.app.montar is False:
                        if self.cont < (int(self.combo_repeticao_4_11.get())-1):
                            print(f"self.cont = {self.cont}")

                            self._buffer_serial = ""
                        else:
                            self.cont = 0
                            self.cont_total += 1
                            print(f"self.cont = {self.cont}")
                            print(f"self.cont_total = {self.cont_total}")
                            self._buffer_serial = ""
                            self.parar_4_11()                            
                
        except queue.Empty:
            pass
        finally:
            self.after_consume_id = self.iec411_tab.after(20, self._consumir_queue_4_11)

    
    def _pausar_e_proximo_4_11(self, cont_total):
        self.pausar_seq_4_11()
        self.proximo_4_11(cont_total)

        
    def iniciar_leitura_4_11(self):
        if self._reader_4_11 and self._reader_4_11.is_alive():
            return
        self._stop_serial_4_11.clear()
        self._reader_4_11 = threading.Thread(target=self._leitor_serial_4_11, daemon=True)
        self._reader_4_11.start()
        self.iec411_tab.after(10, self._consumir_queue_4_11)

    def parar_leitura_4_11(self):
        self._stop_serial_4_11.set()
        self._fechar_porta()

    def verificar_tempo_4_11(self):
        if self.inicio_4_11 is None:
            self.inicio_4_11 = time.monotonic()

        if self.app.prmt_4_11 is True and self.app.montar is False:
            if self.cont_total < 1:
                # Garante thread de leitura e consumidor de fila ativos
                try:
                    # Inicie a leitura se ainda não estiver ativa
                    if not (self._reader_4_11 and self._reader_4_11.is_alive()):
                        # criar estruturas se ainda não existirem
                        if self._q_serial_4_11 is None:
                            self._q_serial_4_11 = queue.Queue()
                        if self._stop_serial_4_11 is None:
                            self._stop_serial_4_11 = threading.Event()
                        else:
                            self._stop_serial_4_11.clear()

                        # inicie a leitura (seu método deve criar e startar o thread)
                        self.iniciar_leitura_4_11()

                    # Garante o consumidor da fila agendado
                    if not getattr(self, "after_consume_id", None):
                        # seu consumidor deve recolocar o after periodicamente
                        self.after_consume_id = self.iec411_tab.after(10, self._consumir_queue_4_11)

                except Exception as ex:
                    # Evite capturar 'ex' dentro da lambda sem congelar a mensagem
                    msg = f"Falha ao iniciar leitura/consumo: {ex}"
                    self.iec411_tab.after(0, lambda m=msg: print(m))

                # Reagende o verificador de tempo e SALVE o ID
                if getattr(self, "after_timer_id", None):
                    try:
                        self.iec411_tab.after_cancel(self.after_timer_id)
                    except Exception:
                        pass
                    self.after_timer_id = None

                self.after_timer_id = self.iec411_tab.after(1000, self.verificar_tempo_4_11)

            else:          
                print("Parou aqui (uni)!")
                self.parar_4_11(por_tempo=True)

                self.envia_v2("0")
                #self.salvar_dados_csv()
                #self.contador = 0

        if self.app.prmt_4_11 is False and self.app.montar is True:
            #print(f"self.cont = {self.cont}")
            itens = self.tree.get_children()
            
            if self.cont_total < len(itens):
               
                try:
                    # Inicie a leitura se ainda não estiver ativa
                    if not (self._reader_4_11 and self._reader_4_11.is_alive()):
                        # criar estruturas se ainda não existirem
                        if self._q_serial_4_11 is None:
                            self._q_serial_4_11 = queue.Queue()
                        if self._stop_serial_4_11 is None:
                            self._stop_serial_4_11 = threading.Event()
                        else:
                            self._stop_serial_4_11.clear()

                        # inicie a leitura (seu método deve criar e startar o thread)
                        self.iniciar_leitura_4_11()

                    # Garante o consumidor da fila agendado
                    if not getattr(self, "after_consume_id", None):
                        # seu consumidor deve recolocar o after periodicamente
                        self.after_consume_id = self.iec411_tab.after(10, self._consumir_queue_4_11)

                except Exception as ex:
                    # Evite capturar 'ex' dentro da lambda sem congelar a mensagem
                    msg = f"Falha ao iniciar leitura/consumo: {ex}"
                    self.iec411_tab.after(0, lambda m=msg: print(m))

                # Reagende o verificador de tempo e SALVE o ID
                if getattr(self, "after_timer_id", None):
                    try:
                        self.iec411_tab.after_cancel(self.after_timer_id)
                    except Exception:
                        pass
                    self.after_timer_id = None

                self.after_timer_id = self.iec411_tab.after(1000, self.verificar_tempo_4_11)


            else:
                # Cancela o timer (se ainda houver) e chama o parar com flag por_tempo
                if getattr(self, "after_timer_id", None):
                    try:
                        self.iec411_tab.after_cancel(self.after_timer_id)
                    except Exception:
                        pass
                    self.after_timer_id = None

                # Para tudo (sem mostrar alerta de desconexão ao usuário por causa do tempo)
                #self.parar_4_11()
                self.cont = 0
                self.cont_total = 0
                #self.salvar_dados_csv()
            
                
    
    def grafico_corrente(self):
        if not self.correntes:
            messagebox.showwarning("Aviso", "Nenhum dado de corrente disponível!")
            return

        # Se já existir uma janela aberta do gráfico → não abrir outra
        if self.graph_window_corrente and tk.Toplevel.winfo_exists(self.graph_window_corrente):
            return

        # Cria janela do gráfico
        self.graph_window_corrente = tk.Toplevel(self.iec411_tab)
        self.graph_window_corrente.title("Gráfico de Corrente em Tempo Real")

        # Adiciona o canvas do matplotlib dentro do Tkinter
        self.canvas_corrente = FigureCanvasTkAgg(self.fig_corrente, master=self.graph_window_corrente)
        self.canvas_corrente.get_tk_widget().pack(fill="both", expand=True)

        # Atualiza o gráfico automaticamente
        self.atualizar_grafico_continuo()

    def grafico_tensao(self):
        if not self.correntes:
            messagebox.showwarning("Aviso", "Nenhum dado de tensao disponível!")
            return

        # Se já existir uma janela aberta do gráfico → não abrir outra
        if self.graph_window_tensao and tk.Toplevel.winfo_exists(self.graph_window_tensao):
            return

        # Cria janela do gráfico
        self.graph_window_tensao = tk.Toplevel(self.iec411_tab)
        self.graph_window_tensao.title("Gráfico da tensão do impulso")

        # Adiciona o canvas do matplotlib dentro do Tkinter
        self.canvas_tensao = FigureCanvasTkAgg(self.fig_tensao, master=self.graph_window_tensao)
        self.canvas_tensao.get_tk_widget().pack(fill="both", expand=True)

        # Atualiza o gráfico automaticamente
        self.atualizar_grafico_continuo_tensao()

    
    def atualizar_grafico_continuo(self):
        if not (self.graph_window_corrente and tk.Toplevel.winfo_exists(self.graph_window_corrente)):
            return  # janela já foi fechada

        # Atualiza o gráfico com os dados atuais
        self._atualizar_plot()

        # Chama novamente após 300 ms
        self.graph_window_corrente.after(300, self.atualizar_grafico_continuo)

    def atualizar_grafico_continuo_tensao(self):
        if not (self.graph_window_tensao and tk.Toplevel.winfo_exists(self.graph_window_tensao)):
            return  # janela já foi fechada

        # Atualiza o gráfico com os dados atuais
        self._atualizar_plot_tensao()

        # Chama novamente após 300 ms
        self.graph_window_tensao.after(300, self.atualizar_grafico_continuo_tensao)

    
    def _atualizar_plot(self):
        if not self.correntes:
            return

        x = list(range(1, len(self.correntes) + 1))
        self.linha_corrente.set_xdata(x)
        self.linha_corrente.set_ydata(self.correntes)

        self.ax_corrente.relim()
        self.ax_corrente.autoscale_view()

        if self.canvas_corrente:
            self.canvas_corrente.draw()

    def _atualizar_plot_tensao(self):
        if not self.tensoes:
            return

        x = list(range(1, len(self.tensoes) + 1))
        self.linha_tensao.set_xdata(x)
        self.linha_tensao.set_ydata(self.tensoes)

        self.ax_tensao.relim()
        self.ax_tensao.autoscale_view()

        if self.canvas_tensao:
            self.canvas_tensao.draw()

    def apagar_graficos(self):
        resposta = messagebox.askyesno(
            "Confirmar",
            "Deseja realmente apagar todos os dados medidos?"
        )

        if resposta:
            self.correntes.clear()
            self.tensoes.clear()
            self.dados_medidos.clear()
            self.linha_corrente.set_xdata([])
            self.linha_corrente.set_ydata([])
            self.linha_tensao.set_xdata([])
            self.linha_tensao.set_ydata([])
            self.ax_corrente.relim()
            self.ax_corrente.autoscale_view()
            self.ax_tensao.relim()
            self.ax_tensao.autoscale_view()
            if self.canvas_corrente:
                self.canvas_corrente.draw()
            if self.canvas_tensao:
                self.canvas_tensao.draw()
            print("Dados apagados.")
        else:
            print("Operação cancelada.")

    def salvar_dados_csv(self):
        # Abre janela para escolha do arquivo
        caminho_arquivo = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("Arquivo CSV", "*.csv")],
            title="Ensaio_61000-4-11"
        )

        if not caminho_arquivo:
            return  # Usuário cancelou

        # Cabeçalhos da tabela
        colunas = ["Data/Hora", "V nominal", "Frequencia", "U%", "Sincronismo", "N ciclos", "Intervalo", "N repeticoes", "Canal", "Trigger"]
        
        try:
            with open(caminho_arquivo, mode="w", newline="", encoding="utf-8") as arquivo_csv:
                writer = csv.DictWriter(arquivo_csv, fieldnames=colunas)
                writer.writeheader()
                writer.writerows(self.dados_medidos)

            print(f"Arquivo salvo: {caminho_arquivo}")

        except Exception as e:
            print(f"Erro ao salvar arquivo: {e}")

    def _on_rr_00_teste_finalizado(self, params, raw):
        self.text_result_4_11.insert(tk.END, "Ensaio finalizado (RR,00).\n")
                
