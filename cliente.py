import socket      # Para comunicação de rede (UDP e TCP)
import psutil      # Para extração de métricas de hardware 
import platform    # Para identificação do Sistema Operacional
import time        # Para controle do intervalo de 'Hello' 
import json        # Para serialização dos dados 

class AgenteMonitoramento:
    """
    Classe Agente (Cliente) responsável pela coleta de inventário e 
    transmissão periódica para o servidor central.
    """
    def __init__(self, porta_udp=5000, porta_tcp=5001):
        self.porta_udp = porta_udp
        self.porta_tcp = porta_tcp
        self.ip_servidor = None  # Será preenchido via descoberta automática

    def descobrir_servidor(self):
        """
        Executa a descoberta automática via UDP Broadcast.
        Evita a necessidade de configurar IPs manualmente em redes dinâmicas.
        """
        print("[UDP] Buscando servidor na rede local...")
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.settimeout(5.0) # Aguarda até 5 segundos por uma resposta
            
            try:
                # Envia mensagem para o endereço de broadcast.
                s.sendto("ONDE_ESTA_O_SERVIDOR?".encode(), ('<broadcast>', self.porta_udp))
                data, addr = s.recvfrom(1024)
                
                if data.decode() == "AQUI_ESTA_O_SERVIDOR":
                    self.ip_servidor = addr[0]
                    print(f"[SUCESSO] Servidor encontrado em: {self.ip_servidor}")
            except socket.timeout:
                print("[AVISO] Nenhum servidor respondeu ao broadcast.")
            except Exception as e:
                print(f"[ERRO] Falha na descoberta UDP: {e}")

    def coletar_inventario(self):
        """
        Realiza a leitura dos sensores de hardware usando psutil.
        """
        # Captura dados de interfaces de rede e seu status
        interfaces_info = []
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()

        for nome, enderecos in addrs.items():
            status = "UP" if nome in stats and stats[nome].isup else "DOWN"
            for end in enderecos:
                if end.family == socket.AF_INET: # Somente IPv4
                    interfaces_info.append({
                        "interface": nome,
                        "ip": end.address,
                        "status": status
                    })

        # Estrutura o pacote de dados para o servidor
        payload = {
            "so": f"{platform.system()} {platform.release()}",
            "cpu_logica": psutil.cpu_count(logical=True),
            "ram_livre_gb": round(psutil.virtual_memory().available / (1024**3), 2),
            "disco_livre_gb": round(psutil.disk_usage('/').free / (1024**3), 2),
            "interfaces": interfaces_info
        }
        return payload

    def enviar_dados_tcp(self):
        """
        Estabelece conexão TCP para envio garantido do inventário.
        """
        try:
            dados = self.coletar_inventario()
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                s.connect((self.ip_servidor, self.porta_tcp))
                s.sendall(json.dumps(dados).encode('utf-8'))
                print(f"[TCP] Dados enviados para {self.ip_servidor}")
        except Exception as e:
            print(f"[ERRO] Falha na conexão TCP: {e}")
            # Resetamos o IP para tentar uma nova descoberta caso o servidor tenha caído
            self.ip_servidor = None

    def iniciar(self):
        """Loop principal de funcionamento do agente."""
        print("=== Agente de Monitoramento Iniciado ===")
        while True:
            if not self.ip_servidor:
                self.descobrir_servidor()
            else:
                self.enviar_dados_tcp()
            
            # Intervalo de 10 segundos entre envios (Mecanismo de Hello)
            time.sleep(10)

if __name__ == "__main__":
    agente = AgenteMonitoramento()
    agente.iniciar()