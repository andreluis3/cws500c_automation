import threading, queue, serial, re, time, tkinter as tk
from tkinter import messagebox

def __init__(self, parent, app):
    self.parent = parent
    self.app = app

    # --- sessão serial persistente ---
    self._ser = None
    self._rx_thread = None
    self._tx_thread = None
    self._tx_queue = queue.Queue()
    self._event_queue = queue.Queue()
    self._stop_evt = threading.Event()

    ###############

    def _capturar_config_serial(self):
        porta = self.app.conexao.combo_porta.get()
        baudrate = int(self.app.conexao.combo_baudrate.get())
        paridade = self.app.conexao.combo_paridade.get()
        data_bits = int(self.app.conexao.combo_data_bits.get())
        stop_bits = float(self.app.conexao.combo_stop_bits.get())
        timeout_user = int(self.app.conexao.combo_timeout_user.get())

        paridade_map = {
            "None": serial.PARITY_NONE,
            "Even": serial.PARITY_EVEN,
            "Odd": serial.PARITY_ODD,
            "Mark": serial.PARITY_MARK,
            "Space": serial.PARITY_SPACE
        }

        return {
            "port": porta,
            "baudrate": baudrate,
            "bytesize": data_bits,
            "parity": paridade_map[paridade],
            "stopbits": stop_bits,
            "timeout": timeout_user,        # leitura responsiva
            "write_timeout": timeout_user,  # evita travar no write
        }
    
    ############

    def iniciar_sessao_serial(self):
        if self._ser:  # já está ativo
            return
        try:
            cfg = self._capturar_config_serial()
            self._ser = serial.Serial(**cfg)
        except Exception as e:
            messagebox.showwarning("Erro", f"Não foi possível abrir porta: {e}")
            return

        self._stop_evt.clear()
        self._rx_thread = threading.Thread(target=self._rx_loop, daemon=True).start()
        self._tx_thread = threading.Thread(target=self._tx_loop, daemon=True).start()

        # bomba de eventos para a UI (executa a cada 50ms)
        self._agendar_pump_ui()

    def parar_sessao_serial(self):
        if not self._ser:
            return
        self._stop_evt.set()
        try:
            self._tx_queue.put_nowait(None)  # acorda o tx
        except:
            pass
        try:
            self._ser.close()
        except:
            pass
        self._ser = None


    ############

    def _rx_loop(self):
        # Lê linhas do equipamento enquanto a sessão estiver ativa
        while not self._stop_evt.is_set():
            try:
                line = self._ser.readline()  # até \n ou timeout
                if not line:
                    continue
                txt = line.decode("ascii", errors="replace").strip()
                if not txt:
                    continue
                # Enfileira para a UI tratar
                self._event_queue.put(("DEVICE_MSG", txt))
            except Exception as e:
                # Em caso de erro, notifica UI e tenta continuar
                self._event_queue.put(("ERROR", f"RX erro: {e}"))
                time.sleep(0.2)

    def _tx_loop(self):
        while not self._stop_evt.is_set():
            try:
                item = self._tx_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if item is None:  # sinal de parada
                break
            try:
                # converta seu comando para bytes conforme seu método atual
                payload = self.app.conexao.comando(item)
                self._ser.write(payload)
                self._ser.flush()
            except Exception as e:
                self._event_queue.put(("ERROR", f"TX erro ao enviar '{item}': {e}"))
            finally:
                self._tx_queue.task_done()

    ###########

    def _agendar_pump_ui(self):
        try:
            while True:
                typ, payload = self._event_queue.get_nowait()
                if typ == "DEVICE_MSG":
                    self._handle_device_message(payload)
                elif typ == "ERROR":
                    # Mostre em log/label, evite spam de messagebox se muito frequente
                    self._log(payload)
        except queue.Empty:
            pass
        # rode novamente em 50 ms
        self.parent.after(50, self._agendar_pump_ui)

    def _log(self, txt):
        # Seu widget de log
        try:
            self.text_result_4_4.insert(tk.END, f"{txt}\n")
            self.text_result_4_4.see(tk.END)
        except:
            pass

    #################

    _CODE_RE = re.compile(r'^\s*([A-Z]{2})(?:,([^:;]*))?(?::([^;]*))?\s*;?\s*$', re.I)
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
        m = _CODE_RE.match(msg.strip())
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
    
    ################

    
def _build_handlers(self):
    return {
        "RR,00": self._on_rr_00_test_finished,
        "RR,02": self._on_rr_02_ready_for_trigger,
        "RR,05": self._on_rr_05_fail1,
        "RR,06": self._on_rr_06_running_stopped,
        "RR,07": self._on_rr_07_fail2,
        "RR,08": self._on_rr_08_overtemp,
        "RR,10": self._on_rr_10_string_error,
        "RR,11": self._on_rr_11_test_not_possible,
        "RR,12": self._on_rr_12_wrong_coupler,
        "RR,13": self._on_rr_13_unknown_parameter,
        "RR,15": self._on_rr_15_checksum_error,
        "RR,16": self._on_rr_16_sync_error,
        "RR,18": self._on_rr_18_overcurrent,
        "RR,20": self._on_rr_20_not_correctable,
        "RF,.":  self._on_rf_feedback_freq,
        "BS,.":  self._on_bs_feedback_bank,
        # adicione outros conforme a tabela do fabricante
    }


############

def _handle_device_message(self, msg: str):
    code_base, params, original = self._parse_code(msg)

    # log bruto (opcional)
    self._log(f"[RX] {original}")

    if not code_base:
        # mensagem fora do padrão
        return

    handler = self._handlers.get(code_base)
    if handler:
        try:
            handler(params, original)  # roda na UI thread
        except Exception as e:
            self._log(f"Erro no handler {code_base}: {e}")
    else:
        # se não tiver handler específico, você pode tratar por prefixo
        prefix = code_base.split(",")[0]
        if prefix in ("RR", "RF", "BS"):
            # desconhecido, mas válido: logue de forma genérica
            self._on_generic(prefix, code_base, params, original)
        else:
            self._log(f"[WARN] Código não mapeado: {code_base}")