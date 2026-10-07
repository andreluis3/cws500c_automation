from tkinter import ttk
import tkinter as tk
import serial
from tkinter import ttk, messagebox
import time
import threading

resposta = ' '

class conexaoTab:
    def __init__(self, parent, app):
        self.app = app
        self.conexao_tab = parent
        self.build_conexao_tab()

# Aba Conexão com place()
    def build_conexao_tab(self):
        ### Frame para porta COM       
        frame_conexao = ttk.LabelFrame(self.conexao_tab, text="Conexão", style="Custom.TLabelframe", padding=(10, 10))
        frame_conexao.place(x=20, y=130, width=400, height=100)
        tk.Label(frame_conexao, text="Porta de comunicação:").place(x=1, y=1)
        # Lista de portas COM disponíveis
        portas = [port.device for port in serial.tools.list_ports.comports()]
        # Combobox para seleção da porta
        self.combo_porta = ttk.Combobox(frame_conexao, values=portas, width=8, state="readonly")
        self.combo_porta.place(x=140, y=1)
        # Define valor padrão (se houver portas)
        if portas:
            self.combo_porta.set(portas[0])
        else:
            self.combo_porta.set("Nenhuma porta")

        ### Frame para seleção do equipamento
        frame_equip = ttk.LabelFrame(self.conexao_tab, text="Seleção do Gerador", style="Custom.TLabelframe", padding=(10, 10))
        frame_equip.place(x=20, y=20, width=400, height=100)
        self.equipamento_var = tk.StringVar(value="UCS-500")
        rb_ucs = tk.Radiobutton(frame_equip, text="UCS-500", variable=self.equipamento_var, value="UCS-500", command=self.atualizar_abas)
        rb_cws = tk.Radiobutton(frame_equip, text="CWS-500", variable=self.equipamento_var, value="CWS-500", command=self.atualizar_abas)
        rb_ucs.place(x=5, y=1)
        rb_cws.place(x=100, y=1)

        ### Frame para configurações da porta serial
        frame_config_com = ttk.LabelFrame(self.conexao_tab, text="Configuração da porta serial", style="Custom.TLabelframe", padding=(10, 10))
        frame_config_com.place(x=430, y=20, width=400, height=380)      
        
        # Baudrate
        tk.Label(frame_config_com, text="Baudrate:").place(x=10, y=10)
        baudrates = ["9600", "19200", "38400", "57600", "115200"]
        self.combo_baudrate = ttk.Combobox(frame_config_com, values=baudrates, width=12, state="readonly")
        self.combo_baudrate.place(x=140, y=10)
        self.combo_baudrate.set("9600")

        # Paridade
        tk.Label(frame_config_com, text="Paridade:").place(x=10, y=50)
        paridades = ["None", "Even", "Odd", "Mark", "Space"]
        self.combo_paridade = ttk.Combobox(frame_config_com, values=paridades, width=12, state="readonly")
        self.combo_paridade.place(x=140, y=50)
        self.combo_paridade.set("None")

        # Bits de dados
        tk.Label(frame_config_com, text="Bits de dados:").place(x=10, y=90)
        data_bits = ["5", "6", "7", "8"]
        self.combo_data_bits = ttk.Combobox(frame_config_com, values=data_bits, width=12, state="readonly")
        self.combo_data_bits.place(x=140, y=90)
        self.combo_data_bits.set("8")

        # Bits de parada
        tk.Label(frame_config_com, text="Bits de parada:").place(x=10, y=130)
        stop_bits = ["1", "1.5", "2"]
        self.combo_stop_bits = ttk.Combobox(frame_config_com, values=stop_bits, width=12, state="readonly")
        self.combo_stop_bits.place(x=140, y=130)
        self.combo_stop_bits.set("1")

        # Timeout
        tk.Label(frame_config_com, text="Timeout (s):").place(x=10, y=170)
        timeout_user = ["1", "2", "3", "4", "5"]
        self.combo_timeout_user = ttk.Combobox(frame_config_com, values=timeout_user, width=12, state="readonly")
        self.combo_timeout_user.place(x=140, y=170)
        self.combo_timeout_user.set("2")

        # Botão Conectar
        self.btn_conectar = tk.Button(frame_conexao, text="Conectar", command=self.conectar_comando)
        self.btn_conectar.place(x=230, y=1)

        # Botão Desconectar
        self.btn_desconectar = tk.Button(frame_conexao, text="Desconectar", command=self.desconectar_comando)
        self.btn_desconectar.place(x=300, y=1)

        # Área de resultado
        self.text_result = tk.Text(self.conexao_tab, width=50, height=10)
        self.text_result.place(x=20, y=240)

    def build_placeholder_tab(self, tab, texto):
        tk.Label(tab, text=texto, font=("Arial", 14)).place(relx=0.5, rely=0.5, anchor="center")

#---------------------------------------------------------------------------------------
#Funções
    def atualizar_abas(self):
        equipamento = self.equipamento_var.get()
        if equipamento == "UCS-500":
            # Habilita todas e desabilita IEC 61000-4-6
            self.app.notebook.tab(1, state="normal")  # IEC 61000-4-4
            self.app.notebook.tab(2, state="normal")  # IEC 61000-4-5
            self.app.notebook.tab(4, state="normal")  # IEC 61000-4-11
            self.app.notebook.tab(3, state="disabled")  # IEC 61000-4-6
        else:
            # Habilita todas e desabilita IEC 61000-4-4, 4-5, 4-11
            self.app.notebook.tab(3, state="normal")  # IEC 61000-4-6
            self.app.notebook.tab(1, state="disabled")  # IEC 61000-4-4
            self.app.notebook.tab(2, state="disabled")  # IEC 61000-4-5
            self.app.notebook.tab(4, state="disabled")  # IEC 61000-4-11
            
    def conversor(self, c: str) -> bytes:
        # Garante ASCII
        payload = c.encode('ascii')

        soma = sum(payload)          # soma dos bytes ASCII
        checksum = (-soma) & 0xFF    # (0x100 - soma) mod 256

        # Monta bytes finais (NÃO use chr aqui)
        cmd = payload + bytes([checksum]) + b'\n'  # adicione \\n somente se o protocolo pedir
        print(cmd)  # debug
        return cmd

    def comando(self, x: str) -> bytearray:
        # Agora conversor já retorna bytes prontos
        s1 = self.conversor(x)
        return bytearray(s1)

    def conectar_comando(self):
        global resposta
        porta = self.combo_porta.get()
        equipamento = self.equipamento_var.get()
        if not porta:
            messagebox.showwarning("Aviso", "Informe a porta COM!")
            return
        if equipamento == "UCS-500":
            self.conexao(porta)
        if equipamento == "CWS-500":
            self.conexao_CWS(porta)
        self.text_result.delete("1.0", tk.END)
        self.text_result.insert(tk.END, f"Comando enviado para {equipamento} na porta {porta}\n")
        self.text_result.insert(tk.END, f"Aguardando conexão...\n")

    def conexao(self, porta):
        self.text_result.delete("1.0", tk.END)  # Limpa área de resultado
        def tentar_conectar():
            global ucs_bool, resposta
            equipamento = self.equipamento_var.get()
            try:
                baudrate = int(self.combo_baudrate.get())
                paridade = self.combo_paridade.get()
                data_bits = int(self.combo_data_bits.get())
                stop_bits = float(self.combo_stop_bits.get())
                timeout_user = int(self.combo_timeout_user.get())

                paridade_map = {
                    "None": serial.PARITY_NONE,
                    "Even": serial.PARITY_EVEN,
                    "Odd": serial.PARITY_ODD,
                    "Mark": serial.PARITY_MARK,
                    "Space": serial.PARITY_SPACE
                }

                s = serial.Serial(
                    port=porta,
                    baudrate=baudrate,
                    bytesize=data_bits,
                    parity=paridade_map[paridade],
                    stopbits=stop_bits,
                    timeout=timeout_user
                )

                s.write(self.comando('PC;'))
                time.sleep(1)
                resposta = s.read(50)
                #time.sleep(1)
                self.text_result.delete("1.0", tk.END)
                self.text_result.insert(tk.END, resposta.decode(errors='ignore') + "\n")
                s.close()
                if resposta:
                    self.text_result.insert(tk.END, f"Conectado ao {equipamento}!\n")
                    ucs_bool = True
                else:
                    self.text_result.insert(tk.END, f"Não conectado ao {equipamento}!\n")
                    ucs_bool = False
            except Exception as e:
                self.text_result.insert(tk.END, f"Erro: {e}\n")

        # Inicia thread
        thread_conexao = threading.Thread(target=tentar_conectar, daemon=True)
        thread_conexao.start()        
        
    def conexao_CWS(self, porta):
        self.text_result.delete("1.0", tk.END)  # Limpa área de resultado
        def tentar_conectar():
            global cws_bool, resposta
            equipamento = self.equipamento_var.get()
            try:
                baudrate = int(self.combo_baudrate.get())
                paridade = self.combo_paridade.get()
                data_bits = int(self.combo_data_bits.get())
                stop_bits = float(self.combo_stop_bits.get())
                timeout_user = int(self.combo_timeout_user.get())

                paridade_map = {
                    "None": serial.PARITY_NONE,
                    "Even": serial.PARITY_EVEN,
                    "Odd": serial.PARITY_ODD,
                    "Mark": serial.PARITY_MARK,
                    "Space": serial.PARITY_SPACE
                }

                s = serial.Serial(
                    port=porta,
                    baudrate=baudrate,
                    bytesize=data_bits,
                    parity=paridade_map[paridade],
                    stopbits=stop_bits,
                    timeout=timeout_user
                )

                s.write(self.comando('CC;'))
                time.sleep(1)
                resposta = s.read(50)
                #time.sleep(1)
                self.text_result.insert(tk.END, resposta.decode(errors='ignore') + "\n")
                s.close()
                if resposta:
                    self.text_result.insert(tk.END, f"Conectado ao {equipamento}!\n")
                    cws_bool = True
                else:
                    self.text_result.insert(tk.END, f"Não conectado ao {equipamento}!\n")
                    cws_bool = False
            except Exception as e:
                self.text_result.insert(tk.END, f"Erro: {e}\n")

        # Inicia thread
        thread_conexao = threading.Thread(target=tentar_conectar, daemon=True)
        thread_conexao.start()

    def desconexao(self, porta):
        self.text_result.delete("1.0", tk.END)  # Limpa área de resultado
        def tentar_conectar():
            global ucs_bool, cws_bool
            equipamento = self.equipamento_var.get()
            try:
                baudrate = int(self.combo_baudrate.get())
                paridade = self.combo_paridade.get()
                data_bits = int(self.combo_data_bits.get())
                stop_bits = float(self.combo_stop_bits.get())
                timeout_user = int(self.combo_timeout_user.get())

                paridade_map = {
                    "None": serial.PARITY_NONE,
                    "Even": serial.PARITY_EVEN,
                    "Odd": serial.PARITY_ODD,
                    "Mark": serial.PARITY_MARK,
                    "Space": serial.PARITY_SPACE
                }

                s = serial.Serial(
                    port=porta,
                    baudrate=baudrate,
                    bytesize=data_bits,
                    parity=paridade_map[paridade],
                    stopbits=stop_bits,
                    timeout=timeout_user
                )

                s.write(self.comando('AR;'))
                time.sleep(1)
                s.close()
                ucs_bool = False
                cws_bool = False
                self.text_result.delete("1.0", tk.END)
                self.text_result.insert(tk.END, f"Desconectado!\nChecar display do {equipamento}\n")
            except Exception as e:
                self.text_result.insert(tk.END, f"Erro: {e}\n")

        # Inicia thread
        thread_desconexao = threading.Thread(target=tentar_conectar, daemon=True)
        thread_desconexao.start()
        
    def conectar_comando(self):
        global resposta
        porta = self.combo_porta.get()
        equipamento = self.equipamento_var.get()
        if not porta:
            messagebox.showwarning("Aviso", "Informe a porta COM!")
            return
        if equipamento == "UCS-500":
            self.conexao(porta)
        if equipamento == "CWS-500":
            self.conexao_CWS(porta)
        self.text_result.delete("1.0", tk.END)
        self.text_result.insert(tk.END, f"Comando enviado para {equipamento} na porta {porta}\n")
        self.text_result.insert(tk.END, f"Aguardando conexão...\n")

    def desconectar_comando(self):
        global resposta
        porta = self.combo_porta.get()
        equipamento = self.equipamento_var.get()
        if not porta:
            messagebox.showwarning("Aviso", "Informe a porta COM!")
            return

        self.desconexao(porta)
        self.text_result.delete("1.0", tk.END)
        self.text_result.insert(tk.END, f"Comando enviado para desconexão do {equipamento}.\nAguardando desconexão...\n")
