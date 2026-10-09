"""
Terminal interativo para comandos do CWS 500C / protocolo CWS 500A descrito no manual.

IMPORTANTE:
- Confirme que o manual citado corresponde ao seu CWS 500C antes de confiar em
  todos os códigos/respostas operacionais.
- O programa nunca envia AR;.
- Cada envio exige confirmação explícita no terminal.
- AA e AS são comandos operacionais e também exigem confirmação.
- A sintaxe CN usada aqui é exatamente a informada: CN,U,AM,f,Cal,td,Pau;
- O frame enviado é payload ASCII + checksum de 1 byte + LF, conforme a lógica
  já documentada no projeto.
"""

from __future__ import annotations

import re
import time
from decimal import Decimal, InvalidOperation
from typing import Optional

import serial
import serial.tools.list_ports


BAUDRATE = 9600
TIMEOUT_SERIAL = 0.25
TIMEOUT_RESPOSTA = 2.0
PORTA_PADRAO_LINUX = "/dev/rfcomm0"

# Traduções baseadas no trecho de manual fornecido na conversa.
# Como o trecho copiado perdeu parte da formatação/alinhamento, confirme os
# códigos ambíguos com o PDF original antes de usar estas mensagens como
# diagnóstico definitivo.
FEEDBACK_RR = {
    "00": "Rotina de teste concluída corretamente.",
    "03": "Memória de calibração inválida.",
    "04": "Clipping: a tensão corrigida ficou fora dos limites; o manual informa saída ajustada para 60,0 V.",
    "05": "Calibração fora dos limites permitidos (descrição a confirmar no manual original).",
    "06": "Sinal Fail 1: o teste em execução é interrompido.",
    "10": "Erro de string/protocolo OU sinal Fail 2, conforme o alinhamento do trecho copiado. Confira o manual original.",
    "11": "Não é possível iniciar o teste, ou ele parou porque TEST ON não está ligado (confirmar código no manual original).",
    "13": "Nenhuma matriz selecionada ou matriz de acoplamento incorreta.",
    "14": "Um ou mais parâmetros foram limitados pelo equipamento; confira os valores efetivamente aceitos.",
    "15": "Erro de checksum OU erro de string/protocolo, conforme a versão/alinhamento do manual. Confira o manual original.",
    "19": "Erro de checksum ou de comunicação interna: confirme a associação exata no manual do seu equipamento.",
    "20": "Erro de comunicação interna. O trecho do manual recomenda desligar e reiniciar o equipamento; siga o procedimento seguro do laboratório.",
    "25": "Erro de limitação não corrigível.",
    "31": "Código RR,31 recebido. A descrição precisa ser confirmada no manual correspondente.",
    "32": "Código RR,32 recebido. A descrição precisa ser confirmada no manual correspondente.",
}

COMANDOS_MENU = {
    1: "CC — verificar interface/conexão e solicitar modo remoto",
    2: "CN — configurar parâmetros de teste normal",
    3: "NU — definir tensão",
    4: "NF — definir frequência",
    5: "NA — definir modulação",
    6: "ND — definir duração (dwell-time)",
    7: "NK — definir tensão e frequência",
    8: "Ler feedback pendente",
    9: "AA — iniciar rotina de teste (operacional)",
    10: "AS — parar teste em execução (operacional)",
}


def montar_frame(texto: str) -> bytes:
    """Monta payload ASCII + checksum de 1 byte + LF."""
    payload = texto.encode("ascii")
    checksum = (-sum(payload)) & 0xFF
    return payload + bytes([checksum]) + b"\n"


def listar_portas() -> list[str]:
    portas = list(serial.tools.list_ports.comports())
    print("\nPortas seriais detectadas:")
    if not portas:
        print("  Nenhuma porta listada pelo pySerial.")
    for porta in portas:
        print(f"  {porta.device}: {porta.description}")
    return [porta.device for porta in portas]


def escolher_porta() -> str:
    portas = listar_portas()
    sugestao = PORTA_PADRAO_LINUX if PORTA_PADRAO_LINUX in portas else (
        portas[0] if len(portas) == 1 else ""
    )
    texto = f"Porta serial exata"
    if sugestao:
        texto += f" [{sugestao}]"
    texto += " (ex.: /dev/rfcomm0 ou COM5): "
    entrada = input(texto).strip()
    return entrada or sugestao


def abrir_serial(porta: str) -> serial.Serial:
    return serial.Serial(
        port=porta,
        baudrate=BAUDRATE,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=TIMEOUT_SERIAL,
        write_timeout=2,
    )


def traduzir_resposta(linha: str) -> None:
    """Mostra a linha original e acrescenta uma explicação quando reconhecida."""
    texto = linha.strip()
    if not texto:
        return

    print(f"[RX] {texto}")

    # Respostas de erro/estado no formato RR,nn;
    match = re.search(r"RR\s*,\s*([0-9]{2})", texto, flags=re.IGNORECASE)
    if match:
        codigo = match.group(1)
        descricao = FEEDBACK_RR.get(codigo)
        if descricao:
            print(f"[FEEDBACK RR,{codigo}] {descricao}")
        else:
            print(f"[FEEDBACK RR,{codigo}] Código recebido; descrição ainda não cadastrada.")
        return

    if "CWS500C" in texto.upper() or "CWS500A" in texto.upper():
        print("[FEEDBACK CC] Resposta de identificação do equipamento detectada.")
        print("[INFO] Confira número de software, serviço e versão na resposta acima.")
    elif texto.upper().startswith(("RC,", "KR,")):
        print("[FEEDBACK] Resposta de calibração/memória recebida; interpretação detalhada ainda não implementada.")
    elif texto.upper() in {"CC;", "CN;", "NU;", "NF;", "NA;", "ND;", "NK;", "AA;", "AS;"}:
        print("[FEEDBACK] Eco do identificador do comando recebido.")
    else:
        print("[INFO] Resposta recebida; ainda sem tradução específica cadastrada.")


def ler_respostas(ser: serial.Serial, timeout: float = TIMEOUT_RESPOSTA) -> list[str]:
    """Lê linhas recebidas durante uma janela limitada; não presume sucesso por abrir a porta."""
    linhas: list[str] = []
    limite = time.monotonic() + timeout

    while time.monotonic() < limite:
        try:
            bruto = ser.readline()
        except serial.SerialException as erro:
            print(f"[ERRO SERIAL durante leitura] {erro}")
            break

        if not bruto:
            continue

        print(f"[RX HEX] {bruto.hex(' ')}")
        texto = bruto.decode("ascii", errors="replace").strip()
        if texto:
            linhas.append(texto)
            traduzir_resposta(texto)

    if not linhas:
        print("[AVISO] Nenhuma resposta recebida dentro do tempo de espera.")
    return linhas


def confirmar_envio(comando: str) -> bool:
    frame = montar_frame(comando)
    print("\nPrévia do envio:")
    print(f"  Comando lógico: {comando}")
    print(f"  Frame HEX:      {frame.hex(' ')}")
    print(f"  Frame bytes:    {frame!r}")
    resposta = input("Enviar este comando ao equipamento? [s/N]: ").strip().lower()
    return resposta in {"s", "sim", "y", "yes"}


def enviar_comando(ser: serial.Serial, comando: str) -> None:
    """Envia um único comando após confirmação e traduz as respostas recebidas."""
    if not confirmar_envio(comando):
        print("[CANCELADO] Nada foi enviado.")
        return

    frame = montar_frame(comando)
    try:
        ser.reset_input_buffer()
        quantidade = ser.write(frame)
        ser.flush()
        print(f"[TX] {quantidade} bytes enviados.")
        print(f"[TX HEX] {frame.hex(' ')}")
    except (serial.SerialException, serial.SerialTimeoutException) as erro:
        print(f"[ERRO DE ENVIO] {erro}")
        return

    print("[INFO] Aguardando feedback do equipamento...")
    ler_respostas(ser)


def ler_decimal(mensagem: str, minimo: str, maximo: str, casas: int) -> str:
    while True:
        entrada = input(f"{mensagem} ({minimo} a {maximo}): ").strip().replace(",", ".")
        try:
            valor = Decimal(entrada)
        except InvalidOperation:
            print("[ERRO] Digite um número válido.")
            continue

        if not valor.is_finite() or valor < Decimal(minimo) or valor > Decimal(maximo):
            print(f"[ERRO] Valor fora do intervalo {minimo} a {maximo}.")
            continue

        casas_digitadas = max(0, -valor.as_tuple().exponent)
        if casas_digitadas > casas:
            print(f"[ERRO] Use no máximo {casas} casas decimais.")
            continue

        return f"{valor:.{casas}f}"


def ler_inteiro(mensagem: str, minimo: int, maximo: int) -> int:
    while True:
        entrada = input(f"{mensagem} ({minimo} a {maximo}): ").strip()
        try:
            valor = int(entrada)
        except ValueError:
            print("[ERRO] Digite um número inteiro.")
            continue
        if not minimo <= valor <= maximo:
            print(f"[ERRO] Valor fora do intervalo {minimo} a {maximo}.")
            continue
        return valor


def criar_cn() -> str:
    
    print("\n=== Configuração CN ===")
    print("Informe os parâmetros de acordo com o manual do equipamento.")
    print("U é validado aqui pelo intervalo geral 0,2–60,0 V; as faixas/passos")
    print("específicos de tensão precisam ser conferidos na tabela original.")

    u = ler_decimal("Tensão U (V)", "0.2", "60.0", 1)
    am = ler_inteiro("Modulação AM (0=OFF, 1=2Hz, 2=400Hz, 3=1kHz, 4=Pulse)", 0, 4)
    frequencia = ler_decimal("Frequência f (kHz)", "0.009", "250.000", 3)
    cal = ler_inteiro("Calibração Cal (1=F1, 2=F2, 3=F3, 4=F4)", 1, 4)
    td = ler_decimal("Duração td (s)", "0.3", "9999.9", 1)
    pau = ler_inteiro("Estado após td (0=saída OFF, 1=saída ON)", 0, 1)

    comando = f"CN,{u},{am},{frequencia},{cal},{td},{pau};"
    print("\nResumo dos parâmetros:")
    print(f"  U={u} V | AM={am} | f={frequencia} kHz | Cal=F{cal} | td={td} s | Pau={pau}")
    return comando


def executar_menu(ser: serial.Serial) -> bool:
    print("\n========== CWS 500C | COMANDOS ==========")
    for numero, descricao in COMANDOS_MENU.items():
        print(f"{numero:2} - {descricao}")
    print(" 0 - Sair")

    entrada = input("\nSelecione uma opção (0-10): ").strip()
    if entrada == "0":
        return False

    try:
        opcao = int(entrada)
    except ValueError:
        print("[ERRO] Digite um número inteiro de 0 a 10.")
        return True

    if opcao not in COMANDOS_MENU:
        print("[ERRO] Opção inválida.")
        return True

    if opcao == 1:
        enviar_comando(ser, "CC;")
    elif opcao == 2:
        comando = criar_cn()
        enviar_comando(ser, comando)
    elif opcao == 3:
        u = ler_decimal("Nova tensão U (V)", "0.2", "60.0", 1)
        enviar_comando(ser, f"NU,{u};")
    elif opcao == 4:
        f = ler_decimal("Nova frequência f (kHz)", "0.009", "250.000", 3)
        enviar_comando(ser, f"NF,{f};")
    elif opcao == 5:
        am = ler_inteiro("Nova modulação AM (0=OFF, 1=2Hz, 2=400Hz, 3=1kHz, 4=Pulse)", 0, 4)
        enviar_comando(ser, f"NA,{am};")
    elif opcao == 6:
        td = ler_decimal("Novo dwell-time td (s)", "0.3", "9999.9", 1)
        enviar_comando(ser, f"ND,{td};")
    elif opcao == 7:
        u = ler_decimal("Tensão U (V)", "0.2", "60.0", 1)
        f = ler_decimal("Frequência f (kHz)", "0.009", "250.000", 3)
        enviar_comando(ser, f"NK,{u},{f};")
    elif opcao == 8:
        print("[INFO] Lendo respostas pendentes por até 2 segundos...")
        ler_respostas(ser)
    elif opcao == 9:
        print("[ATENÇÃO] AA inicia uma rotina de teste. O trecho enviado informa que")
        print("a rotina e os parâmetros precisam ter sido configurados previamente.")
        if input("Você já configurou a rotina e deseja iniciar o teste? [s/N]: ").strip().lower() in {"s", "sim", "y", "yes"}:
            enviar_comando(ser, "AA;")
        else:
            print("[CANCELADO] A rotina não foi iniciada.")
    elif opcao == 10:
        print("[ATENÇÃO] AS solicita a parada do teste em execução.")
        if input("Deseja realmente enviar AS;? [s/N]: ").strip().lower() in {"s", "sim", "y", "yes"}:
            enviar_comando(ser, "AS;")
        else:
            print("[CANCELADO] Nenhum comando de parada foi enviado.")

    return True


def main() -> None:
    print("=== Terminal de comandos CWS 500C ===")
    print("A conexão da porta não garante que o equipamento respondeu.")
    print("Todos os envios exigem confirmação; AR; não está implementado.")

    porta = escolher_porta()
    if not porta:
        print("[ERRO] Nenhuma porta informada. Encerrando sem enviar comandos.")
        return

    try:
        with abrir_serial(porta) as ser:
            print(f"[OK] Porta {porta} aberta com 9600, 8N1.")
            print("[INFO] Ainda é necessário validar a resposta real do equipamento.")

            while True:
                try:
                    if not executar_menu(ser):
                        break
                except KeyboardInterrupt:
                    print("\n[INFO] Interrompido pelo usuário.")
                    break
                except (serial.SerialException, serial.SerialTimeoutException) as erro:
                    print(f"[ERRO SERIAL] {erro}")
                    break
                except Exception as erro:
                    print(f"[ERRO INESPERADO] {type(erro).__name__}: {erro}")

    except (serial.SerialException, OSError) as erro:
        print(f"[ERRO AO ABRIR A PORTA] {erro}")
        print("[DICA] Confira a porta exata, permissões, pareamento/conexão e se outro programa está usando a porta.")


if __name__ == "__main__":
    main()
