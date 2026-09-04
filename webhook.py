from flask import Flask, request, jsonify
import threading
from funcoes_webhook import *

app = Flask(__name__)

monitor = threading.Thread(target=trabalhador_fila, daemon=True, name="Monitor")
monitor.start()

@app.route('/', methods=['POST'])
def receber_webhook():
    dados = request.json
    print("Webhook recebido no terminal. Respondendo ao servidor externo...")

    fila_tarefas.put(dados)

    # Dispara a função pesada em uma linha de execução paralela (Thread)
    thread_impressão = threading.Thread(target=processar_dados_webhook, args=(dados,), name="Impressão")
    thread_impressão.start()

    # Retorna IMEDIATAMENTE o status 200. O servidor externo para de reenviar!
    return jsonify({"status": "sucesso", "mensagem": "Webhook recebido e em processamento!"}), 200

@app.route('/webhook', methods=['POST'])
def receber_webhook_notion():
    dados = request.json
    print("Webhook recebido no terminal. Respondendo ao servidor externo...")

    # Retorna IMEDIATAMENTE o status 200. O servidor externo para de reenviar!
    return jsonify({"status": "sucesso", "mensagem": "Webhook recebido e em processamento!"}), 200

if __name__ == '__main__':
    # Roda o servidor localmente na porta 5000
    app.run(port=5000, debug=True, use_reloader=False)
    