"""
Aba IEC 61000-4-6 — CWS 500C.

Integração incremental:
- Não envia CC; a identificação inicial continua fora desta aba.
- Usa os parâmetros seriais configurados na aba Conexão.
- Mantém uma sessão serial persistente própria para TX/RX durante o ensaio.
- O enquadramento usado é o já validado no projeto:
      ASCII(comando) + checksum((-sum(payload)) & 0xFF) + LF

ATENÇÃO AO PROTOCOLO EXPERIMENTAL:
- A frequência enviada por NF é convertida para MHz (ex.: 80 MHz -> 80.000).
- A frequência inicial é mantida na interface para a lógica de varredura/software;
  NF recebe a frequência final.
- O código de coupling 1 é um PALPITE DE TESTE para BCI, não uma confirmação
  do fabricante. Os códigos 0..8 podem ser alterados na interface para investigar.
- AA (iniciar) e AS (parar) vieram do script de terminal do projeto.
- Não foi fornecido comando confirmado de PAUSE/CONTINUE; esses botões registram
  o aviso no log e não transmitem um comando inventado.
"""

import queue
import re
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import serial
from PIL import Image, ImageTk


class IEC46Tab:
    COUPLING_BCI_CODE = 1  # Código experimental para testar a hipótese BCI.

    def __init__(self, parent, app):
        self.parent = parent
        self.iec46_tab = parent
        self.app = app

        self._ser = None
        self._rx_thread = None
        self._tx_thread = None
        self._tx_queue = queue.Queue()
        self._event_queue = queue.Queue()
        self._stop_evt = threading.Event()
        self._session_lock = threading.Lock()
        self._test_running = False
        self._last_tx_command = None
        self._handlers = self._build_handlers()

        self.build_ui()
        self._schedule_event_pump()
        self._log_ui("Aba IEC 61000-4-6 pronta. CC não será enviado por esta aba.")
        self._log_ui("Faixa inicial padrão: 150 kHz; frequência final padrão: 80 MHz.")
        self._log_ui("BCI está associado provisoriamente ao código de coupling 1.")

    # ------------------------------------------------------------------
    # INTERFACE
    # ------------------------------------------------------------------
    def build_ui(self):
        style = ttk.Style(self.iec46_tab)
        if not style.lookup("Custom.TLabelframe", "background"):
            style.configure(
                "Custom.TLabelframe", background="#f0f0f0",
                borderwidth=3, relief="groove"
            )
        if not style.lookup("Custom.TLabelframe.Label", "foreground"):
            style.configure(
                "Custom.TLabelframe.Label",
                font=("Arial", 12, "bold"), foreground="#003366"
            )

        frame_parametros = ttk.LabelFrame(
            self.iec46_tab, text="Parâmetros do ensaio",
            style="Custom.TLabelframe", padding=(10, 10)
        )
        frame_parametros.place(x=20, y=20, width=600, height=255)

        frame_controle = ttk.LabelFrame(
            self.iec46_tab, text="Controle",
            style="Custom.TLabelframe", padding=(10, 10)
        )
        frame_controle.place(x=630, y=20, width=250, height=130)

        frame_status = ttk.LabelFrame(
            self.iec46_tab, text="Estado",
            style="Custom.TLabelframe", padding=(10, 10)
        )
        frame_status.place(x=630, y=160, width=250, height=75)

        frame_log = ttk.LabelFrame(
            self.iec46_tab, text="Resultado / Log de comunicação",
            style="Custom.TLabelframe", padding=(10, 10)
        )
        frame_log.place(x=20, y=290, width=860, height=270)

        # Tensão
        tk.Label(
            frame_parametros, text="Tensão (V):",
            font=("Arial", 10, "bold"), fg="#080069"
        ).place(x=5, y=10)
        self.tensao_var = tk.StringVar(value="")
        self.tensao_step = None  # Não inventar incremento sem especificação.
        self.tensao_entry = ttk.Entry(
            frame_parametros, textvariable=self.tensao_var, width=16
        )
        self.tensao_entry.place(x=150, y=10)
        self.btn_tensao_menos = tk.Button(
            frame_parametros, text="-",
            command=lambda: self._ajustar_tensao(-1), width=2, bg="#9EE8BE"
        )
        self.btn_tensao_menos.place(x=270, y=8)
        self.btn_tensao_mais = tk.Button(
            frame_parametros, text="+",
            command=lambda: self._ajustar_tensao(1), width=2, bg="#9EE8BE"
        )
        self.btn_tensao_mais.place(x=300, y=8)
        self.btn_setar_tensao = tk.Button(
            frame_parametros, text="SETAR",
            command=self._setar_tensao_ui, width=10, bg="#9EE8BE"
        )
        self.btn_setar_tensao.place(x=350, y=7)

        # Faixa de frequência: início é uma referência de software; NF usa o final.
        tk.Label(
            frame_parametros, text="Frequência / Range:",
            font=("Arial", 10, "bold"), fg="#080069"
        ).place(x=5, y=55)
        self.frequencia_inicio_var = tk.StringVar(value="150 kHz")
        self.frequencia_final_var = tk.StringVar(value="80 MHz")
        tk.Label(frame_parametros, text="Início:", font=("Arial", 9)).place(x=150, y=55)
        self.frequencia_inicio_entry = ttk.Entry(
            frame_parametros, textvariable=self.frequencia_inicio_var, width=13
        )
        self.frequencia_inicio_entry.place(x=195, y=55)
        tk.Label(frame_parametros, text="Final:", font=("Arial", 9)).place(x=315, y=55)
        self.frequencia_final_entry = ttk.Entry(
            frame_parametros, textvariable=self.frequencia_final_var, width=13
        )
        self.frequencia_final_entry.place(x=355, y=55)
        self.frequencia_var = tk.StringVar(value="150 kHz - 80 MHz")

        # Dwell time
        tk.Label(
            frame_parametros, text="TD (dwell time):",
            font=("Arial", 10, "bold"), fg="#080069"
        ).place(x=5, y=100)
        self.td_var = tk.StringVar(value="")
        self.td_entry = ttk.Entry(
            frame_parametros, textvariable=self.td_var, width=30
        )
        self.td_entry.place(x=150, y=100)

        # Coupling: código selecionável para testes de identificação.
        tk.Label(
            frame_parametros, text="Coupling:",
            font=("Arial", 10, "bold"), fg="#080069"
        ).place(x=5, y=145)
        self.coupling_var = tk.StringVar(value="BCI")
        self.coupling_combo = ttk.Combobox(
            frame_parametros, textvariable=self.coupling_var,
            values=("BCI", "CDN", "CCC", "OFF"),
            state="readonly", width=12
        )
        self.coupling_combo.place(x=150, y=145)
        self.coupling_combo.bind("<<ComboboxSelected>>", self.selecionar_coupling)

        tk.Label(
            frame_parametros, text="Código 0–8:",
            font=("Arial", 9)
        ).place(x=280, y=145)
        self.coupling_code_var = tk.StringVar(value=str(self.COUPLING_BCI_CODE))
        self.coupling_code_combo = ttk.Combobox(
            frame_parametros, textvariable=self.coupling_code_var,
            values=tuple(str(i) for i in range(9)),
            state="readonly", width=5
        )
        self.coupling_code_combo.place(x=355, y=145)
        self.coupling_code_combo.bind(
            "<<ComboboxSelected>>", self._coupling_code_changed
        )

        # Modulação: preservada como seleção experimental.
        tk.Label(
            frame_parametros, text="Modulação:",
            font=("Arial", 10, "bold"), fg="#080069"
        ).place(x=5, y=190)
        self.modulacao_var = tk.StringVar(value="AM")
        self.modulacao_combo = ttk.Combobox(
            frame_parametros, textvariable=self.modulacao_var,
            values=("AM", "FM"), state="readonly", width=12
        )
        self.modulacao_combo.place(x=150, y=190)
        self.modulacao_combo.bind(
            "<<ComboboxSelected>>", self.selecionar_modulacao
        )

        self.btn_enviar_parametros = tk.Button(
            frame_parametros, text="ENVIAR PARÂMETROS",
            command=self.enviar_parametros_cws, width=20, bg="#9EE8BE"
        )
        self.btn_enviar_parametros.place(x=300, y=188)

        # Ícones opcionais; a aba continua funcionando se os PNGs não existirem.
        self.img_play = self._carregar_icone("play.png")
        self.img_pause = self._carregar_icone("pause.png")
        self.img_continue = self._carregar_icone("continue.png")
        self.img_stop = self._carregar_icone("stop_lime.png") or self._carregar_icone("stop.png")

        self.btn_play = self._criar_botao_controle(
            frame_controle, "PLAY", self.img_play, self._play_ui, 10
        )
        self.btn_pause = self._criar_botao_controle(
            frame_controle, "PAUSE", self.img_pause, self._pause_ui, 60
        )
        self.btn_continue = self._criar_botao_controle(
            frame_controle, "CONTINUE", self.img_continue, self._continue_ui, 110
        )
        self.btn_stop = self._criar_botao_controle(
            frame_controle, "STOP", self.img_stop, self._stop_ui, 160
        )

        self.label_status = tk.Label(
            frame_status, text="Aguardando comando",
            font=("Arial", 12, "bold"), foreground="#003366", anchor="w"
        )
        self.label_status.place(x=5, y=5, width=220)

        self.text_result = tk.Text(
            frame_log, bg="#000000", fg="#E6E6E6",
            insertbackground="#FFFFFF", font=("Consolas", 10),
            wrap="word", state="disabled"
        )
        self.text_result.place(x=5, y=5, width=805, height=210)
        for tag, color in (
            ("INFO", "#E6E6E6"), ("UI", "#87CEFA"),
            ("STATUS", "#9EE8BE"), ("AVISO", "#FFF6BF"),
            ("ERRO", "#FF8080"), ("TX", "#D7B5FF"), ("RX", "#8FE8FF")
        ):
            self.text_result.tag_config(tag, foreground=color)
        self.scroll_log = ttk.Scrollbar(
            frame_log, orient="vertical", command=self.text_result.yview
        )
        self.scroll_log.place(x=815, y=5, height=210)
        self.text_result.configure(yscrollcommand=self.scroll_log.set)
        
        #icones
        self.img_play = self._carregar_icone("play.png")
        self.img_play_lime = self._carregar_icone("play_lime.png")

        self.img_pause = self._carregar_icone("pause.png")
        self.img_pause_lime = self._carregar_icone("pause_lime.png")

        self.img_continue = self._carregar_icone("continue.png")
        self.img_continue_lime = self._carregar_icone("continue_lime.png")

        self.img_stop = self._carregar_icone("stop.png")
        self.img_stop_lime = self._carregar_icone("stop_lime.png")

        # ----------------------------------------------------------
        # BOTÕES DE CONTROLE
        # Preserva posições e callbacks existentes.
        # ----------------------------------------------------------

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

        # Preserva o comportamento original:
        # STOP inicia com o ícone verde (lime), se disponível.
        self.btn_stop = self._criar_botao_controle(
            frame_controle,
            "STOP",
            self.img_stop_lime or self.img_stop,
            self._stop_ui,
            160
        )
        
    def _carregar_icone(self, nome_arquivo):
        """
        Carrega um ícone PNG original, redimensionando para 40x30.
        Procura a partir da localização real deste arquivo Python.
        """
        base = Path(__file__).resolve().parent
        candidatos = (
            base / nome_arquivo,
            base / "V20-barbosa" / "v21" / nome_arquivo,
            base.parent / "V20-barbosa" / "v21" / nome_arquivo,
            base.parent.parent / "V20-barbosa" / "v21" / nome_arquivo,
            base.parent.parent.parent / "V20-barbosa" / "v21" / nome_arquivo,
        )

        caminho = next(
            (p for p in candidatos if p.is_file()),
            None
        )

        if caminho is None:
            mensagem = (
                f"Ícone não encontrado: {nome_arquivo}. "
                f"Diretório da aba: {base}"
            )

            if hasattr(self, "_log_ui"):
                self._log_ui(mensagem, "AVISO")

            return None

        try:
            with Image.open(caminho) as imagem:
                imagem = imagem.convert("RGBA")
                imagem = imagem.resize((40, 30), Image.Resampling.LANCZOS)

                # O PhotoImage precisa permanecer referenciado pela classe.
                icone = ImageTk.PhotoImage(imagem)

            return icone

        except Exception as erro:
            if hasattr(self, "_log_ui"):
                self._log_ui(
                    f"Erro ao carregar {nome_arquivo}: {erro}",
                    "ERRO"
                )

            return None

    def _criar_botao_controle(self, parent, texto, imagem, callback, x):
        kwargs = {
            "command": callback,
            "width": 40,
            "height": 30
        }

        if imagem is not None:
            kwargs["image"] = imagem
        else:
            kwargs.update(text=texto, width=8, height=2)

        botao = tk.Button(parent, **kwargs)
        botao.place(x=x, y=1)

        return botao


    # ------------------------------------------------------------------
    # VALIDAÇÃO E MONTAGEM DOS COMANDOS
    # ------------------------------------------------------------------
    @staticmethod
    def _numero(texto, nome):
        valor = str(texto).strip().replace(",", ".")
        if not valor:
            raise ValueError(f"Preencha o campo {nome}.")
        try:
            numero = float(valor)
        except ValueError:
            raise ValueError(f"O campo {nome} precisa ser numérico.")
        if numero <= 0:
            raise ValueError(f"O campo {nome} precisa ser maior que zero.")
        return numero

    @staticmethod
    def _frequencia_mhz(texto):
        """Converte valores com kHz/MHz para MHz, sem adivinhar unidade ausente."""
        raw = str(texto).strip().lower().replace(",", ".").replace(" ", "")
        match = re.fullmatch(r"(\d+(?:\.\d+)?)(khz|mhz)", raw)
        if not match:
            raise ValueError(
                "Informe a frequência com unidade, por exemplo 150 kHz ou 80 MHz."
            )
        valor = float(match.group(1))
        unidade = match.group(2)
        mhz = valor / 1000.0 if unidade == "khz" else valor
        if mhz <= 0:
            raise ValueError("A frequência deve ser maior que zero.")
        return mhz

    def _validar_parametros(self):
        tensao = self._numero(self.tensao_var.get(), "Tensão (V)")
        f_inicio = self._frequencia_mhz(self.frequencia_inicio_var.get())
        f_final = self._frequencia_mhz(self.frequencia_final_var.get())
        if f_inicio >= f_final:
            raise ValueError("A frequência inicial deve ser menor que a final.")
        td = self._numero(self.td_var.get(), "TD")
        try:
            coupling_code = int(self.coupling_code_var.get())
        except ValueError:
            raise ValueError("Selecione um código de coupling entre 0 e 8.")
        if coupling_code not in range(9):
            raise ValueError("O código de coupling deve estar entre 0 e 8.")
        modulacao = self.modulacao_var.get().strip()
        if modulacao not in ("AM", "FM"):
            raise ValueError("Selecione AM ou FM.")
        return {
            "tensao": tensao,
            "f_inicio_mhz": f_inicio,
            "f_final_mhz": f_final,
            "td": td,
            "coupling_code": coupling_code,
            "coupling": self.coupling_var.get(),
            "modulacao": modulacao,
        }

    def _montar_comandos_parametros(self, p):
        """
        Monta comandos do script de terminal fornecido pelo usuário.
        NF recebe a frequência FINAL em MHz; o início fica para o software.
        NK é mantido como experimento de coupling e ainda precisa ser confirmado
        fisicamente para o CWS 500C.
        """
        return [
            f"NU,{p['tensao']:g};",
            f"NF,{p['f_final_mhz']:.3f};",
            f"NA,{p['modulacao']};",
            f"ND,{p['td']:g};",
            f"NK,{p['coupling_code']},{p['f_final_mhz']:.3f};",
        ]

    # ------------------------------------------------------------------
    # SERIAL TX/RX — não envia CC
    # ------------------------------------------------------------------
    def _ler_combo(self, nome, padrao=None):
        conexao = getattr(self.app, "conexao", None)
        widget = getattr(conexao, nome, None) if conexao is not None else None
        if widget is None:
            return padrao
        try:
            valor = widget.get()
            return valor if valor not in ("", None) else padrao
        except Exception:
            return padrao

    def _capturar_config_serial(self):
        porta = self._ler_combo("combo_porta")
        if not porta:
            raise RuntimeError(
                "Não consegui ler a porta na aba Conexão. Selecione uma porta serial."
            )
        baud = int(self._ler_combo("combo_baudrate", "9600"))
        paridade_txt = str(self._ler_combo("combo_paridade", "N")).upper()
        paridade = {
            "N": serial.PARITY_NONE, "NONE": serial.PARITY_NONE,
            "E": serial.PARITY_EVEN, "EVEN": serial.PARITY_EVEN,
            "O": serial.PARITY_ODD, "ODD": serial.PARITY_ODD,
            "M": serial.PARITY_MARK, "S": serial.PARITY_SPACE,
        }.get(paridade_txt, serial.PARITY_NONE)
        bits_txt = str(self._ler_combo("combo_data_bits", "8")).upper()
        bytesize = {
            "5": serial.FIVEBITS, "5 BITS": serial.FIVEBITS,
            "6": serial.SIXBITS, "6 BITS": serial.SIXBITS,
            "7": serial.SEVENBITS, "7 BITS": serial.SEVENBITS,
            "8": serial.EIGHTBITS, "8 BITS": serial.EIGHTBITS,
        }.get(bits_txt, serial.EIGHTBITS)
        stop_txt = str(self._ler_combo("combo_stop_bits", "1")).upper()
        stopbits = serial.STOPBITS_TWO if stop_txt in ("2", "2.0", "2 BITS") else serial.STOPBITS_ONE
        timeout_txt = self._ler_combo("combo_timeout_user", "0.2")
        try:
            timeout = max(0.1, float(str(timeout_txt).replace(",", ".")))
        except (TypeError, ValueError):
            timeout = 0.2
        return {
            "port": porta, "baudrate": baud, "parity": paridade,
            "bytesize": bytesize, "stopbits": stopbits, "timeout": timeout,
            "write_timeout": max(1.0, timeout),
        }

    @staticmethod
    def _codificar_comando(comando):
        if not isinstance(comando, str):
            raise TypeError("O comando precisa ser texto.")
        comando = comando.strip()
        if not comando.endswith(";"):
            raise ValueError("O comando precisa terminar com ';'.")
        payload = comando.encode("ascii")
        checksum = (-sum(payload)) & 0xFF
        return payload + bytes((checksum,)) + b"\n"

    def _garantir_sessao_serial(self):
        with self._session_lock:
            if self._ser is not None and self._ser.is_open:
                return
            config = self._capturar_config_serial()
            self._ser = serial.Serial(**config)
            self._stop_evt.clear()
            self._rx_thread = threading.Thread(
                target=self._rx_loop, name="IEC46-RX", daemon=True
            )
            self._tx_thread = threading.Thread(
                target=self._tx_loop, name="IEC46-TX", daemon=True
            )
            self._rx_thread.start()
            self._tx_thread.start()
        self._log_ui(
            f"Sessão serial aberta em {config['port']} ({config['baudrate']} baud).",
            "STATUS"
        )
        self._atualizar_status_ui("Serial aberta")

    def enviar_comando(self, comando):
        """Enfileira comando lógico; checksum e LF são adicionados no TX worker."""
        if not isinstance(comando, str) or not comando.strip().endswith(";"):
            self._log_ui(f"Comando inválido: {comando!r}", "ERRO")
            return False
        try:
            self._garantir_sessao_serial()
        except Exception as exc:
            self._log_ui(f"Não foi possível abrir a serial: {exc}", "ERRO")
            self._atualizar_status_ui("Falha serial")
            messagebox.showerror("Comunicação CWS", str(exc), parent=self.iec46_tab)
            return False
        self._last_tx_command = comando.strip()
        self._tx_queue.put(self._last_tx_command)
        return True

    def _tx_loop(self):
        while not self._stop_evt.is_set():
            try:
                comando = self._tx_queue.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                ser = self._ser
                if ser is None or not ser.is_open:
                    raise serial.SerialException("A sessão serial foi encerrada.")
                frame = self._codificar_comando(comando)
                ser.write(frame)
                ser.flush()
                self._event_queue.put(("LOG", f"[TX] {comando} | HEX: {frame.hex(' ').upper()}"))
            except Exception as exc:
                self._event_queue.put(("ERROR", f"Falha ao transmitir {comando}: {exc}"))
            finally:
                self._tx_queue.task_done()

    def _rx_loop(self):
        buffer = bytearray()
        while not self._stop_evt.is_set():
            try:
                ser = self._ser
                if ser is None or not ser.is_open:
                    break
                chunk = ser.read(ser.in_waiting or 1)
                if not chunk:
                    continue
                buffer.extend(chunk)
                # O equipamento usa ';' como terminador de mensagem; LF pode vir depois.
                while b";" in buffer:
                    pos = buffer.index(b";")
                    mensagem = bytes(buffer[:pos + 1])
                    del buffer[:pos + 1]
                    while buffer[:1] in (b"\n", b"\r"):
                        del buffer[:1]
                    texto = mensagem.decode("ascii", errors="replace").strip()
                    if texto:
                        self._event_queue.put(("RX", texto))
                if len(buffer) > 4096:
                    self._event_queue.put(("ERROR", "Buffer RX excedeu 4096 bytes; descartado."))
                    buffer.clear()
            except Exception as exc:
                if not self._stop_evt.is_set():
                    self._event_queue.put(("ERROR", f"Falha na recepção serial: {exc}"))
                time.sleep(0.1)
                break

    def _schedule_event_pump(self):
        try:
            while True:
                tipo, mensagem = self._event_queue.get_nowait()
                if tipo == "LOG":
                    self._log_ui(mensagem, "TX")
                elif tipo == "RX":
                    self._log_ui(f"[RX] {mensagem}", "RX")
                    self._processar_resposta(mensagem)
                elif tipo == "ERROR":
                    self._log_ui(mensagem, "ERRO")
                    self._atualizar_status_ui("Erro de comunicação")
        except queue.Empty:
            pass
        try:
            self.iec46_tab.after(50, self._schedule_event_pump)
        except tk.TclError:
            pass

    def fechar_sessao_serial(self):
        self._stop_evt.set()
        with self._session_lock:
            ser = self._ser
            self._ser = None
            if ser is not None:
                try:
                    if ser.is_open:
                        ser.close()
                except Exception:
                    pass
        self._atualizar_status_ui("Serial fechada")
        self._log_ui("Sessão serial fechada.", "STATUS")

    # ------------------------------------------------------------------
    # AÇÕES DA INTERFACE
    # ------------------------------------------------------------------
    def _log_ui(self, mensagem, nivel="INFO"):
        if not hasattr(self, "text_result"):
            return
        if nivel not in {"INFO", "UI", "STATUS", "AVISO", "ERRO", "TX", "RX"}:
            nivel = "INFO"
        try:
            self.text_result.configure(state="normal")
            self.text_result.insert(tk.END, f"[{nivel}] {mensagem}\n", nivel)
            self.text_result.see(tk.END)
            self.text_result.configure(state="disabled")
        except tk.TclError:
            pass

    def _atualizar_status_ui(self, mensagem):
        if hasattr(self, "label_status"):
            try:
                self.label_status.configure(text=mensagem)
            except tk.TclError:
                pass

    def _ajustar_tensao(self, direcao):
        if self.tensao_step is None:
            self._log_ui(
                "Passo de incremento da tensão ainda não foi definido; o valor não mudou.",
                "AVISO"
            )
            return
        try:
            valor = float(self.tensao_var.get().replace(",", "."))
        except ValueError:
            self._log_ui("Informe uma tensão numérica antes de ajustar.", "AVISO")
            return
        self.tensao_var.set(f"{valor + direcao * self.tensao_step:g}")

    def _setar_tensao_ui(self):
        try:
            tensao = self._numero(self.tensao_var.get(), "Tensão (V)")
        except ValueError as exc:
            messagebox.showwarning("Parâmetros", str(exc), parent=self.iec46_tab)
            return
        self._log_ui(f"Enviando tensão {tensao:g} V pelo comando NU.", "UI")
        self.enviar_comando(f"NU,{tensao:g};")

    def enviar_parametros_cws(self):
        try:
            parametros = self._validar_parametros()
        except ValueError as exc:
            messagebox.showwarning("Parâmetros inválidos", str(exc), parent=self.iec46_tab)
            return False

        comandos = self._montar_comandos_parametros(parametros)
        self.frequencia_var.set(
            f"{self.frequencia_inicio_var.get()} - {self.frequencia_final_var.get()}"
        )
        self._log_ui(
            "A frequência inicial é mantida para o software; NF recebe apenas a frequência final.",
            "INFO"
        )
        self._log_ui(
            f"Coupling selecionado: {parametros['coupling']} / código {parametros['coupling_code']}.",
            "AVISO"
        )
        self._log_ui("Sequência de parâmetros enviada em ordem; conferir respostas RR no hardware.", "INFO")
        for comando in comandos:
            if not self.enviar_comando(comando):
                return False
        return True

    def iniciar_teste_cws(self):
        if self.enviar_comando("AA;"):
            self._test_running = True
            self._atualizar_status_ui("Ensaio iniciado")
            self._log_ui("Comando de início AA enviado.", "STATUS")

    def _play_ui(self):
        self.iniciar_teste_cws()

    def _pause_ui(self):
        self._log_ui(
            "PAUSE não transmitido: o comando de pausa do CWS 500C ainda não foi confirmado.",
            "AVISO"
        )

    def _continue_ui(self):
        self._log_ui(
            "CONTINUE não transmitido: o comando de retomada do CWS 500C ainda não foi confirmado.",
            "AVISO"
        )

    def _stop_ui(self):
        if self.enviar_comando("AS;"):
            self._test_running = False
            self._atualizar_status_ui("Comando de parada enviado")
            self._log_ui("Comando de parada AS enviado.", "STATUS")

    def selecionar_coupling(self, event=None):
        coupling = self.coupling_var.get()
        if coupling == "BCI":
            self.coupling_code_var.set(str(self.COUPLING_BCI_CODE))
        elif coupling == "OFF":
            self.coupling_code_var.set("0")
        self._log_ui(
            f"Coupling selecionado: {coupling}; código atual {self.coupling_code_var.get()}.",
            "UI"
        )

    #não sei o código de coupling correto para BCI, mas deixei a interface para registro de teste
    def _coupling_code_changed(self, event=None):
        codigo = int(self.coupling_code_var.get())
        if codigo == 0:
            self.coupling_var.set("OFF")
        elif codigo == self.COUPLING_BCI_CODE:
            self.coupling_var.set("BCI")
        else:
            self.coupling_var.set("CDN/CCC a identificar")
        self._log_ui(
            f"Código de coupling alterado para {codigo}; nome físico ainda precisa ser confirmado.",
            "AVISO"
        )

    #ainda não sei qual valor é destinado para modulação, mas deixei a interface para registro de teste
    def selecionar_modulacao(self, event=None):
        self._log_ui(
            f"Modulação selecionada na interface: {self.modulacao_var.get()}.",
            "UI"
        )

   
    # RESPOSTAS DO EQUIPAMENTO
    # Handlers 
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
            "RR,15": self._on_rr_15_checksum_error,
            "RR,19": self._on_rr_19_internal_communication_error,
            "RR,20": self._on_rr_20_uncorrectable_limiting_error,
            "RR,25": self._on_rr_25_corrupt_calibration_data,
            "RR,31": self._on_rr_31_invalid_bci_memory,
            "RR,32": self._on_rr_32_bci_error,
        }

    def _processar_resposta(self, mensagem):
        texto = mensagem.strip().strip(";")
        if texto.startswith("CWS500C"):
            self._log_ui(f"Identificação do gerador recebida: {texto}", "STATUS")
            self._atualizar_status_ui("CWS500C respondeu")
            return
        chave = texto.replace(" ", "")
        if chave in self._handlers:
            self._handlers[chave]()
        elif texto.startswith("RR,"):
            self._log_ui(f"Resposta RR sem handler conhecido: {texto}", "AVISO")
        else:
            self._log_ui(f"Resposta recebida sem interpretação específica: {texto}", "INFO")

    def _rr(self, codigo, descricao, erro=False):
        nivel = "ERRO" if erro else "STATUS"
        self._log_ui(f"RR,{codigo}: {descricao}", nivel)
        self._atualizar_status_ui(f"RR,{codigo}")

    def _on_rr_00_test_finished(self):
        self._test_running = False
        self._rr("00", "Comando concluído / teste finalizado.")

    def _on_rr_03_invalid_calibration_memory(self):
        self._rr("03", "Memória de calibração inválida.", True)

    def _on_rr_04_voltage_out_of_limits(self):
        self._rr("04", "Tensão fora dos limites.", True)

    def _on_rr_05_fail1_test_interrupted(self):
        self._test_running = False
        self._rr("05", "Fail 1: ensaio interrompido.", True)

    def _on_rr_06_fail2(self):
        self._test_running = False
        self._rr("06", "Fail 2.", True)

    def _on_rr_10_string_error(self):
        self._rr("10", "Erro na string/comando enviado.", True)

    def _on_rr_11_test_not_possible(self):
        self._rr("11", "Ensaio não pode ser executado no estado atual.", True)

    def _on_rr_13_coupling_matrix_error(self):
        self._rr("13", "Erro de matriz/coupling; verificar o código selecionado.", True)

    def _on_rr_14_parameter_limited(self):
        self._rr("14", "Parâmetro limitado ou fora da faixa aceita.", True)

    def _on_rr_15_checksum_error(self):
        self._rr("15", "Erro de checksum. Não haverá reenvio automático.", True)

    def _on_rr_19_internal_communication_error(self):
        self._rr("19", "Erro de comunicação interna do equipamento.", True)

    def _on_rr_20_uncorrectable_limiting_error(self):
        self._rr("20", "Erro de limitação não corrigível.", True)

    def _on_rr_25_corrupt_calibration_data(self):
        self._rr("25", "Dados de calibração corrompidos.", True)

    def _on_rr_31_invalid_bci_memory(self):
        self._rr("31", "Memória BCI inválida.", True)

    def _on_rr_32_bci_error(self):
        self._rr("32", "Erro relacionado à memória BCI.", True)

    def destroy(self):
        """Pode ser chamado pelo app antes de destruir a aba."""
        self.fechar_sessao_serial()
