
import time
import serial
import serial.tools.list_ports

PORTA = "/dev/rfcomm0" # Troque pela COM do Bob Esponja


def comando(texto: str) -> bytes:
    payload = texto.encode("ascii")
    checksum = (-sum(payload)) & 0xFF
    return payload + bytes([checksum]) + b"\n"


def listar_portas():
    print("Portas seriais encontradas:")
    for porta in serial.tools.list_ports.comports():
        print(f"  {porta.device}: {porta.description}")


def main():
    listar_portas()

    print(f"\nTentando abrir {PORTA}...")

    try:
        with serial.Serial(
            port=PORTA,
            baudrate=9600,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=2,
            write_timeout=2,
        ) as ser:
            print("[OK] Porta serial aberta.")

            tx = comando("CC;")
            print("[TX] Hexadecimal:", tx.hex(" "))
            print("[TX] Bytes:", repr(tx))

            ser.write(tx)
            ser.flush()

            print("[OK] Comando enviado. Aguardando resposta...")
            time.sleep(1)

            rx = ser.read(50)

            print("[RX] Hexadecimal:", rx.hex(" "))
            print("[RX] Bytes:", repr(rx))
            print("[RX] Texto:", rx.decode("ascii", errors="replace"))

            if rx:
                print("[INFO] Foram recebidos bytes.")
                print("[INFO] Ainda é necessário validar a resposta.")
            else:
                print("[AVISO] Nenhum byte recebido.")

    except serial.SerialException as erro:
        print(f"[ERRO SERIAL] {erro}")

    except Exception as erro:
        print(f"[ERRO] {erro}")


if __name__ == "__main__":
    main()
