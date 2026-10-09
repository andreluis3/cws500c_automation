"""
Detector e conector serial portátil para o CWS 500C ("Bob Esponja").

Compatibilidade pretendida: Windows (incluindo versões antigas que suportem
a versão do Python instalada) e Linux, usando pySerial.

Instalação:
    python -m pip install pyserial

Uso:
    python detector_cws.py

Observações:
- O Bluetooth precisa estar pareado/configurado no sistema operacional.
- O script prioriza portas que parecem Bluetooth, mas verifica a identidade
  do CWS enviando CC; e procurando uma resposta com "CWS500C".
- Não envia AR; automaticamente. Use a opção do menu quando desejar.
"""

import platform
import time

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    print("[ERRO] pySerial nao esta instalado.")
    print("Instale com: python -m pip install pyserial")
    raise SystemExit(1)


# Configuracao serial que funcionou no teste do CWS 500C.
DEFAULT_BAUDRATE = 9600
DEFAULT_BYTESIZE = serial.EIGHTBITS
DEFAULT_PARITY = serial.PARITY_NONE
DEFAULT_STOPBITS = serial.STOPBITS_ONE
DEFAULT_TIMEOUT = 2
READ_SIZE = 128
IDENTIFICATION_MARKER = b"CWS500C"


def verificar_sistema():
    sistema = platform.system()
    print("[INFO] Sistema operacional: {0}".format(sistema or "desconhecido"))
    if sistema not in ("Windows", "Linux", "Darwin"):
        print("[AVISO] Sistema nao testado especificamente; tentando usar pySerial.")
    return sistema


def listar_portas():
    """Lista portas detectadas pelo pySerial em qualquer sistema suportado."""
    portas = list(list_ports.comports())

    print("\n=== PORTAS SERIAIS DETECTADAS ===")
    if not portas:
        print("[AVISO] Nenhuma porta serial encontrada.")
        print("Verifique o pareamento Bluetooth, adaptadores USB/serial e permissoes.")
        return []

    for indice, porta in enumerate(portas, 1):
        descricao = getattr(porta, "description", None) or "sem descricao"
        fabricante = getattr(porta, "manufacturer", None) or "nao informado"
        hwid = getattr(porta, "hwid", None) or "nao informado"
        print("{0}. {1}".format(indice, porta.device))
        print("   Descricao: {0}".format(descricao))
        print("   Fabricante: {0}".format(fabricante))
        print("   HWID: {0}".format(hwid))

    return portas


def pontuar_porta(porta):
    """Heuristica de ordenacao; nao confirma que uma porta seja o CWS."""
    texto = " ".join([
        str(getattr(porta, "device", "") or ""),
        str(getattr(porta, "description", "") or ""),
        str(getattr(porta, "manufacturer", "") or ""),
        str(getattr(porta, "hwid", "") or ""),
    ]).lower()

    pontos = 0
    palavras_prioritarias = (
        "bluetooth", "rfcomm", "serial port", "standard serial",
        "spp", "wireless", "bob esponja", "cws500c", "cws 500c"
    )
    for palavra in palavras_prioritarias:
        if palavra in texto:
            pontos += 3

    # Algumas portas Linux Bluetooth aparecem como /dev/rfcommN.
    if "/dev/rfcomm" in texto:
        pontos += 5

    # No Windows, COM ports podem ser Bluetooth; COM por si só não prova isso.
    if texto.strip().startswith("com"):
        pontos += 1

    return pontos


def ordenar_portas(portas):
    """Coloca candidatas mais provaveis primeiro, sem descartar nenhuma."""
    return sorted(portas, key=pontuar_porta, reverse=True)


def montar_frame(comando):
    """
    Converte comando ASCII em frame: payload + checksum de 1 byte + LF.
    Regra replicada do projeto: (-sum(payload)) & 0xFF.
    """
    if not isinstance(comando, str):
        raise TypeError("O comando deve ser uma string.")
    payload = comando.encode("ascii")
    checksum = (-sum(bytearray(payload))) & 0xFF
    return payload + bytes(bytearray([checksum])) + b"\n"


def abrir_porta(nome_porta, baudrate=DEFAULT_BAUDRATE):
    """Abre a porta com as configuracoes seriais padrao do CWS."""
    # write_timeout existe nas versoes modernas do pySerial. O fallback
    # permite executar em instalacoes antigas que nao aceitam esse argumento.
    configuracao = {
        "port": nome_porta,
        "baudrate": baudrate,
        "bytesize": DEFAULT_BYTESIZE,
        "parity": DEFAULT_PARITY,
        "stopbits": DEFAULT_STOPBITS,
        "timeout": DEFAULT_TIMEOUT,
    }
    try:
        return serial.Serial(write_timeout=DEFAULT_TIMEOUT, **configuracao)
    except TypeError:
        return serial.Serial(**configuracao)


def ler_resposta(ser, janela_segundos=2.0):
    """
    Lê bytes até receber LF ou até expirar a janela.
    Funciona com respostas parciais; nao pressupoe que uma unica read()
    contenha toda a resposta.
    """
    inicio = time.time()
    dados = bytearray()

    while time.time() - inicio < janela_segundos:
        quantidade = ser.in_waiting if hasattr(ser, "in_waiting") else ser.inWaiting()
        bloco = ser.read(quantidade if quantidade > 0 else 1)

        if bloco:
            dados.extend(bytearray(bloco))
            if b"\n" in dados or b";" in dados:
                # Dá uma pequena oportunidade para bytes restantes chegarem.
                time.sleep(0.05)
                quantidade = ser.in_waiting if hasattr(ser, "in_waiting") else ser.inWaiting()
                if quantidade > 0:
                    dados.extend(bytearray(ser.read(quantidade)))
                break

    return bytes(dados)


def testar_identidade_cws(ser, nome_porta):
    """Envia CC; e aceita a porta como CWS apenas se a resposta o identificar."""
    frame = montar_frame("CC;")

    # Evita interpretar bytes antigos como resposta ao comando atual.
    if hasattr(ser, "reset_input_buffer"):
        ser.reset_input_buffer()
    elif hasattr(ser, "flushInput"):
        ser.flushInput()

    print("[TX] Texto: CC;")
    print("[TX] HEX:   {0}".format(" ".join("{0:02X}".format(b) for b in bytearray(frame))))
    ser.write(frame)
    ser.flush()

    resposta = ler_resposta(ser)
    if not resposta:
        print("[AVISO] Sem resposta em {0}.".format(nome_porta))
        return False, b""

    print("[RX] HEX:   {0}".format(" ".join("{0:02X}".format(b) for b in bytearray(resposta))))
    print("[RX] Texto: {0}".format(resposta.decode("ascii", errors="replace").strip()))

    if IDENTIFICATION_MARKER in resposta.upper():
        print("[OK] Bob Esponja/CWS 500C identificado na porta {0}.".format(nome_porta))
        return True, resposta

    print("[AVISO] Houve resposta, mas ela nao confirmou a identidade do CWS 500C.")
    return False, resposta


def descobrir_e_conectar():
    """
    Testa as portas candidatas em ordem de probabilidade.
    Retorna a serial aberta e a resposta de identificacao, ou (None, None).
    """
    portas = listar_portas()
    if not portas:
        return None, None

    candidatas = ordenar_portas(portas)
    print("\n[INFO] Vou testar as portas nesta ordem:")
    for porta in candidatas:
        print("  - {0} (prioridade {1})".format(porta.device, pontuar_porta(porta)))

    for porta in candidatas:
        print("\n[TESTE] Tentando {0} ...".format(porta.device))
        ser = None
        try:
            ser = abrir_porta(porta.device)
            print("[OK] Porta aberta com 9600 baud, 8N1, timeout 2 s.")
            identificado, resposta = testar_identidade_cws(ser, porta.device)
            if identificado:
                return ser, resposta
            ser.close()
        except (serial.SerialException, OSError, ValueError) as erro:
            print("[AVISO] Nao foi possivel usar {0}: {1}".format(porta.device, erro))
            if ser is not None:
                try:
                    ser.close()
                except Exception:
                    pass

    print("\n[ERRO] Nao consegui identificar o CWS 500C em nenhuma porta.")
    print("Confira se o Bluetooth esta pareado, se a porta serial correta existe")
    print("e se outro programa nao esta usando a porta.")
    return None, None


def enviar_comando(ser, comando):
    """Envia um comando informado pelo usuario e mostra TX/RX."""
    frame = montar_frame(comando)
    ser.write(frame)
    ser.flush()
    print("[TX] {0}".format(comando))
    print("[TX] HEX: {0}".format(" ".join("{0:02X}".format(b) for b in bytearray(frame))))

    resposta = ler_resposta(ser)
    if resposta:
        print("[RX] HEX: {0}".format(" ".join("{0:02X}".format(b) for b in bytearray(resposta))))
        print("[RX] Texto: {0}".format(resposta.decode("ascii", errors="replace").strip()))
    else:
        print("[AVISO] Nenhuma resposta recebida dentro do timeout.")
    return resposta


def menu_interativo(ser):
    """Mantém a sessão aberta até o usuario escolher sair."""
    try:
        while True:
            print("\n=== SESSAO CWS 500C ===")
            print("[1] Enviar CC; (identificacao)")
            print("[2] Enviar AR; (comando de desconexao/retorno usado no projeto)")
            print("[3] Enviar outro comando (uso consciente)")
            print("[4] Mostrar portas novamente")
            print("[0] Sair e fechar a serial")
            escolha = input("Escolha: ").strip()

            if escolha == "1":
                enviar_comando(ser, "CC;")
            elif escolha == "2":
                confirmar = input("Enviar AR; agora? (s/N): ").strip().lower()
                if confirmar == "s":
                    enviar_comando(ser, "AR;")
                    print("[INFO] A porta permanece aberta ate voce sair.")
                    print("[INFO] O efeito de AR; deve ser confirmado no equipamento.")
            elif escolha == "3":
                comando = input("Digite o comando completo, incluindo ';': ").strip()
                if not comando.endswith(";"):
                    print("[ERRO] O comando deve terminar com ';'. Nada foi enviado.")
                    continue
                confirmar = input("Enviar '{0}'? (s/N): ".format(comando)).strip().lower()
                if confirmar == "s":
                    enviar_comando(ser, comando)
            elif escolha == "4":
                listar_portas()
            elif escolha == "0":
                break
            else:
                print("[AVISO] Opcao invalida.")
    except KeyboardInterrupt:
        print("\n[INFO] Encerramento solicitado pelo teclado.")
    finally:
        if ser is not None:
            aberta = getattr(ser, "is_open", None)
            if aberta is None and hasattr(ser, "isOpen"):
                aberta = ser.isOpen()
            if aberta:
                ser.close()
                print("[OK] Porta serial fechada.")


def main():
    verificar_sistema()
    ser, _ = descobrir_e_conectar()
    if ser is None:
        print("\nNao houve conexao confirmada. Encerrando sem enviar AR; automaticamente.")
        return
    menu_interativo(ser)


if __name__ == "__main__":
    main()
