from tkinter import ttk
import tkinter as tk
from PIL import Image, ImageTk
import serial
import time
from tkinter import ttk, messagebox
import threading
from tkinter import ttk, filedialog
import queue

class IEC44Tab:
    def __init__(self, parent, app):
        self.app = app
        self.iec44_tab = parent
        self.build_4_4_tab()        
        self._cmd_queue = queue.Queue()
        self._serial_worker_started = False


    # Estilo e tag para destaque
        style_treeview = ttk.Style()
        style_treeview.map("Treeview",
          background=[("selected", "lightblue")],
          foreground=[("selected", "black")])
        style_treeview.configure("Treeview", rowheight=25)

    # Aba IEC 61000-4-4
    def build_4_4_tab(self):
        
        ### Frame para Aplicação única
        frame_4_4_unico = ttk.LabelFrame(self.iec44_tab, text="Aplicação única", style="Custom.TLabelframe", padding=(10, 10))
        frame_4_4_unico.place(x=20, y=20, width=600, height=130)
        
        tk.Label(frame_4_4_unico, text="Amplitude (V):").place(x=1, y=1)
        
        tensao_4_4 = ["250", "500", "1000", "2000", "4000"]
        self.combo_tensao_4_4 = ttk.Combobox(frame_4_4_unico, values=tensao_4_4, width=8, state="readonly")
        self.combo_tensao_4_4.place(x=85, y=1)
        self.combo_tensao_4_4.set("250")

        tk.Label(frame_4_4_unico, text="Frequência (kHz):").place(x=200, y=1)

        freq_4_4 = ["5", "100"]
        self.combo_freq_4_4 = ttk.Combobox(frame_4_4_unico, values=freq_4_4, width=8, state="readonly")
        self.combo_freq_4_4.place(x=300, y=1)
        self.combo_freq_4_4.set("5")

        tk.Label(frame_4_4_unico, text="Duração (ms):").place(x=1, y=25)

        duracao_4_4 = ["0.8", "15"]
        self.combo_duracao_4_4 = ttk.Combobox(frame_4_4_unico, values=duracao_4_4, width=8, state="readonly")
        self.combo_duracao_4_4.place(x=85, y=25)
        self.combo_duracao_4_4.set("15")

        tk.Label(frame_4_4_unico, text="Repetição (ms):").place(x=200, y=25)

        repeticao_4_4 = ["300"]
        self.combo_repeticao_4_4 = ttk.Combobox(frame_4_4_unico, values=repeticao_4_4, width=8, state="readonly")
        self.combo_repeticao_4_4.place(x=300, y=25)
        self.combo_repeticao_4_4.set("300")

        tk.Label(frame_4_4_unico, text="Polaridade:").place(x=1, y=49)

        pol_4_4 = ["+", "-"]
        self.combo_pol_4_4 = ttk.Combobox(frame_4_4_unico, values=pol_4_4, width=8, state="readonly")
        self.combo_pol_4_4.place(x=85, y=49)
        self.combo_pol_4_4.set("+")

        tk.Label(frame_4_4_unico, text="Acoplamento:").place(x=200, y=49)

        acoplamento_4_4 = ["L", "N", "L-N", "PE", "L-PE", "N-PE", "L-N-PE", "/ - CCP"]
        self.combo_acoplamento_4_4 = ttk.Combobox(frame_4_4_unico, values=acoplamento_4_4, width=8, state="readonly")
        self.combo_acoplamento_4_4.place(x=300, y=49)
        self.combo_acoplamento_4_4.set("L")

        tk.Label(frame_4_4_unico, text="Tempo de ensaio (s):").place(x=175, y=73)

        tempo_4_4 = ["15", "30", "60", "120"]
        self.combo_tempo_4_4 = ttk.Combobox(frame_4_4_unico, values=tempo_4_4, width=8, state="readonly")
        self.combo_tempo_4_4.place(x=300, y=73)
        self.combo_tempo_4_4.set("60")

        self.btn_4_4_enviar = tk.Button(frame_4_4_unico, text="Enviar parâmetros", command=self.envia_parametros_4_4, width=16, height=2, bg="#9EE8BE")
        self.btn_4_4_enviar.place(x=430, y=49)
        
        ### Frame para Aplicação sequencial
        frame_4_4_sequencial = ttk.LabelFrame(self.iec44_tab, text="Aplicação sequêncial", style="Custom.TLabelframe", padding=(10, 10))
        frame_4_4_sequencial.place(x=20, y=160, width=860, height=245)
        
        tk.Label(frame_4_4_sequencial, text="Amplitude (V):").place(x=20, y=13)
        self.combo_seq_tensao_4_4 = ttk.Combobox(frame_4_4_sequencial, values=tensao_4_4, width=8, state="readonly")
        self.combo_seq_tensao_4_4.place(x=140, y=13)
        self.combo_seq_tensao_4_4.set("250")
        
        tk.Label(frame_4_4_sequencial, text="Duração (ms):").place(x=20, y=38)
        self.combo_seq_duracao_4_4 = ttk.Combobox(frame_4_4_sequencial, values=duracao_4_4, width=8, state="readonly")
        self.combo_seq_duracao_4_4.place(x=140, y=38)
        self.combo_seq_duracao_4_4.set("15")
        
        tk.Label(frame_4_4_sequencial, text="Polaridade:").place(x=20, y=63)
        self.combo_seq_pol_4_4 = ttk.Combobox(frame_4_4_sequencial, values=pol_4_4, width=8, state="readonly")
        self.combo_seq_pol_4_4.place(x=140, y=63)
        self.combo_seq_pol_4_4.set("+")
        
        tk.Label(frame_4_4_sequencial, text="Frequência (kHz):").place(x=20, y=88)
        self.combo_seq_freq_4_4 = ttk.Combobox(frame_4_4_sequencial, values=freq_4_4, width=8, state="readonly")
        self.combo_seq_freq_4_4.place(x=140, y=88)
        self.combo_seq_freq_4_4.set("5")
        
        tk.Label(frame_4_4_sequencial, text="Repetição (ms):").place(x=20, y=113)
        self.combo_seq_repeticao_4_4 = ttk.Combobox(frame_4_4_sequencial, values=repeticao_4_4, width=8, state="readonly")
        self.combo_seq_repeticao_4_4.place(x=140, y=113)
        self.combo_seq_repeticao_4_4.set("300")
        
        tk.Label(frame_4_4_sequencial, text="Acoplamento:").place(x=20, y=138)
        self.combo_seq_acoplamento_4_4 = ttk.Combobox(frame_4_4_sequencial, values=acoplamento_4_4, width=8, state="readonly")
        self.combo_seq_acoplamento_4_4.place(x=140, y=138)
        self.combo_seq_acoplamento_4_4.set("L")
        
        tk.Label(frame_4_4_sequencial, text="Tempo de ensaio (s):").place(x=20, y=163)
        self.combo_seq_tempo_4_4 = ttk.Combobox(frame_4_4_sequencial, values=tempo_4_4, width=8, state="readonly")
        self.combo_seq_tempo_4_4.place(x=140, y=163)
        self.combo_seq_tempo_4_4.set("60")
        
        #self.tree = ttk.Treeview(frame_4_4_sequencial, columns=("ID", "Acoplamento", "Tensão", "Polaridade", "Duração", "Repetição", "Frequência", "T_Ensaio"), show="headings", height=7)
        self.tree = ttk.Treeview(frame_4_4_sequencial, columns=("Acoplamento", "Tensão", "Polaridade", "Duração", "Repetição", "Frequência", "T_Ensaio"), show="headings", height=7)
        #self.tree.heading("ID", text="ID")
        self.tree.heading("Acoplamento", text="Acop.")
        self.tree.heading("Tensão", text="V(V)")
        self.tree.heading("Polaridade", text="Pol.")
        self.tree.heading("Duração", text="Dur.(ms)")
        self.tree.heading("Repetição", text="Rep.(ms)")
        self.tree.heading("Frequência", text="Freq.(kHz)")
        self.tree.heading("T_Ensaio", text="T(s)")
        
        #self.tree.column("ID", width=50)
        self.tree.column("Acoplamento", width=65)
        self.tree.column("Tensão", width=65)
        self.tree.column("Polaridade", width=65)
        self.tree.column("Duração", width=65)
        self.tree.column("Repetição", width=65)
        self.tree.column("Frequência", width=65)
        self.tree.column("T_Ensaio", width=65)
        self.tree.place(x=330, y=1)

        # Configura tag para destaque
        self.tree.tag_configure("destaque", background="yellow", foreground="black")

        # Configura tag para default
        self.tree.tag_configure("default", background="white", foreground="black")

        #self.scrollbar = tk.Scrollbar(frame_4_4_sequencial, orient=tk.VERTICAL)
        #self.scrollbar.place(x=340, y=1, height=200)

        self.scrollbar = ttk.Scrollbar(frame_4_4_sequencial, orient=tk.VERTICAL, command=self.tree.yview)
        self.scrollbar.place(x=310, y=1, height=200)
        self.tree.configure(yscrollcommand=self.scrollbar.set)

        self.btn_4_4_incluir = tk.Button(frame_4_4_sequencial, text="-->>", command=self.adicionar_item_4_4, width=7, height=1, bg="#9EE8BE")
        self.btn_4_4_incluir.place(x=230, y=14)
        self.btn_4_4_excluir = tk.Button(frame_4_4_sequencial, text="<<--", command=self.remover_item_4_4, width=7, height=1, bg="#B0B0B0", state="disabled")
        self.btn_4_4_excluir.place(x=230, y=49)
        self.btn_4_4_editar = tk.Button(frame_4_4_sequencial, text="Edit.Linha", command=self.editar_item_4_4, width=7, height=1, bg="#B0B0B0", state="disabled")
        self.btn_4_4_editar.place(x=230, y=84)
        self.btn_4_4_deletar = tk.Button(frame_4_4_sequencial, text="Del.Linha", command=self.deletar_item_4_4, width=7, height=1, bg="#B0B0B0", state="disabled")
        self.btn_4_4_deletar.place(x=230, y=119)
        self.btn_4_4_montar = tk.Button(frame_4_4_sequencial, text="Montar", command=self.montar_4_4, width=7, height=1, bg="#B0B0B0", state="disabled")
        self.btn_4_4_montar.place(x=230, y=154)
        #self.btn_4_4_proximo = tk.Button(frame_4_4_sequencial, text="Próximo", command=self.iniciar_tempo_4_4, width=7, height=2)
        #self.btn_4_4_proximo.place(x=600, y=210)
        self.btn_4_4_salvar = tk.Button(frame_4_4_sequencial, text="Salvar", command=self.salvar_4_4, width=6, height=2, bg="#9EE8BE", state="normal")
        self.btn_4_4_salvar.place(x=790, y=20)
        self.btn_4_4_abrir = tk.Button(frame_4_4_sequencial, text="Abrir", command=self.abrir_4_4, width=6, height=2, bg="#9EE8BE")
        self.btn_4_4_abrir.place(x=790, y=70)
        self.btn_4_4_deletarTab = tk.Button(frame_4_4_sequencial, text="Del.Tab.", command=self.limpar_treeview, width=6, height=2, bg="#9EE8BE", state="normal")
        self.btn_4_4_deletarTab.place(x=790, y=120)

        ### Frame para controle
        frame_4_4_controle = ttk.LabelFrame(self.iec44_tab, text="Controle", style="Custom.TLabelframe", padding=(10, 10))
        frame_4_4_controle.place(x=630, y=20, width=250, height=130)

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

        
        self.btn_4_4_iniciar = tk.Button(frame_4_4_controle, image = self.img_play, command=self.iniciar_4_4, width=40, height=30)
        self.btn_4_4_iniciar.place(x=15, y=1)

        self.btn_4_4_continuar = tk.Button(frame_4_4_controle, image = self.img_continue, command=self.continuar_4_4, width=40, height=30, state="disabled")
        self.btn_4_4_continuar.place(x=65, y=1)

        self.btn_4_4_pausar = tk.Button(frame_4_4_controle, image = self.img_pausar, command=self.pausar_4_4, width=40, height=30, state="normal")
        self.btn_4_4_pausar.place(x=115, y=1)

        self.btn_4_4_parar = tk.Button(frame_4_4_controle, image = self.img_stop_lime, command=self.parar_4_4, width=40, height=30)
        self.btn_4_4_parar.place(x=165, y=1)

        

        tk.Label(frame_4_4_controle, text="T. decorrido (hh:mm:ss):").place(x=1, y=45)

        self.label_tempo_decorrido = tk.Label(frame_4_4_controle, text="00:00:00", font=("Arial", 14), foreground="green")
        self.label_tempo_decorrido.place(x=150, y=45)

        tk.Label(frame_4_4_controle, text="Intervalo (hh:mm:ss):").place(x=1, y=68)

        self.label_tempo_parcial = tk.Label(frame_4_4_controle, text="00:00:00", font=("Arial", 14), foreground="blue")
        self.label_tempo_parcial.place(x=150, y=68)

        ### Frame para Aplicação sequencial pré programada
        frame_4_4_sequencial_pp = ttk.LabelFrame(self.iec44_tab, text="Aplicação sequêncial pré-programada", style="Custom.TLabelframe", padding=(10, 10))
        frame_4_4_sequencial_pp.place(x=20, y=410, width=450, height=155)

        tk.Label(frame_4_4_sequencial_pp, text="Seq. de acoplamento:", font=("Arial", 10, "bold"), fg="#080069").place(x=5, y=1)

        self.modo_acoplamento_4_4 = tk.StringVar(value="Com PE")
        rb_com_pe = tk.Radiobutton(frame_4_4_sequencial_pp, text="Com PE", variable=self.modo_acoplamento_4_4, value="Com PE")
        rb_sem_pe = tk.Radiobutton(frame_4_4_sequencial_pp, text="Sem PE", variable=self.modo_acoplamento_4_4, value="Sem PE")
        rb_com_pe.place(x=155, y=1)
        rb_sem_pe.place(x=155, y=30)

        tk.Label(frame_4_4_sequencial_pp, text="Nível de tensão:", font=("Arial", 10, "bold"), fg="#080069").place(x=250, y=1)

        self.nivel_tensao_4_4 = tk.StringVar(value="250")
        rb_250v = tk.Radiobutton(frame_4_4_sequencial_pp, text="250 V", variable=self.nivel_tensao_4_4, value="250")
        rb_500v = tk.Radiobutton(frame_4_4_sequencial_pp, text="500 V", variable=self.nivel_tensao_4_4, value="500")
        rb_1000v = tk.Radiobutton(frame_4_4_sequencial_pp, text="1000 V", variable=self.nivel_tensao_4_4, value="1000")
        rb_2000v = tk.Radiobutton(frame_4_4_sequencial_pp, text="2000 V", variable=self.nivel_tensao_4_4, value="2000")
        rb_4000v = tk.Radiobutton(frame_4_4_sequencial_pp, text="4000 V", variable=self.nivel_tensao_4_4, value="4000")
        rb_250v.place(x=365, y=1)
        rb_500v.place(x=365, y=23)
        rb_1000v.place(x=365, y=46)
        rb_2000v.place(x=365, y=71)
        rb_4000v.place(x=365, y=96)

        self.btn_4_4_montar_pp = tk.Button(frame_4_4_sequencial_pp, text="Montar", command=self.montar_4_4_pp, width=10, height=2, bg="#9EE8BE")
        self.btn_4_4_montar_pp.place(x=150, y=70)

        self.btn_4_4_informacoes_pp = tk.Button(frame_4_4_sequencial_pp, text="Informações", command=self.informacoes_4_4_pp, width=10, height=2, bg="#FFF6BF")
        self.btn_4_4_informacoes_pp.place(x=20, y=70)

        ### Área de resultado
        self.text_result_4_4 = tk.Text(self.iec44_tab, width=51, height=8.5)
        self.text_result_4_4.place(x=470, y=420)

        ### Tags para texto
        self.text_result_4_4.tag_config("Atenção", foreground="red", font=("Arial", 16, "bold"))
        self.text_result_4_4.tag_config("Sucesso", foreground="green", font=("Arial", 12, "bold"))
        self.text_result_4_4.tag_config("Normal", foreground="blue", font=("Arial", 12))

#------------------------------------------------------------------------------------------
#Funções
    def envia_parametros_4_4(self):        
        self.app.prmt_4_4 = True
        self.app.montar = False
        if self.app.ucs_bool is True:
            string_comando = "EN,"
            string_comando += self.combo_tensao_4_4.get()+","

            if self.combo_freq_4_4.get() == "5" and self.combo_duracao_4_4.get() == "0.8":
                self.combo_duracao_4_4.set("15")
                messagebox.showwarning("Aviso", "Atenção!\n* Para a frequência de 5 KHz, a duração deve ser de 15 ms.\n* Para a frequência de 100 kHz, a duração deve ser de 0,8 ms.")
            elif self.combo_freq_4_4.get() == "100" and self.combo_duracao_4_4.get() == "15":
                self.combo_duracao_4_4.set("0.8")
                messagebox.showwarning("Aviso", "Atenção!\n* Para a frequência de 5 KHz, a duração deve ser de 15 ms.\n* Para a frequência de 100 kHz, a duração deve ser de 0,8 ms.")
            else:
                self.combo_duracao_4_4 = self.combo_duracao_4_4
                self.combo_freq_4_4 = self.combo_freq_4_4
                
            freq = int(self.combo_freq_4_4.get()) * 10
            string_comando += str(freq)+","
            duracao = float(self.combo_duracao_4_4.get())*10
            string_comando += str(int(duracao))+","
            string_comando += self.combo_repeticao_4_4.get()+","
            if self.combo_acoplamento_4_4.get() == "/ - CCP":
                send_acoplamento_4_4 = "0"
            elif self.combo_acoplamento_4_4.get() == "L":
                send_acoplamento_4_4 = "1"
            elif self.combo_acoplamento_4_4.get() == "N":
                send_acoplamento_4_4 = "2"
            elif self.combo_acoplamento_4_4.get() == "L-N":
                send_acoplamento_4_4 = "3"
            elif self.combo_acoplamento_4_4.get() == "PE":
                send_acoplamento_4_4 = "4"
            elif self.combo_acoplamento_4_4.get() == "L-PE":
                send_acoplamento_4_4 = "5"
            elif self.combo_acoplamento_4_4.get() == "N-PE":
                send_acoplamento_4_4 = "6"
            elif self.combo_acoplamento_4_4.get() == "L-N-PE":
                send_acoplamento_4_4 = "7"
            else:
                print("Acoplamento incorreto!")
            string_comando += send_acoplamento_4_4+","
            if self.combo_pol_4_4.get() == "+":
                send_pol_4_4 = "0"
            elif self.combo_pol_4_4.get() == "-":
                send_pol_4_4 = "1"
            else:
                print("Polaridade incorreta!")
            string_comando += send_pol_4_4+","
            string_comando += self.combo_tempo_4_4.get()+";"
            print(string_comando)
            try:
                # Captura as configurações da interface
                porta = self.app.conexao.combo_porta.get()
                baudrate = int(self.app.conexao.combo_baudrate.get())
                paridade = self.app.conexao.combo_paridade.get()
                data_bits = int(self.app.conexao.combo_data_bits.get())
                stop_bits = float(self.app.conexao.combo_stop_bits.get())
                timeout_user = int(self.app.conexao.combo_timeout_user.get())

                # Mapeamento da paridade para pyserial
                paridade_map = {
                    "None": serial.PARITY_NONE,
                    "Even": serial.PARITY_EVEN,
                    "Odd": serial.PARITY_ODD,
                    "Mark": serial.PARITY_MARK,
                    "Space": serial.PARITY_SPACE
                }

                # Abre a porta serial com as configurações escolhidas
                s = serial.Serial(
                    port=porta,
                    baudrate=baudrate,
                    bytesize=data_bits,
                    parity=paridade_map[paridade],
                    stopbits=stop_bits,
                    timeout=timeout_user
                )
                # Envia comando
                s.write(self.app.conexao.comando('BS,1;'))
                time.sleep(1)
                s.write(self.app.conexao.comando(string_comando))
                #time.sleep(1)
                s.close()
                #ucs_bool = True
                self.text_result_4_4.delete("1.0", tk.END)
                self.text_result_4_4.insert(tk.END, f"Parâmetros da Aplicação Única enviados! \nClique em 'Iniciar' para começar o ensaio.", "Sucesso")
            except Exception as e:
                return f"Erro: {e}"
        else:
            messagebox.showwarning("Aviso", "Gerador desconectado!\nVerifique conexão serial.")
        return
    
    def envia_comando(self, string):
        if not self.app.ucs_bool:
            messagebox.showwarning("Aviso", "Gerador desconectado!\nVerifique conexão serial.")
            return

        if not string:
            messagebox.showwarning("Aviso", "Erro na conexão!\nParâmetros não enviados.")
            return

        # garante worker rodando
        self._start_serial_worker()

        # coloca na fila e retorna imediatamente (UI não congela)
        self._cmd_queue.put(string)

    
    def _start_serial_worker(self):
        if self._serial_worker_started:
            return
        self._serial_worker_started = True
        threading.Thread(target=self._serial_worker_loop, daemon=True).start()

    
    def _serial_worker_loop(self):
        while True:
            cmd = self._cmd_queue.get()
            if cmd is None:
                self._cmd_queue.task_done()
                break

            try:
                config = self._capturar_config_serial()
                with serial.Serial(**config) as s:
                    s.write(self.app.conexao.comando(cmd))
                    s.flush()
            except Exception as e:
                # volta para UI thread para mostrar/logar erro com segurança
                self.text_result_4_4.after(
                    0, lambda e=e: messagebox.showwarning("Erro", f"Falha na serial ao enviar '{cmd}':\n{e}")
                )
            finally:
                self._cmd_queue.task_done()
                
       
    
    def iniciar_4_4(self):
        if self.app.ucs_bool is not True:
            messagebox.showwarning("Aviso", "Gerador desconectado!\nVerifique conexão serial.")
            return

        # --- CASO 1: aplicação única ---
        if self.app.montar is False and self.app.prmt_4_4 is True:
            try:
                config = self._capturar_config_serial()

                # (Opcional) Atualizações rápidas de UI antes de enviar, para dar feedback imediato
                self.text_result_4_4.delete("1.0", tk.END)
                self.text_result_4_4.insert(tk.END, "Enviando comando para o gerador...", "Normal")

                # Dispara worker (não congela a UI)
                threading.Thread(target=self._worker_enviar_AA_4_4, args=(config, "uni"), daemon=True).start()

            except Exception as e:
                return f"Erro: {e}"

            return

        # --- CASO 2: aplicação sequencial ---
        if self.app.montar is True and self.app.prmt_4_4 is False:
            try:
                config = self._capturar_config_serial()

                self.text_result_4_4.delete("1.0", tk.END)
                self.text_result_4_4.insert(tk.END, "Enviando comando para o gerador...", "Normal")

                threading.Thread(target=self._worker_enviar_AA_4_4, args=(config, "seq"), daemon=True).start()

            except Exception as e:
                return f"Erro: {e}"

            return

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
            "timeout": timeout_user,
            # evita travar em write se o dispositivo estiver “enroscado”
            "write_timeout": timeout_user
        }

    def _worker_enviar_AA_4_4(self, config, modo):
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
            self.text_result_4_4.after(0, lambda: messagebox.showwarning("Erro", f"Falha na serial: {e}"))
            return

        # Ao terminar o envio com sucesso, voltar para UI thread
        self.text_result_4_4.after(0, lambda: self._apos_enviar_AA_4_4(modo))  
        
    def _apos_enviar_AA_4_4(self, modo):
        """
        Roda na UI thread depois que o comando AA; foi enviado e o worker terminou.
        """
        # (Re)inicia/organiza contador (sem bloquear)
        self.parar_tempo_4_4()
        self.iniciar_tempo_4_4()
        self.verificar_tempo_4_4()

        # UI comum aos dois modos
        self.btn_4_4_iniciar.config(image=self.img_play_lime)
        self.btn_4_4_iniciar.config(state="disabled")
        self.btn_4_4_incluir.config(state="disabled", bg="#B0B0B0")
        self.btn_4_4_excluir.config(state="disabled", bg="#B0B0B0")
        self.btn_4_4_deletar.config(state="disabled", bg="#B0B0B0")
        self.btn_4_4_montar.config(state="disabled", bg="#B0B0B0")
        self.btn_4_4_enviar.config(state="disabled", bg="#B0B0B0")
        self.btn_4_4_montar_pp.config(state="disabled", bg="#B0B0B0")
        self.btn_4_4_editar.config(state="disabled", bg="#B0B0B0")
        self.btn_4_4_abrir.config(state="disabled", bg="#B0B0B0")
        self.btn_4_4_salvar.config(state="disabled", bg="#B0B0B0")
        self.btn_4_4_deletarTab.config(state="disabled", bg="#B0B0B0")
        self.btn_4_4_parar.config(image=self.img_stop)
        self.btn_4_4_pausar.config(state="normal")

        # Agora separa a lógica de cada modo
        if modo == "uni":
            self.app.prmt_4_4 = False
            self.app.pause_uni = True

            t_total = int(self.combo_tempo_4_4.get())
            horas = t_total // 3600
            minutos = (t_total % 3600) // 60
            segundos = t_total % 60

            self.text_result_4_4.delete("1.0", tk.END)
            self.text_result_4_4.insert(tk.END, f"Aplicação única iniciada! \nA estimativa de duração total é de {horas:02}:{minutos:02}:{segundos:02}", "Sucesso")
            return

        if modo == "seq":
            #self.intervalo_seq = (int(self.busca_item_4_4(0, 6)) * 1000) #- 1000

            self.iec44_tab.after(0, lambda: self.proximo_4_4(0))

            self.iniciar_seq_tempo_4_4()
            self.verificar_seq_tempo_4_4()

            self.app.pause_seq = True

            t_total = self.tempo_total_4_4()
            horas = t_total // 3600
            minutos = (t_total % 3600) // 60
            segundos = t_total % 60

            self.text_result_4_4.delete("1.0", tk.END)
            self.text_result_4_4.insert(tk.END, f"Aplicação sequencial iniciada! \nA estimativa de duração total é de {horas:02}:{minutos:02}:{segundos:02}", "Sucesso")
            return    
    
    def parar_4_4 (self):
        if hasattr(self, "after_id") and self.after_id:
            self.iec44_tab.after_cancel(self.after_id)
            self.after_id = None

        if self.app.ucs_bool is True:
            try:
                # Captura as configurações da interface
                porta = self.app.conexao.combo_porta.get()
                baudrate = int(self.app.conexao.combo_baudrate.get())
                paridade = self.app.conexao.combo_paridade.get()
                data_bits = int(self.app.conexao.combo_data_bits.get())
                stop_bits = float(self.app.conexao.combo_stop_bits.get())
                timeout_user = int(self.app.conexao.combo_timeout_user.get())

                # Mapeamento da paridade para pyserial
                paridade_map = {
                    "None": serial.PARITY_NONE,
                    "Even": serial.PARITY_EVEN,
                    "Odd": serial.PARITY_ODD,
                    "Mark": serial.PARITY_MARK,
                    "Space": serial.PARITY_SPACE
                }

                # Abre a porta serial com as configurações escolhidas
                s = serial.Serial(
                    port=porta,
                    baudrate=baudrate,
                    bytesize=data_bits,
                    parity=paridade_map[paridade],
                    stopbits=stop_bits,
                    timeout=timeout_user
                )

                # Envia comando
                s.write(self.app.conexao.comando('AS;'))
                time.sleep(1)
                s.close()
                #ucs_bool = True
                self.text_result_4_4.delete("1.0", tk.END)
                self.text_result_4_4.insert(tk.END, f"Ensaio parado!", "Normal")
                self.parar_tempo_4_4()
                self.btn_4_4_iniciar.config(image = self.img_play, state="normal")
                self.btn_4_4_parar.config(image=self.img_stop_lime)
                self.btn_4_4_pausar.config(state="normal", image=self.img_pausar)
                self.btn_4_4_continuar.config(state="disabled", image=self.img_continue)
                self.btn_4_4_iniciar.config(state="normal", image=self.img_play)
                self.btn_4_4_enviar.config(state="normal", bg="#9EE8BE")
                self.btn_4_4_incluir.config(state="normal", bg="#9EE8BE")
                self.btn_4_4_montar_pp.config(state="normal", bg="#9EE8BE")
                self.btn_4_4_salvar.config(state="normal", bg="#9EE8BE")
                self.btn_4_4_abrir.config(state="normal", bg="#9EE8BE")
                self.btn_4_4_deletarTab.config(state="normal", bg="#9EE8BE")
                if self.tree.get_children():
                    self.btn_4_4_incluir.config(state="normal", bg="#9EE8BE")
                    self.btn_4_4_excluir.config(state="normal", bg="#9EE8BE")
                    self.btn_4_4_editar.config(state="normal", bg="#9EE8BE")
                    self.btn_4_4_deletar.config(state="normal", bg="#9EE8BE")
                    self.btn_4_4_montar.config(state="normal", bg="#9EE8BE")
                return
            except Exception as e:
                return f"Erro: {e}"
        else:
            messagebox.showwarning("Aviso", "Gerador desconectado!\nVerifique conexão serial.")
    
    def pausar_4_4(self):
        if self.app.pause_seq is True:
            self.app.montar = True
            self.app.prmt_4_4 = False
        elif self.app.pause_uni is True:
            self.app.montar = False
            self.app.prmt_4_4 = True

        if self.app.ucs_bool is True:
            try:
                # Captura as configurações da interface
                porta = self.app.conexao.combo_porta.get()
                baudrate = int(self.app.conexao.combo_baudrate.get())
                paridade = self.app.conexao.combo_paridade.get()
                data_bits = int(self.app.conexao.combo_data_bits.get())
                stop_bits = float(self.app.conexao.combo_stop_bits.get())
                timeout_user = int(self.app.conexao.combo_timeout_user.get())

                # Mapeamento da paridade para pyserial
                paridade_map = {
                    "None": serial.PARITY_NONE,
                    "Even": serial.PARITY_EVEN,
                    "Odd": serial.PARITY_ODD,
                    "Mark": serial.PARITY_MARK,
                    "Space": serial.PARITY_SPACE
                }

                # Abre a porta serial e envia comando de pausa
                s = serial.Serial(
                    port=porta,
                    baudrate=baudrate,
                    bytesize=data_bits,
                    parity=paridade_map[paridade],
                    stopbits=stop_bits,
                    timeout=timeout_user
                )
                s.write(self.app.conexao.comando('AS;'))
                #time.sleep(1)
                s.close()

                # Calcula tempo restante antes de cancelar o after
                if hasattr(self, "tempo_seq_inicial") and hasattr(self, "intervalo_seq"):
                    elapsed_ms = int((time.time() - self.tempo_seq_inicial) * 1000)
                    self.remaining_ms = max(self.intervalo_seq - elapsed_ms, 0)
                else:
                    self.remaining_ms = None

                # Cancela agendamento
                if hasattr(self, "after_id") and self.after_id:
                    self.iec44_tab.after_cancel(self.after_id)
                    self.after_id = None

                # Atualiza interface
                self.pausar_tempo_4_4()
                self.pausar_seq_tempo_4_4()
                self.btn_4_4_iniciar.config(image=self.img_play)
                self.btn_4_4_parar.config(image=self.img_stop)
                self.btn_4_4_pausar.config(image=self.img_pausar_lime, state="disabled")
                self.btn_4_4_continuar.config(state="normal", image=self.img_continue)
                self.btn_4_4_iniciar.config(state="disabled")

                self.text_result_4_4.delete("1.0", tk.END)
                self.text_result_4_4.insert(tk.END, "Ensaio pausado!", "Normal")
                return
            except Exception as e:
                return f"Erro: {e}"
        else:
            messagebox.showwarning("Aviso", "Gerador desconectado!\nVerifique conexão serial.")   
    
    def continuar_4_4(self):
        if self.app.ucs_bool is True:
            if self.app.prmt_4_4 is True and self.app.montar is False:
                try:
                    # Captura as configurações da interface
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

                    # Envia comando para continuar
                    s = serial.Serial(
                        port=porta,
                        baudrate=baudrate,
                        bytesize=data_bits,
                        parity=paridade_map[paridade],
                        stopbits=stop_bits,
                        timeout=timeout_user
                    )
                    s.write(self.app.conexao.comando('AW;'))
                    #time.sleep(1)
                    s.close()

                    # Atualiza interface
                    self.btn_4_4_continuar.config(image=self.img_continue_lime, state="disabled")
                    self.btn_4_4_pausar.config(image=self.img_pausar, state="normal")
                    
                    t_total = int(self.combo_tempo_4_4.get())
                    horas = t_total // 3600           
                    minutos = (t_total % 3600) // 60            
                    segundos = t_total % 60            
                
                    self.text_result_4_4.delete("1.0", tk.END)
                    self.text_result_4_4.insert(tk.END, f"Continuação do ensaio! \nA estimativa de duração total é de {horas:02}:{minutos:02}:{segundos:02}", "Normal")

                    # Retoma contadores internos
                    self.verificar_tempo_4_4()
                    self.retomar_tempo_4_4()
                    return
                except Exception as e:
                    return f"Erro: {e}"
            elif self.app.prmt_4_4 is False and self.app.montar is True:
                try:
                    # Captura as configurações da interface
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

                    # Envia comando para continuar
                    s = serial.Serial(
                        port=porta,
                        baudrate=baudrate,
                        bytesize=data_bits,
                        parity=paridade_map[paridade],
                        stopbits=stop_bits,
                        timeout=timeout_user
                    )
                    s.write(self.app.conexao.comando('AW;'))
                    #time.sleep(1)
                    s.close()

                    # Atualiza interface
                    self.text_result_4_4.delete("1.0", tk.END)
                    self.text_result_4_4.insert(tk.END, "Continuação do ensaio!", "Normal")
                    self.btn_4_4_continuar.config(image=self.img_continue_lime, state="disabled")
                    self.btn_4_4_pausar.config(image=self.img_pausar, state="normal")

                    # Reagenda com tempo restante
                    if hasattr(self, "remaining_ms") and self.remaining_ms and self.remaining_ms > 0:
                        delay = self.remaining_ms
                    else:
                        delay = self.intervalo_seq  # caso não tenha pausa registrada

                    t_add = self.tempo_adicional_4_4()

                    t_total = self.tempo_total_4_4() #+ t_add

                    horas = t_total // 3600           
                    minutos = (t_total % 3600) // 60            
                    segundos = t_total % 60            
                
                    self.text_result_4_4.delete("1.0", tk.END)
                    self.text_result_4_4.insert(tk.END, f"Continuação do ensaio! \nA estimativa de duração total é de {horas:02}:{minutos:02}:{segundos:02}", "Normal")
            

                    self.tempo_seq_inicial = time.time()  # reinicia contagem
                    self.after_id = self.iec44_tab.after(delay, lambda: self.proximo_4_4(self.i_atual + 1))

                    # Limpa remaining_ms para evitar reutilização indevida
                    self.remaining_ms = None

                    # Retoma contadores internos
                    self.verificar_tempo_4_4()
                    self.verificar_seq_tempo_4_4()
                    self.retomar_tempo_4_4()
                    self.retomar_seq_tempo_4_4()
                    

                    return
                except Exception as e:
                    return f"Erro: {e}"
        else:
            messagebox.showwarning("Aviso", "Gerador desconectado!\nVerifique conexão serial.")

    def adicionar_item_4_4(self):
        if self.combo_seq_freq_4_4.get() == "5" and self.combo_seq_duracao_4_4.get() == "0.8":
            self.combo_seq_duracao_4_4.set("15")
            messagebox.showwarning("Aviso", "Atenção!\n* Para a frequência de 5 KHz, a duração deve ser de 15 ms.\n* Para a frequência de 100 kHz, a duração deve ser de 0,8 ms.")
        elif self.combo_seq_freq_4_4.get() == "100" and self.combo_seq_duracao_4_4.get() == "15":
            self.combo_seq_duracao_4_4.set("0.8")
            messagebox.showwarning("Aviso", "Atenção!\n* Para a frequência de 5 KHz, a duração deve ser de 15 ms.\n* Para a frequência de 100 kHz, a duração deve ser de 0,8 ms.")
        else:
            self.combo_seq_duracao_4_4 = self.combo_seq_duracao_4_4
            self.combo_seq_freq_4_4 = self.combo_seq_freq_4_4
            
        acoplamento = self.combo_seq_acoplamento_4_4.get().strip()
        amplitude = self.combo_seq_tensao_4_4.get().strip()
        duracao = self.combo_seq_duracao_4_4.get().strip()
        pol = self.combo_seq_pol_4_4.get().strip()
        freq = self.combo_seq_freq_4_4.get().strip()
        repeticao = self.combo_seq_repeticao_4_4.get().strip()
        tempo = self.combo_seq_tempo_4_4.get().strip()
        if acoplamento and amplitude and duracao and pol and freq and repeticao and tempo:
            self.tree.insert("", tk.END, values=(acoplamento, amplitude, pol, duracao, repeticao, freq, tempo))
            #item_id = self.tree.insert("", tk.END, values=(acoplamento, amplitude, pol, duracao, repeticao, freq, tempo))
            #self.tree.set(item_id, "ID", item_id)
            self.tempo_total_4_4()
            self.btn_4_4_excluir.config(state="normal", bg="#9EE8BE")
            self.btn_4_4_deletar.config(state="normal", bg="#9EE8BE")
            self.btn_4_4_montar.config(state="normal", bg="#9EE8BE")
            self.btn_4_4_salvar.config(state="normal", bg="#9EE8BE")
            self.btn_4_4_deletarTab.config(state="normal", bg="#9EE8BE")
            self.btn_4_4_editar.config(state="normal", bg="#9EE8BE")
        else:
            messagebox.showwarning("Aviso", "Erro no preenchimento dos dados!")
        itens = self.tree.get_children()
        if itens:
            self.combo_seq_tempo_4_4.config(state="disabled")
        else:
            self.combo_seq_tempo_4_4.config(state="normal")
            
    def deletar_item_4_4(self):
        selecionados = self.tree.selection()
        self.text_result_4_4.delete("1.0", tk.END)
        if selecionados:
            # Apaga os itens selecionados
            for item_id in selecionados:
                self.tree.delete(item_id)

            # Limpa o texto associado
            self.text_result_4_4.delete("1.0", tk.END)

            if len(self.tree.get_children()) < 2:
                self.combo_seq_tempo_4_4.config(state="normal")

            # Agora verifica se a Treeview ficou vazia
            if  len(self.tree.get_children()) < 1:
                # Desabilita e pinta os botões
                self.btn_4_4_excluir.config(state="disabled", bg="#B0B0B0")
                self.btn_4_4_deletar.config(state="disabled", bg="#B0B0B0")
                self.btn_4_4_montar.config(state="disabled", bg="#B0B0B0")
                self.btn_4_4_montar_pp.config(state="normal", bg="#9EE8BE")
                self.btn_4_4_editar.config(state="disabled", bg="#B0B0B0")
                self.btn_4_4_enviar.config(state="normal", bg="#9EE8BE")
                #self.btn_4_4_salvar.config(state="disabled", bg="red")
                #self.btn_4_4_deletarTab.config(state="disabled", bg="red")
        else:
            messagebox.showwarning("Aviso", "Nenhuma linha selecionada!")        

    def limpar_treeview(self):
        itens = self.tree.get_children()
        self.text_result_4_4.delete("1.0", tk.END)
        for item in itens:
            self.tree.delete(item)
        self.combo_seq_tempo_4_4.config(state="normal")
        self.btn_4_4_excluir.config(state="disabled", bg="#B0B0B0")
        self.btn_4_4_deletar.config(state="disabled", bg="#B0B0B0")
        self.btn_4_4_montar.config(state="disabled", bg="#B0B0B0")
        self.btn_4_4_editar.config(state="disabled", bg="#B0B0B0")
        self.btn_4_4_enviar.config(state="normal", bg="#9EE8BE")
        self.btn_4_4_montar_pp.config(state="normal", bg="#9EE8BE")
                    
    def remover_item_4_4(self):
        selecionados = self.tree.selection()
        self.text_result_4_4.delete("1.0", tk.END)
        if selecionados:
            item_id = selecionados[0]  # Pega o primeiro selecionado
            valores = self.tree.item(item_id, "values")  # Tupla com os valores da linha
            self.combo_seq_acoplamento_4_4.set(valores[0])
            self.combo_seq_tensao_4_4.set(valores[1])
            self.combo_seq_pol_4_4.set(valores[2])
            self.combo_seq_duracao_4_4.set(valores[3])
            self.combo_seq_repeticao_4_4.set(valores[4])
            self.combo_seq_freq_4_4.set(valores[5])
            self.combo_seq_tempo_4_4.set(valores[6])

            # Remove a linha do Treeview
            self.tree.delete(item_id)

            if len(self.tree.get_children()) < 2:
                self.combo_seq_tempo_4_4.config(state="normal")

            if  len(self.tree.get_children()) < 1:
                # Desabilita e pinta os botões
                self.btn_4_4_excluir.config(state="disabled", bg="#B0B0B0")
                self.btn_4_4_deletar.config(state="disabled", bg="#B0B0B0")
                self.btn_4_4_montar.config(state="disabled", bg="#B0B0B0")
                self.btn_4_4_montar_pp.config(state="normal", bg="#9EE8BE")
                self.btn_4_4_editar.config(state="disabled", bg="#B0B0B0")
                self.btn_4_4_enviar.config(state="normal", bg="#9EE8BE")
                #self.btn_4_4_salvar.config(state="disabled", bg="red")
                #self.btn_4_4_deletarTab.config(state="disabled", bg="red")
        else:
            messagebox.showwarning("Aviso", "Nenhuma linha selecionada!")

    def editar_item_4_4(self):
        selecionados = self.tree.selection()
        self.text_result_4_4.delete("1.0", tk.END)
        if selecionados:
            acoplamento = self.combo_seq_acoplamento_4_4.get().strip()
            amplitude = self.combo_seq_tensao_4_4.get().strip()
            duracao = self.combo_seq_duracao_4_4.get().strip()
            pol = self.combo_seq_pol_4_4.get().strip()
            freq = self.combo_seq_freq_4_4.get().strip()
            repeticao = self.combo_seq_repeticao_4_4.get().strip()
            tempo = self.combo_seq_tempo_4_4.get().strip()
            if acoplamento and amplitude and duracao and pol and freq and repeticao and tempo:
                item_id = selecionados[0]
                self.tree.item(item_id, values=(acoplamento, amplitude, pol, duracao, repeticao, freq, tempo))
        else:
            messagebox.showwarning("Aviso", "Nenhuma linha selecionada!")        

    def busca_item_4_4(self, id, coluna):    
        item_id = self.tree.get_children()[id]
        valores = self.tree.item(item_id, "values")
        valor = valores[coluna]
        #print(type(valor))
        return valor   
            
    def tempo_total_4_4(self):
        soma = 0
        itens = self.tree.get_children()  # Lista de IDs
        for i in range(len(itens)):       # Itera pelos índices
            string = self.busca_item_4_4(i, 6)  # Pega valor da coluna 6
            tempo = int(string)
            soma += tempo
        return soma
    
    def proximo_4_4(self, i=0):    
        self.i_atual = i
        itens = self.tree.get_children()
        self.cont = 0     
        if i >= len(itens):
            self.parar_4_4()
            self.text_result_4_4.delete("1.0", tk.END)
            self.text_result_4_4.insert(tk.END, f"Ensaio finalizado!", "Sucesso")
            return  # terminou todos os itens
        else:            
            for j in range(len(itens)):
                item_id = itens[j]
                self.tree.item(item_id, tags=("default",))
                if j == i:
                    self.tree.item(item_id, tags=("destaque",))
                    self.tree.see(item_id)
            if i == 0:
                    if self.busca_item_4_4(i, 0) == "/ - CCP":
                        self.varp0 = "0"
                    elif self.busca_item_4_4(i, 0) == "L":
                        self.varp0 = "1"
                    elif self.busca_item_4_4(i, 0) == "N":
                        self.varp0 = "2"
                    elif self.busca_item_4_4(i, 0) == "L-N":
                        self.varp0 = "3"
                    elif self.busca_item_4_4(i, 0) == "PE":
                        self.varp0 = "4"
                    elif self.busca_item_4_4(i, 0) == "L-PE":
                        self.varp0 = "5"
                    elif self.busca_item_4_4(i, 0) == "N-PE":
                        self.varp0 = "6"
                    elif self.busca_item_4_4(i, 0) == "L-N-PE":
                        self.varp0 = "7"
                    else:
                        messagebox.showwarning("Aviso", "Acoplamento incorreto!")
                    self.varp1 = self.busca_item_4_4(i, 1)
                    if self.busca_item_4_4(i, 2) == "+":
                        self.varp2 = "0"
                    elif self.busca_item_4_4(i, 2) == "-":
                        self.varp2 = "1"
                    else:
                        messagebox.showwarning("Aviso", "Polaridade incorreta!")
                    self.varp3 = self.busca_item_4_4(i, 3)
                    self.varp4 = self.busca_item_4_4(i, 4)
                    self.varp5 = self.busca_item_4_4(i, 5)
                    self.varp6 = self.busca_item_4_4(i, 6)
            else:   
                for j in range(7):
                    if j == 0:
                        if self.busca_item_4_4(i, j) == "/ - CCP":
                            varp0 = "0"
                        elif self.busca_item_4_4(i, j) == "L":
                            varp0 = "1"
                        elif self.busca_item_4_4(i, j) == "N":
                            varp0 = "2"
                        elif self.busca_item_4_4(i, j) == "L-N":
                            varp0 = "3"
                        elif self.busca_item_4_4(i, j) == "PE":
                            varp0 = "4"
                        elif self.busca_item_4_4(i, j) == "L-PE":
                            varp0 = "5"
                        elif self.busca_item_4_4(i, j) == "N-PE":
                            varp0 = "6"
                        elif self.busca_item_4_4(i, j) == "L-N-PE":
                            varp0 = "7"
                        else:
                            messagebox.showwarning("Aviso", "Acoplamento incorreto!")
                        if varp0 != self.varp0:
                            self.varp0 = varp0
                            self.envia_comando("NC,"+self.varp0+";") 
                            self.cont+=2                   
                        else:
                            self.varp0 = self.varp0
                    if self.busca_item_4_4(i, j) != self.varp1 and j == 1:
                        self.varp1 = self.busca_item_4_4(i, j)
                        self.envia_comando("NU,"+self.varp1+";")
                        self.cont+=2
                    else:
                        self.varp1 = self.varp1
                    if j == 2:
                        if self.busca_item_4_4(i, j) == "+":
                            varp2 = "0"
                        elif self.busca_item_4_4(i, j) == "-":
                            varp2 = "1"
                        else:
                            messagebox.showwarning("Aviso", "Polaridade incorreta!")
                        if varp2 != self.varp2:
                            self.varp2 = varp2
                            self.envia_comando("NP,"+self.varp2+";")
                            self.cont+=2
                        else:
                            self.varp2 = self.varp2
                    if self.busca_item_4_4(i, j) != self.varp3 and j == 3:
                        varp3 = int(float(self.busca_item_4_4(i, j)) * 10)
                        self.varp3 = str(varp3)
                        self.envia_comando("ND,"+self.varp3+";")
                        self.cont+=2
                    else:
                        self.varp3 = self.varp3
                    if self.busca_item_4_4(i, j) != self.varp4 and j == 4:
                        self.varp4 = self.busca_item_4_4(i, j)
                        self.envia_comando("NR,"+self.varp4+";")
                        self.cont+=2
                    else:
                        self.varp4 = self.varp4
                    if self.busca_item_4_4(i, j) != self.varp5 and j == 5:
                        varp5 = int(self.busca_item_4_4(i, j)) * 10
                        self.varp5 = str(varp5)
                        self.envia_comando("NF,"+self.varp5+";")
                        self.cont+=2
                    else:
                        self.varp5 = self.varp5
                    if self.busca_item_4_4(i, j) != self.varp6 and j == 6:
                        self.varp6 = self.busca_item_4_4(i, j)
                        self.cont+=2
                    else:
                        self.varp6 = self.varp6
            self.verificar_seq_tempo_4_4()  
            #self.iniciar_seq_tempo_4_4()      
            self.retomar_seq_tempo_4_4()
            #self.verificar_tempo_4_4()
            #self.intervalo_seq = (int(self.varp6) * 1000) + 1000  # em ms
            #intervalo = ((int(self.varp6) * 1000) + 1000) - (self.tempo_seq_decorrido * 1000)
            #print("varp6: ", self.varp6)
            #self.master.after(intervalo, lambda: self.proximo_4_4(i+1))
            self.intervalo_seq = (int(self.varp6) * 1000) #- ((self.cont+1)*1000)
            self.after_id = self.iec44_tab.after(self.intervalo_seq, lambda: self.proximo_4_4(i+1))
            
            #self.verificar_seq_tempo_4_4(int(self.varp6))
    
    def tempo_adicional_4_4(self):
        itens = self.tree.get_children()
        if not itens:
            return 0

        # valores "prev" da primeira linha
        prev = [self.busca_item_4_4(0, j) for j in range(7)]
        t_add = 0

        # percorre a partir da segunda linha
        for i in range(1, len(itens)):
            for j in range(7):
                val = self.busca_item_4_4(i, j)
                if val != prev[j]:
                    t_add += 2
                    prev[j] = val  # atualiza o "prev" para a próxima comparação
            t_add = t_add

        return t_add

    def montar_4_4(self):
        t_add = self.tempo_adicional_4_4()
        if not self.tree.get_children():
            messagebox.showwarning("Aviso", "Sequência de testes não preenchida!")
            self.app.montar = False
        else:
            self.app.montar = True
        t_total = self.tempo_total_4_4() #+ t_add

        horas = t_total // 3600           
        minutos = (t_total % 3600) // 60            
        segundos = t_total % 60            
       
        self.text_result_4_4.delete("1.0", tk.END)
        self.text_result_4_4.insert(tk.END, f"Sequência de aplicação montada! \nA estimativa de duração é de {horas:02}:{minutos:02}:{segundos:02}\nClique em 'Iniciar' para começar o ensaio.", "Sucesso")
        #item_id = self.tree.get_children()[0]
        #valores = list(self.tree.item(item_id, "values"))  # Converte para lista
        #valores[6] = str(t_total)  # Agora pode alterar
        #self.tree.item(item_id, values=valores)  # Atualiza no Treeview
        string = "EN,"
        #Adiciona a tensão
        string += self.busca_item_4_4(0, 1)+","
        #Adiciona a frequência
        var5 = int(self.busca_item_4_4(0, 5))*10
        string += str(var5)+","
        #Adiciona a duração
        var3 = float(self.busca_item_4_4(0, 3))*10
        string += str(int(var3))+","
        #Adiciona a repetição
        string += self.busca_item_4_4(0, 4)+","
        #Adiciona o acoplamento
        if self.busca_item_4_4(0, 0) == "/ - CCP":
            var0 = "0"
        elif self.busca_item_4_4(0, 0) == "L":
            var0 = "1"
        elif self.busca_item_4_4(0, 0) == "N":
            var0 = "2"
        elif self.busca_item_4_4(0, 0) == "L-N":
            var0 = "3"
        elif self.busca_item_4_4(0, 0) == "PE":
            var0 = "4"
        elif self.busca_item_4_4(0, 0) == "L-PE":
            var0 = "5"
        elif self.busca_item_4_4(0, 0) == "N-PE":
            var0 = "6"
        elif self.busca_item_4_4(0, 0) == "L-N-PE":
            var0 = "7"
        else:
            messagebox.showwarning("Aviso", "Acoplamento incorreto!")
        string += var0+","
        if self.busca_item_4_4(0, 2) == "+":
            var2 = "0"
        elif self.busca_item_4_4(0, 2) == "-":
            var2 = "1"
        else:
            messagebox.showwarning("Aviso", "Polaridade incorreta!")
        string += var2+","
        string += str(t_total)+";"
        #self.envia_comando(string)
        try:
            # Captura as configurações da interface
            porta = self.app.conexao.combo_porta.get()
            baudrate = int(self.app.conexao.combo_baudrate.get())
            paridade = self.app.conexao.combo_paridade.get()
            data_bits = int(self.app.conexao.combo_data_bits.get())
            stop_bits = float(self.app.conexao.combo_stop_bits.get())
            timeout_user = int(self.app.conexao.combo_timeout_user.get())

            # Mapeamento da paridade para pyserial
            paridade_map = {
                "None": serial.PARITY_NONE,
                "Even": serial.PARITY_EVEN,
                "Odd": serial.PARITY_ODD,
                "Mark": serial.PARITY_MARK,
                "Space": serial.PARITY_SPACE
            }

            # Abre a porta serial com as configurações escolhidas
            s = serial.Serial(
                port=porta,
                baudrate=baudrate,
                bytesize=data_bits,
                parity=paridade_map[paridade],
                stopbits=stop_bits,
                timeout=timeout_user
            )
            # Envia comando
            s.write(self.app.conexao.comando('BS,1;'))
            time.sleep(1)
            s.write(self.app.conexao.comando(string))
            #time.sleep(1)
            s.close()
            #ucs_bool = True
            #self.text_result_4_4.delete("1.0", tk.END)
            #self.text_result_4_4.insert(tk.END, f"Parâmetros da Aplicação Sequencial enviados! \nClique em 'Iniciar' para começar o ensaio.")
        except Exception as e:
            return f"Erro: {e}"
        
        self.btn_4_4_montar_pp.config(state="disabled", bg="#B0B0B0")
        self.btn_4_4_enviar.config(state="disabled", bg="#B0B0B0")
        return

    def montar_4_4_pp(self):
        self.limpar_treeview()
        acoplamento = self.modo_acoplamento_4_4.get()
        amplitude = self.nivel_tensao_4_4.get()
        if acoplamento == "Com PE":
            self.tree.insert("", tk.END, values=("L", amplitude, "+", "15", "300", "5", "60"))
            self.tree.insert("", tk.END, values=("L", amplitude, "-", "15", "300", "5", "60"))
            self.tree.insert("", tk.END, values=("N", amplitude, "-", "15", "300", "5", "60"))
            self.tree.insert("", tk.END, values=("N", amplitude, "+", "15", "300", "5", "60"))
            self.tree.insert("", tk.END, values=("L-N", amplitude, "+", "15", "300", "5", "60"))
            self.tree.insert("", tk.END, values=("L-N", amplitude, "-", "15", "300", "5", "60"))
            self.tree.insert("", tk.END, values=("PE", amplitude, "-", "15", "300", "5", "60"))
            self.tree.insert("", tk.END, values=("PE", amplitude, "+", "15", "300", "5", "60"))
            self.tree.insert("", tk.END, values=("L-PE", amplitude, "+", "15", "300", "5", "60"))
            self.tree.insert("", tk.END, values=("L-PE", amplitude, "-", "15", "300", "5", "60"))
            self.tree.insert("", tk.END, values=("N-PE", amplitude, "-", "15", "300", "5", "60"))
            self.tree.insert("", tk.END, values=("N-PE", amplitude, "+", "15", "300", "5", "60"))
            self.tree.insert("", tk.END, values=("L-N-PE", amplitude, "+", "15", "300", "5", "60"))
            self.tree.insert("", tk.END, values=("L-N-PE", amplitude, "-", "15", "300", "5", "60"))
        elif acoplamento == "Sem PE":
            self.tree.insert("", tk.END, values=("L", amplitude, "+", "15", "300", "5", "60"))
            self.tree.insert("", tk.END, values=("L", amplitude, "-", "15", "300", "5", "60"))
            self.tree.insert("", tk.END, values=("N", amplitude, "-", "15", "300", "5", "60"))
            self.tree.insert("", tk.END, values=("N", amplitude, "+", "15", "300", "5", "60"))
            self.tree.insert("", tk.END, values=("L-N", amplitude, "+", "15", "300", "5", "60"))
            self.tree.insert("", tk.END, values=("L-N", amplitude, "-", "15", "300", "5", "60"))
        else: 
            messagebox.showwarning("Aviso", "Erro na montagem da sequência!")
        self.montar_4_4()
        self.btn_4_4_editar.config(state="normal", bg="#9EE8BE")
        self.btn_4_4_incluir.config(state="normal", bg="#9EE8BE")
        self.btn_4_4_excluir.config(state="normal", bg="#9EE8BE")
        self.btn_4_4_deletar.config(state="normal", bg="#9EE8BE")

    def informacoes_4_4_pp(self):
        messagebox.showwarning("Aviso", "As aplicações pré programadas são definidas com o padrão comum da IEC 61000-4-4, com os seguintes parâmetros:" \
        "\n\nTempo de aplicação do ensaio: 1 minuto" \
        "\n*Duração: 15 ms" \
        "\n*Repetição: 300 ms" \
        "\n*Frequência: 5 kHz" \
        "\n\nPara casos onde estes parâmetros devem ser ajustados, utilize a edição da sequência de ensaios no frame 'Aplicação sequencial'.")

    def salvar_4_4(self):
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

    def abrir_4_4(self):
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
                self.btn_4_4_excluir.config(state="disabled", bg="#B0B0B0")
                self.btn_4_4_deletar.config(state="disabled", bg="#B0B0B0")
                self.btn_4_4_montar.config(state="disabled", bg="#B0B0B0")
                self.btn_4_4_editar.config(state="disabled", bg="#B0B0B0")
                #self.btn_4_4_salvar.config(state="disabled", bg="red")
                #self.btn_4_4_deletarTab.config(state="disabled", bg="red")
            else:
                self.btn_4_4_excluir.config(state="normal", bg="#9EE8BE")
                self.btn_4_4_deletar.config(state="normal", bg="#9EE8BE")
                self.btn_4_4_montar.config(state="normal", bg="#9EE8BE")
                self.btn_4_4_editar.config(state="normal", bg="#9EE8BE")
                #self.btn_4_4_salvar.config(state="normal", bg="lime")
                #self.btn_4_4_deletarTab.config(state="normal", bg="lime")
                t_add = self.tempo_adicional_4_4()
                t_total = self.tempo_total_4_4()# + t_add

                horas = t_total // 3600           
                minutos = (t_total % 3600) // 60            
                segundos = t_total % 60            
            
                self.text_result_4_4.delete("1.0", tk.END)
                self.text_result_4_4.insert(tk.END, f"Arquivo {arquivo} aberto! \nA estimativa de duração é de {horas:02}:{minutos:02}:{segundos:02}\nClique em 'Iniciar' para começar o ensaio.", "Normal")
        
        
    def atualizar_tempo_4_4(self):
        if self.rodando:
            agora = time.time()
            self.tempo_decorrido = agora - self.tempo_inicial            
            horas = int(self.tempo_decorrido // 3600)            
            minutos = int((self.tempo_decorrido % 3600) // 60)            
            segundos = int(self.tempo_decorrido % 60)            
            self.label_tempo_decorrido.config(text=f"{horas:02}:{minutos:02}:{segundos:02}")            
            self.iec44_tab.after(1000, lambda:self.atualizar_tempo_4_4())

    def atualizar_seq_tempo_4_4(self):
        if self.rodando_seq:
            agora = time.time()            
            self.tempo_seq_decorrido = agora - self.tempo_seq_inicial           
            horas_seq = int(float(self.busca_item_4_4(0, 6)) // 3600)            
            minutos_seq = int((float(self.busca_item_4_4(0, 6)) % 3600) // 60)           
            segundos_seq = int(float(self.busca_item_4_4(0, 6)) % 60)            
            self.label_tempo_parcial.config(text=f"{horas_seq:02}:{minutos_seq:02}:{segundos_seq:02}")
            self.iec44_tab.after(1000, lambda:self.atualizar_seq_tempo_4_4())
            
    def iniciar_tempo_4_4(self):
        if not self.rodando:
            self.tempo_inicial = time.time()
            #self.tempo_seq_inicial = time.time()
            self.rodando = True
            self.atualizar_tempo_4_4()

    def iniciar_seq_tempo_4_4(self):
        if not self.rodando_seq:            
            self.tempo_seq_inicial = time.time()
            self.rodando_seq = True
            self.atualizar_seq_tempo_4_4()
    
    def pausar_tempo_4_4(self):
        if self.rodando:
            self.rodando = False
            self.tempo_decorrido = time.time() - self.tempo_inicial

    def pausar_seq_tempo_4_4(self):
        if self.rodando_seq:
            self.rodando_seq = False
            self.tempo_seq_decorrido = time.time() - self.tempo_seq_inicial
                
    def retomar_tempo_4_4(self):
        if not self.rodando:
            self.tempo_inicial = time.time() - self.tempo_decorrido
            #self.tempo_seq_inicial = time.time() - self.tempo_seq_decorrido
            self.rodando = True
            self.atualizar_tempo_4_4()

    def retomar_seq_tempo_4_4(self):
        if not self.rodando_seq:
            self.tempo_seq_inicial = time.time() - self.tempo_seq_decorrido
            self.rodando_seq = True
            self.atualizar_seq_tempo_4_4()
    
    def parar_tempo_4_4(self):
        self.rodando = False
        self.rodando_seq = False
        self.tempo_decorrido = 0
        self.tempo_seq_decorrido = 0
        self.label_tempo_decorrido.config(text="00:00:00")
        self.label_tempo_parcial.config(text="00:00:00")

    def parar_seq_tempo_4_4(self):
        self.rodando_seq = False
        self.tempo_seq_decorrido = 0
        self.label_tempo_parcial.config(text="00:00:00")        

    def verificar_tempo_4_4(self):
        if self.app.montar is False:
            limite = int(self.combo_tempo_4_4.get())
        else: 
            t_add = self.tempo_adicional_4_4()
            limite = self.tempo_total_4_4() #+ t_add
        #print("Limite_uni: ", limite)
        if self.tempo_decorrido <= limite:  
           # ainda dentro do tempo → agenda nova checagem
           self.iec44_tab.after(1000, self.verificar_tempo_4_4)
        else:
            # passou do tempo → pausa
            self.pausar_tempo_4_4()
            self.text_result_4_4.delete("1.0", tk.END)
            self.text_result_4_4.insert(tk.END, f"Aplicação finalizada.", "Sucesso")
            self.btn_4_4_iniciar.config(image = self.img_play, state="normal")
            self.btn_4_4_incluir.config(state="normal", bg="#9EE8BE")
            self.btn_4_4_excluir.config(state="normal", bg="#9EE8BE")
            self.btn_4_4_deletar.config(state="normal", bg="#9EE8BE")
            self.btn_4_4_editar.config(state="normal", bg="#9EE8BE")
            self.btn_4_4_montar.config(state="normal", bg="#9EE8BE")
            self.btn_4_4_enviar.config(state="normal", bg="#9EE8BE")
            self.btn_4_4_montar_pp.config(state="normal", bg="#9EE8BE")
            self.btn_4_4_salvar.config(state="normal", bg="#9EE8BE")
            self.btn_4_4_abrir.config(state="normal", bg="#9EE8BE")
            self.btn_4_4_deletarTab.config(state="normal", bg="#9EE8BE")
            self.btn_4_4_parar.config(image=self.img_stop_lime)
            self.btn_4_4_pausar.config(state="normal")
            self.btn_4_4_continuar.config(state="disabled", image=self.img_continue)
            self.app.prmt_4_4 = False
        self.app.lim = limite

    def verificar_seq_tempo_4_4(self):
        lim_seq = int(self.busca_item_4_4(0, 6))
        #print("Limite_seq: ", lim_seq)
        if self.tempo_seq_decorrido <= lim_seq:
            # ainda dentro do tempo → agenda nova checagem
            #self.retomar_seq_tempo_4_4()
            self.iec44_tab.after(1000, lambda:self.verificar_seq_tempo_4_4())
            #self.verificar_seq_tempo_4_4()
        #elif self.tempo_seq_decorrido > lim_seq:
            #self.parar_seq_tempo_4_4()
        else:
            # passou do tempo → pausa
            self.parar_seq_tempo_4_4()
            self.iniciar_seq_tempo_4_4()
            #montar = True


        
