import socket      # Comunicação em rede (UDP/TCP)
import threading   # Multiprocessamento para atender vários clientes simultâneos
import time        # Controle de tempo para timeouts e batimentos cardíacos
import json        # Decodificação do protocolo de aplicação (JSON)

class MonitorServer:
    """
    Classe que representa o Servidor Central de Inventário.
    Implementa Sockets Híbridos (UDP/TCP) e gerencia o ciclo de vida dos clientes.
    """
    def __init__(self, host='0.0.0.0', udp_port=5000, tcp_port=5001):
        self.host = host
        self.udp_port = udp_port
        self.tcp_port = tcp_port
        # Dicionário para armazenamento em memória dos agentes conectados
        self.clients = {}  #{ ip: { 'dados': {}, 'last_seen': timestamp, 'status': 'ONLINE' } }
        self.running = True

    def udp_discovery_service(self):
        """
        Serviço de Descoberta Automática. 
        Utiliza protocolo UDP por ser não orientado à conexão e permitir Broadcast.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind((self.host, self.udp_port))
            while self.running:
                data, addr = sock.recvfrom(1024)
                # Resposta ao sinal de 'handshake' inicial do cliente
                if data.decode() == "ONDE_ESTA_O_SERVIDOR?":
                    sock.sendto("AQUI_ESTA_O_SERVIDOR".encode(), addr)

    def handle_client_connection(self, conn, addr):
        """
        Trata o fluxo de dados individual de cada cliente via TCP.
        Iniciado em uma nova Thread para garantir a escalabilidade do servidor.
        """
        try:
            with conn:
                dados_brutos = conn.recv(4096) # Buffer de recepção
                if dados_brutos:
                    pacote = json.loads(dados_brutos.decode('utf-8'))
                    
                    # Atualiza ou insere o registro do cliente na base de dados
                    self.clients[addr[0]] = {
                        "dados": pacote,
                        "last_seen": time.time(),
                        "status": "ONLINE"
                    }
                    self.exibir_dashboard_consolidado()
        except Exception as e:
            print(f"[ERRO] Falha no processamento do cliente {addr[0]}: {e}")

    def tcp_server_service(self):
        """Serviço de escuta TCP para recebimento do inventário."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
            server_sock.bind((self.host, self.tcp_port))
            server_sock.listen(10) # Fila de espera para novas conexões
            while self.running:
                conn, addr = server_sock.accept()
                # Delegação da conexão para uma thread específica (Concorrência)
                threading.Thread(target=self.handle_client_connection, args=(conn, addr)).start()

    def check_timeouts(self):
        """
        Verifica a vivacidade dos clientes.
        Se o 'last_seen' for superior a 30s, o cliente é marcado como OFFLINE.
        """
        while self.running:
            now = time.time()
            for ip, info in list(self.clients.items()):
                if now - info['last_seen'] > 30 and info['status'] == "ONLINE":
                    info['status'] = "OFFLINE"
                    print(f"\n[ALERTA] Cliente {ip} perdido (Timeout de 30s).")
            time.sleep(5)

    def exibir_dashboard_consolidado(self):
        """
        Calcula médias globais e apresenta o status da rede.
        """
        clientes_online = [c for c in self.clients.values() if c['status'] == "ONLINE"]
        total = len(clientes_online)

        print("\n" + "="*50)
        print(f" DASHBOARD DE MONITORAMENTO - {time.strftime('%H:%M:%S')} ")
        print(f" Agentes Registrados: {len(self.clients)} | Agentes Online: {total}")
        
        if total > 0:
            #Cria variáveis para acumular a soma
            soma_ram = 0
            soma_disco = 0

            # Passa por cada cliente online e soma seus valores
            for cliente in clientes_online:
                # Acessa o dicionário de dados do cliente atual
                dados = cliente['dados']
                
                # Acumula os valores
                soma_ram   += dados['ram_livre_gb']
                soma_disco += dados['disco_livre_gb']

            #Calcula a média final (Soma Total / Quantidade de Clientes)
            media_ram = soma_ram / total
            media_disco = soma_disco / total
            
            print(f" Média de Memória RAM Livre: {media_ram:.2f} GB")
            print(f" Média de Espaço em Disco:  {media_disco:.2f} GB")
        
        print("="*50)

    def start(self):
        """Orquestrador das threads de serviço."""
        print(f"[*] Servidor pronto. Aguardando sinalização UDP/TCP...")
        
        # Inicialização das threads de background
        threads = [
            threading.Thread(target=self.udp_discovery_service, daemon=True),
            threading.Thread(target=self.tcp_server_service, daemon=True),
            threading.Thread(target=self.check_timeouts, daemon=True)
        ]
        
        for t in threads:
            t.start()

        try:
            while True: time.sleep(1) # Mantém a thread principal viva
        except KeyboardInterrupt:
            self.running = False
            print("\n[FECHANDO] Encerrando serviços do servidor...")

if __name__ == "__main__":
    servidor = MonitorServer()
    servidor.start()