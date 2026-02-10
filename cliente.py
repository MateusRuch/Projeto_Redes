import socket
import platform
import psutil
import time
import json
from cryptography.fernet import Fernet

CHAVE_SECRETA = b'H71UvbUqhpFs-msgneVYD_2-j8hRDJFWxlnZOUedecQ='

class ClienteMonitoramento:
    def __init__(self, porta_udp=5000, porta_tcp=5001):
        self.porta_udp = porta_udp
        self.porta_tcp = porta_tcp
        self.ip_servidor = None
        self.cifrador = Fernet(CHAVE_SECRETA)

    def descobrir_servidor(self):
        print("Buscando servidor via Broadcast...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(3)

        try:
            sock.sendto("ONDE_ESTA_O_SERVIDOR?".encode(), ('<broadcast>', self.porta_udp))
            dados, endereco = sock.recvfrom(1024)
            if dados.decode() == "AQUI_ESTA_O_SERVIDOR":
                self.ip_servidor = endereco[0]
                print(f"Servidor encontrado: {self.ip_servidor}")
        except Exception:
            print("Servidor não respondeu. Tentando novamente...")
        finally:
            sock.close()

    def obter_info_interfaces(self):
        lista_interfaces = []
        enderecos = psutil.net_if_addrs()
        estatisticas = psutil.net_if_stats()

        for nome, lista_ends in enderecos.items():
            status = "UP" if nome in estatisticas and estatisticas[nome].isup else "DOWN"

            tipo = "ETHERNET"
            nome_lower = nome.lower()
            if "lo" in nome_lower or "loopback" in nome_lower:
                tipo = "LOOPBACK"
            elif "wlan" in nome_lower or "wi-fi" in nome_lower or "wireless" in nome_lower:
                tipo = "WIFI"

            for end in lista_ends:
                if end.family == socket.AF_INET:
                    lista_interfaces.append({
                        "nome": nome,
                        "ip": end.address,
                        "status": status,
                        "tipo": tipo
                    })
        return lista_interfaces

    def coletar_metricas(self):
        return {
            "sistema_operacional": f"{platform.system()} {platform.release()}",
            "nucleos_cpu": psutil.cpu_count(),
            "ram_livre_gb": round(psutil.virtual_memory().available / (1024 ** 3), 2),
            "disco_livre_gb": round(psutil.disk_usage('/').free / (1024 ** 3), 2),
            "interfaces": self.obter_info_interfaces()
        }

    def enviar_dados(self, dados):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                s.connect((self.ip_servidor, self.porta_tcp))

                json_str = json.dumps(dados)
                carga_criptografada = self.cifrador.encrypt(json_str.encode('utf-8'))

                s.sendall(carga_criptografada)
                print("Dados criptografados enviados com sucesso.")
        except Exception as e:
            print(f"Erro ao enviar TCP: {e}")
            self.ip_servidor = None

    def executar(self):
        print("Cliente de Monitoramento Iniciado.")
        while True:
            if not self.ip_servidor:
                self.descobrir_servidor()
            else:
                dados = self.coletar_metricas()
                self.enviar_dados(dados)
            time.sleep(5)

if __name__ == "__main__":
    cliente = ClienteMonitoramento()
    cliente.executar()