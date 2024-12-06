import subprocess
import random
import os
import sys
import time
import requests
import json

# Configurações
VANITYSEARCH_PATH = "./vanitysearch"  # Caminho do executável VanitySearch
INPUT_FILE = "in.txt"  # Arquivo de entrada para o VanitySearch
OUTPUT_FILE = "out.txt"  # Arquivo de saída do VanitySearch

COIN_ADDRESSES = ["1BY8GQbnueYofwSuFAT3USAhGjPrkxDdW9"]  # Lista de endereços BTC alvo

# Definição dos limites gerais (17 dígitos hex)
OVERALL_START_HEX = "70000000000000000"
OVERALL_END_HEX = "7ffffffffffffffff"  # 17 dígitos

# Definição do tamanho do passo
STEP_SIZE_HEX = "10000000000"  # Pode ajustar conforme necessário

# Conversão para inteiros
OVERALL_START = int(OVERALL_START_HEX, 16)
OVERALL_END = int(OVERALL_END_HEX, 16)
STEP_SIZE = int(STEP_SIZE_HEX, 16)

# Cálculo total de lotes
TOTAL_STEPS = (OVERALL_END - OVERALL_START) // STEP_SIZE

# Configurações do Firebase
FIREBASE_DATABASE_URL = "https://btc-puzzle-de0d1-default-rtdb.firebaseio.com/"  # URL do seu Realtime Database
FIREBASE_API_KEY = "AIzaSyDP0ECdgY--W0D4u35tRPZ4kFTLSIyLylw"  # Seu API Key do Firebase

# Configurações do Telegram
TELEGRAM_BOT_TOKEN = "7434188832:AAHE8Bu-DTiYjzloJOXPsKyvi5cQ9yDDmYA"  # Substitua pelo seu token
TELEGRAM_CHAT_ID = "237456702"  # Substitua pelo seu chat_id

def send_telegram_message(message):
    """
    Envia uma mensagem via Telegram usando a Bot API.
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    try:
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            print(f"Falha ao enviar mensagem no Telegram: {response.text}")
    except Exception as e:
        print(f"Erro ao enviar mensagem no Telegram: {e}")

def load_used_ranges_firebase():
    """
    Carrega os ranges já utilizados a partir do Firebase.
    Retorna um conjunto com os starts em formato hexadecimal.
    """
    used_ranges = set()
    try:
        firebase_url = f"{FIREBASE_DATABASE_URL}VanitySearchRanges.json?auth={FIREBASE_API_KEY}"
        response = requests.get(firebase_url)
        if response.status_code == 200:
            data = response.json()
            if data:
                for key, value in data.items():
                    used_ranges.add(value['start'].upper())
        else:
            print(f"Falha ao carregar ranges do Firebase: {response.text}")
    except Exception as e:
        print(f"Erro ao carregar ranges do Firebase: {e}")
    return used_ranges

def save_range_firebase(start_hex, end_hex):
    """
    Salva um novo range no Firebase.
    """
    try:
        firebase_url = f"{FIREBASE_DATABASE_URL}VanitySearchRanges.json?auth={FIREBASE_API_KEY}"
        data = {
            'start': start_hex,
            'end': end_hex,
            'timestamp': int(time.time())
        }
        response = requests.post(firebase_url, json=data)
        if response.status_code != 200:
            print(f"Falha ao salvar range no Firebase: {response.text}")
    except Exception as e:
        print(f"Erro ao salvar range no Firebase: {e}")

def generate_random_start(overall_start, overall_end, step_size, used_ranges):
    """
    Gera um start aleatório dentro do intervalo geral, alinhado com o step_size.
    Garante que o range não tenha sido usado anteriormente.
    """
    max_steps = (overall_end - overall_start) // step_size
    if max_steps <= len(used_ranges):
        raise Exception("Todos os ranges possíveis foram explorados.")
    
    attempts = 0
    max_attempts = 1000000  # Para evitar loops infinitos

    while attempts < max_attempts:
        random_step = random.randint(0, max_steps - 1)
        start = overall_start + random_step * step_size
        start_hex = hex(start)[2:].upper().zfill(17)
        end = start + step_size
        end_hex = hex(end)[2:].upper().zfill(17)
        if start_hex not in used_ranges:
            return start, start_hex, end, end_hex
        attempts += 1

    raise Exception("Não foi possível encontrar um range não utilizado após muitas tentativas.")

def run_vanitysearch(range_start_hex, range_end_hex, addresses):
    """
    Executa o VanitySearch com o range especificado e exibe a saída em tempo real.
    Retorna True se a wallet foi encontrada, False caso contrário.
    """
    # Escreve os endereços no arquivo de entrada
    with open(INPUT_FILE, 'w') as f:
        for address in addresses:
            f.write(f"{address}\n")
    
    command = [
        VANITYSEARCH_PATH,
        "-t", "0",
        "-gpu",
        "-gpuId", "0",
        "-g", "1792",
        "-i", INPUT_FILE,
        "-o", OUTPUT_FILE,
        "--keyspace", f"{range_start_hex}:+" + STEP_SIZE_HEX
    ]

    try:
        # Usa subprocess.Popen para transmitir a saída em tempo real
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        # Lê e exibe cada linha da saída
        for line in process.stdout:
            print(line.strip())  # Exibe a saída no terminal
        
        process.wait()  # Aguarda o término do processo

        # Verifica se o arquivo de saída possui resultados
        if os.path.exists(OUTPUT_FILE) and os.path.getsize(OUTPUT_FILE) > 0:
            with open(OUTPUT_FILE, 'r') as f:
                output = f.read()
            return True, output
        else:
            return False, "Nenhuma wallet encontrada."
    except Exception as e:
        print(f"Erro ao executar VanitySearch: {e}")
        return False, str(e)

def main():
    print("Iniciando o script de automação do VanitySearch...")

    # Carrega os ranges já usados do Firebase
    used_ranges = load_used_ranges_firebase()
    total_used = len(used_ranges)
    print(f"{total_used} ranges já foram explorados anteriormente.")
    send_telegram_message(f"{total_used} ranges já foram explorados anteriormente.")

    try:
        while True:
            progress_percentage = (total_used / TOTAL_STEPS) * 100
            print(f"Progresso: {total_used}/{TOTAL_STEPS} ({progress_percentage:.5f}%)")

            # Gera um novo range aleatório não utilizado
            try:
                start_int, start_hex, end_int, end_hex = generate_random_start(
                    OVERALL_START, OVERALL_END, STEP_SIZE, used_ranges
                )
            except Exception as e:
                print(e)
                send_telegram_message(f"⚠️ *Erro:* {e}")
                sys.exit(1)

            print(f"Iniciando busca no range: {start_hex}:{end_hex}")

            # Executa o VanitySearch com o range gerado
            found, output = run_vanitysearch(start_hex, end_hex, COIN_ADDRESSES)

            if found:
                print("💥 Wallet encontrada!")
                print(output)
                send_telegram_message("💥 *Wallet encontrada!*")
                send_telegram_message(f"```\n{output}\n```")
                sys.exit(0)
            else:
                print(f"Range {start_hex}:{end_hex} concluído sem encontrar a wallet.")
                save_range_firebase(start_hex, end_hex)
                used_ranges.add(start_hex)
                total_used += 1
                send_telegram_message(f"✅ Range `{start_hex}:{end_hex}` concluído.\nNenhuma wallet encontrada.")

    except KeyboardInterrupt:
        print("\nScript interrompido pelo usuário.")
        send_telegram_message("⏹️ *Script interrompido pelo usuário.*")
        sys.exit(0)

if __name__ == "__main__":
    main()