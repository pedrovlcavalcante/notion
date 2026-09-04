import psutil
import time

def checar_threads_do_script(nome_script):
    # Percorre todos os processos rodando no computador
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            # Verifica se é um processo Python e se o nome do script está nos argumentos
            if cmdline and any(nome_script in arg for arg in cmdline):
                pid = proc.info['pid']
                # Obtém a lista de threads criadas por este processo
                threads_ativas = proc.threads()
                
                print(f"📌 Script encontrado: {nome_script} (PID: {pid})")
                print(f"🔢 Quantidade de threads ativas: {len(threads_ativas)}")
                
                for t in threads_ativas:
                    print(f"  -> ID da Thread: {t.id} | Tempo de CPU: {t.user_time}s")
                return
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    
    print(f"❌ O script '{nome_script}' não está em execução.")


def verificar_thread_externa(nome_script, id_da_thread):
    """
    Verifica se uma thread específica de um script externo ainda está ativa.
    """
    for proc in psutil.process_iter(['pid', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            # Identifica se o processo pertence ao script desejado
            if cmdline and any(nome_script in arg for arg in cmdline):
                # Obtém todas as threads atuais deste processo
                threads_atuais = proc.threads()
                
                # Extrai apenas os IDs (IDs de thread no psutil ficam em t.id)
                ids_ativos = [t.id for t in threads_atuais]
                
                if id_da_thread in ids_ativos:
                    return True
                else:
                    return False  # O script está rodando, mas a thread interna morreu
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
            
    return False  # O script inteiro foi fechado


def selenium_esta_rodando():
    # Nomes dos executáveis comuns de WebDrivers
    drivers_selenium = ["chromedriver", "geckodriver", "msedgedriver"]
    
    for proc in psutil.process_iter(['name']):
        try:
            # Converte o nome para minúsculo para evitar problemas no Windows/Linux
            nome_processo = proc.info['name'].lower()
            
            # Se encontrar o driver na lista de processos ativos
            if any(driver in nome_processo for driver in drivers_selenium):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return False

# Teste direto
if selenium_esta_rodando():
    print("🌐 Uma instância do Selenium foi detectada em execução!")
else:
    print("❌ Nenhuma instância do Selenium está rodando no momento.")
# Uso: substitua pelo nome do arquivo do outro script
# checar_threads_do_script("webhook.py")

# # --- EXEMPLO DE USO ---
# NOME_DO_SCRIPT = "outro_script.py"
# ID_PARA_MONITORAR = 15524 # Substitua pelo ID que você capturou anteriormente

# # Loop para monitorar em tempo real
# while True:
#     if verificar_thread_externa(NOME_DO_SCRIPT, ID_PARA_MONITORAR):
#         print(f"🔄 A thread {ID_PARA_MONITORAR} ainda está rodando...")
#     else:
#         print(f"🛑 A thread {ID_PARA_MONITORAR} parou ou o script foi encerrado!")
#         break
    
#     time.sleep(2)  # Aguarda 2 segundos antes de checar novamente

def teste():
    for i in range(10):
        print(i)
        time.sleep(1)
        i += 1
        if i == 10:
            return False

while teste():
    pass
    # print('Teste rodando')