from tkinter import ttk




import threading
import queue
import serial
import time
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import tkinter as tk
from PIL import Image, ImageTk
from pathlib import Path



class IEC46Tab:

    def __init__(self, parent, app):

        self.parent = parent
        self.app = app

        # SESSÃO SERIAL
        self._ser = None
        self._rx_thread = None
        self._tx_thread = None

        self._tx_queue = queue.Queue()
        self._event_queue = queue.Queue()

        self._stop_evt = threading.Event()
        # HANDLERS CWS
        self._handlers = self._build_handlers()
        self.app = app
        self.iec46_tab = parent
        self.build_ui()



        
    def build_ui(self):
        style = ttk.Style(self.iec46_tab)

        if not style.lookup("Custom.TLabelframe", "background"):
            style.configure(
                "Custom.TLabelframe",
                background="#f0f0f0",
                borderwidth=3,
                relief="groove"
            )

        if not style.lookup("Custom.TLabelframe.Label", "foreground"):
            style.configure(
                "Custom.TLabelframe.Label",
                font=("Arial", 12, "bold"),
                foreground="#003366"
            )


        # FRAME: PARÂMETROS DO ENSAIO
        frame_parametros = ttk.LabelFrame(
            self.iec46_tab,
            text="Parâmetros do ensaio",
            style="Custom.TLabelframe",
            padding=(10, 10)
        )
        frame_parametros.place(x=20, y=20, width=600, height=255)


        # FRAME: CONTROLE
        frame_controle = ttk.LabelFrame(
            self.iec46_tab,
            text="Controle",
            style="Custom.TLabelframe",
            padding=(10, 10)
        )
        frame_controle.place(x=630, y=20, width=250, height=130)

        # FRAME: ESTADO STATUS  
        frame_status = ttk.LabelFrame(
            self.iec46_tab,
            text="Estado",
            style="Custom.TLabelframe",
            padding=(10, 10)
        )
        frame_status.place(x=630, y=160, width=250, height=75)


        # FRAME: LOG
        frame_log = ttk.LabelFrame(
            self.iec46_tab,
            text="Resultado / Log de comunicação",
            style="Custom.TLabelframe",
            padding=(10, 10)
        )
        frame_log.place(x=20, y=290, width=860, height=270)

        # TENSÃO
        tk.Label(
            frame_parametros,
            text="Tensão (V):",
            font=("Arial", 10, "bold"),
            fg="#080069"
        ).place(x=5, y=10)

        self.tensao_var = tk.StringVar(value="")

        # Mantido sem passo definido para não inventar
        # um incremento que ainda não foi especificado.
        self.tensao_step = None

        self.tensao_entry = ttk.Entry(
            frame_parametros,
            textvariable=self.tensao_var,
            width=20
        )
        self.tensao_entry.place(x=150, y=10)

        self.btn_tensao_menos = tk.Button(
            frame_parametros,
            text="-",
            command=lambda: self._ajustar_tensao(-1),
            width=2,
            bg="#9EE8BE"
        )
        self.btn_tensao_menos.place(x=300, y=8)

        self.btn_tensao_mais = tk.Button(
            frame_parametros,
            text="+",
            command=lambda: self._ajustar_tensao(1),
            width=2,
            bg="#9EE8BE"
        )
        self.btn_tensao_mais.place(x=330, y=8)

        self.btn_setar_tensao = tk.Button(
            frame_parametros,
            text="SETAR",
            command=self._setar_tensao_ui,
            width=10,
            bg="#9EE8BE"
        )
        self.btn_setar_tensao.place(x=390, y=7)

        # FREQUÊNCIA: INÍCIO E FINAL
        # Padrão: 150 kHz até 80 MHz
        tk.Label(
            frame_parametros,
            text="Frequência / Range:",
            font=("Arial", 10, "bold"),
            fg="#080069"
        ).place(x=5, y=55)

        self.frequencia_inicio_var = tk.StringVar(value="150 kHz")
        self.frequencia_final_var = tk.StringVar(value="80 MHz")

        tk.Label(
            frame_parametros,
            text="Início:",
            font=("Arial", 9)
        ).place(x=150, y=55)

        self.frequencia_inicio_entry = ttk.Entry(
            frame_parametros,
            textvariable=self.frequencia_inicio_var,
            width=13
        )
        self.frequencia_inicio_entry.place(x=195, y=55)

        tk.Label(
            frame_parametros,
            text="Final:",
            font=("Arial", 9)
        ).place(x=315, y=55)

        self.frequencia_final_entry = ttk.Entry(
            frame_parametros,
            textvariable=self.frequencia_final_var,
            width=13
        )
        self.frequencia_final_entry.place(x=355, y=55)

        # Compatibilidade temporária com trechos antigos que
        # consultem self.frequencia_var.
        # O valor é atualizado quando a faixa é consultada.
        self.frequencia_var = tk.StringVar(
            value="150 kHz - 80 MHz"
        )

        # TD (DWELL TIME)
        tk.Label(
            frame_parametros,
            text="TD (dwell time):",
            font=("Arial", 10, "bold"),
            fg="#080069"
        ).place(x=5, y=100)

        self.td_var = tk.StringVar(value="")

        self.td_entry = ttk.Entry(
            frame_parametros,
            textvariable=self.td_var,
            width=30
        )
        self.td_entry.place(x=150, y=100)


        # COUPLING: BCI, CDN OU CCC
        tk.Label(
            frame_parametros,
            text="Coupling:",
            font=("Arial", 10, "bold"),
            fg="#080069"
        ).place(x=5, y=145)

        self.coupling_var = tk.StringVar(value="BCI")

        self.coupling_combo = ttk.Combobox(
            frame_parametros,
            textvariable=self.coupling_var,
            values=("BCI", "CDN", "CCC"),
            state="readonly",
            width=27
        )
        self.coupling_combo.place(x=150, y=145)

        self.coupling_combo.bind(
            "<<ComboboxSelected>>",
            self.selecionar_coupling
        )

        # MODULAÇÃO: AM OU FM
        tk.Label(
            frame_parametros,
            text="Modulação:",
            font=("Arial", 10, "bold"),
            fg="#080069"
        ).place(x=5, y=190)

        self.modulacao_var = tk.StringVar(value="AM")

        self.modulacao_combo = ttk.Combobox(
            frame_parametros,
            textvariable=self.modulacao_var,
            values=("AM", "FM"),
            state="readonly",
            width=27
        )
        self.modulacao_combo.place(x=150, y=190)

        self.modulacao_combo.bind(
            "<<ComboboxSelected>>",
            self.selecionar_modulacao
        )


        # ÍCONES DOS BOTÕES
        self.img_play = self._carregar_icone("play.png")
        self.img_play_lime = self._carregar_icone("play_lime.png")

        self.img_pause = self._carregar_icone("pause.png")
        self.img_pause_lime = self._carregar_icone("pause_lime.png")

        self.img_continue = self._carregar_icone("continue.png")
        self.img_continue_lime = self._carregar_icone(
            "continue_lime.png"
        )

        self.img_stop = self._carregar_icone("stop.png")
        self.img_stop_lime = self._carregar_icone("stop_lime.png")


        # BOTÕES DE CONTROLE
        # Ordem: PLAY, PAUSE, CONTINUE, STOP
        self.btn_play = self._criar_botao_controle(
            frame_controle,
            "PLAY",
            self.img_play,
            self._play_ui,
            10
        )

        self.btn_pause = self._criar_botao_controle(
            frame_controle,
            "PAUSE",
            self.img_pause,
            self._pause_ui,
            60
        )

        self.btn_continue = self._criar_botao_controle(
            frame_controle,
            "CONTINUE",
            self.img_continue,
            self._continue_ui,
            110
        )

        self.btn_stop = self._criar_botao_controle(
            frame_controle,
            "STOP",
            self.img_stop_lime,
            self._stop_ui,
            160
        )


        # ESTADO DO ENSAIO
        self.label_status = tk.Label(
            frame_status,
            text="Aguardando conexão",
            font=("Arial", 12, "bold"),
            foreground="#003366",
            anchor="w"
        )
        self.label_status.place(x=5, y=5, width=205)


        # LOG DE COMUNICAÇÃO
        self.text_result = tk.Text(
            frame_log,
            bg="#000000",
            fg="#E6E6E6",
            insertbackground="#FFFFFF",
            font=("Consolas", 10),
            wrap="word",
            state="disabled"
        )
        self.text_result.place(
            x=5,
            y=5,
            width=805,
            height=210
        )

        self.text_result.tag_config(
            "INFO",
            foreground="#E6E6E6"
        )
        self.text_result.tag_config(
            "UI",
            foreground="#87CEFA"
        )
        self.text_result.tag_config(
            "STATUS",
            foreground="#9EE8BE"
        )
        self.text_result.tag_config(
            "AVISO",
            foreground="#FFF6BF"
        )

        self.scroll_log = ttk.Scrollbar(
            frame_log,
            orient="vertical",
            command=self.text_result.yview
        )
        self.scroll_log.place(
            x=815,
            y=5,
            height=210
        )

        self.text_result.configure(
            yscrollcommand=self.scroll_log.set
        )


        # ESTADO INICIAL E LOG
        self._atualizar_status_ui("Aguardando conexão")

        self._log_ui(
            "Interface IEC 61000-4-6 inicializada.",
            "INFO"
        )

        self._log_ui(
            "Faixa de frequência padrão: 150 kHz até 80 MHz.",
            "INFO"
        )

        self._log_ui(
            "Coupling inicial: BCI.",
            "INFO"
        )

        self._log_ui(
            "Modulação inicial: AM.",
            "INFO"
        )


    def _carregar_icone(self, nome_arquivo):
        pasta_projeto = Path(__file__).resolve().parents[2]
        candidatos = (
            Path(__file__).resolve().parent / nome_arquivo,
            pasta_projeto / "V20-barbosa" / "v21" / nome_arquivo,
        )
        caminho = next((item for item in candidatos if item.is_file()), None)
        if caminho is None:
            return None

        with Image.open(caminho) as imagem:
            return ImageTk.PhotoImage(imagem.resize((40, 30)))

    def _criar_botao_controle(self, parent, texto, imagem, callback, x):
        opcoes = {
            "command": callback,
            "width": 40,
            "height": 30,
        }
        if imagem is not None:
            opcoes["image"] = imagem
        else:
            opcoes["text"] = texto
            opcoes["width"] = 8
            opcoes["height"] = 2

        botao = tk.Button(parent, **opcoes)
        botao.place(x=x, y=1)
        return botao

    def _log_ui(self, mensagem, nivel="INFO"):
        if nivel not in {"INFO", "UI", "STATUS", "AVISO"}:
            nivel = "INFO"
        self.text_result.configure(state="normal")
        self.text_result.insert(
            tk.END,
            f"[{nivel}] {mensagem}\n",
            nivel
        )
        self.text_result.see(tk.END)
        self.text_result.configure(state="disabled")

    def _atualizar_status_ui(self, mensagem):
        self.label_status.configure(text=mensagem)

    def _ajustar_tensao(self, direcao):
        if self.tensao_step is None:
            self._log_ui(
                "Passo de incremento da tensão ainda não foi configurado.",
                "AVISO"
            )
            return

        try:
            valor = float(self.tensao_var.get())
        except ValueError:
            self._log_ui("Informe uma tensão numérica antes de ajustar.", "AVISO")
            return

        self.tensao_var.set(f"{valor + direcao * self.tensao_step:g}")
        self._log_ui("Campo de tensão ajustado pela interface.", "UI")

    def _setar_tensao_ui(self):
        self._log_ui("Botão SETAR pressionado; nenhum comando foi enviado.", "UI")

    def _play_ui(self):
        self._log_ui("Botão PLAY pressionado; nenhum comando foi enviado.", "UI")

    def _pause_ui(self):
        self._log_ui("Botão PAUSE pressionado; nenhum comando foi enviado.", "UI")

    def _continue_ui(self):
        self._log_ui("Botão CONTINUE pressionado; nenhum comando foi enviado.", "UI")

    def _stop_ui(self):
        self._log_ui("Botão STOP pressionado; nenhum comando foi enviado.", "UI")

    
        
    def selecionar_coupling(self, event=None):
        coupling = self.coupling_var.get()

        self._log_ui(
            f"Coupling selecionado na interface: {coupling}.",
            "UI"
        )


    def selecionar_modulacao(self, event=None):
        modulacao = self.modulacao_var.get()

        self._log_ui(
            f"Modulação selecionada na interface: {modulacao}.",
            "UI"
        )
    
    



        
        
    def _build_handlers(self):
        return {
            "RR,00": self._on_rr_00_test_finished,
            "RR,03": self._on_rr_03_invalid_calibration_memory,
            "RR,04": self._on_rr_04_voltage_out_of_limits,
            "RR,05": self._on_rr_05_fail1_test_interrupted,
            "RR,06": self._on_rr_06_fail2,
            "RR,10": self._on_rr_10_string_error,
            "RR,11": self._on_rr_11_test_not_possible,
            "RR,13": self._on_rr_13_coupling_matrix_error,
            "RR,14": self._on_rr_14_parameter_limited,
            # RR,15 → Erro de checksum — reenviar comando
            "RR,15": self._on_rr_15_checksum_error,
            # RR,19 → Erro de comunicação interna
            "RR,19": self._on_rr_19_internal_communication_error,
            "RR,20": self._on_rr_20_uncorrectable_limiting_error,
            "RR,25": self._on_rr_25_corrupt_calibration_data,
            # RR,31 → Memória BCI inválida
            "RR,31": self._on_rr_31_invalid_bci_memory,
            # RR,32 → Erro relacionado à memória BCI
            "RR,32": self._on_rr_32_bci_error,
        }
        
    def enviar_parametros_cws(self):
        pass

    def iniciar_teste_cws(self):
        pass