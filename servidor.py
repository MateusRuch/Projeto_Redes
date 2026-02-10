import socket
import threading
import time
import json
import csv
import os
from datetime import datetime
from cryptography.fernet import Fernet

CHAVE_SECRETA = b'H71UvbUqhpFs-msgneVYD_2-j8hRDJFWxlnZOUedecQ='


class ServidorMonitoramento:
    def __init__(self, host='0.0.0.0', porta_udp=5000, porta_tcp=5001):
        self.host = host
        self.porta_udp = porta_udp
        self.porta_tcp = porta_tcp
        self.clientes = {}
        self.executando = True
        self.cifrador = Fernet(CHAVE_SECRETA)

        os.makedirs("logs", exist_ok=True)
        os.makedirs("relatorios", exist_ok=True)

        self.registrar_auditoria("Servidor iniciado.")

    def registrar_auditoria(self, mensagem): 
        caminho_arquivo = os.path.join("logs", "auditoria.log")
        with open(caminho_arquivo, "a") as arquivo:
            data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            arquivo.write(f"[{data_hora}] {mensagem}\n")

    def exportar_csv(self):
        try:
            nome_arquivo = f"relatorio_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
            caminho_completo = os.path.join("relatorios", nome_arquivo)

            with open(caminho_completo, mode='w', newline='') as arquivo:
                escritor = csv.writer(arquivo)
                escritor.writerow(['IP', 'Hostname', 'SO', 'Nucleos CPU', 'RAM Livre (GB)', 'Status', 'Interfaces'])

                for ip, info in self.clientes.items():
                    dados = info['dados']

                    try:
                        hostname = socket.gethostbyaddr(ip)[0] if info['status'] == 'ONLINE' else 'Desconhecido'
                    except:
                        hostname = "Desconhecido"

                    interfaces_texto = "; ".join([f"{i['nome']}({i['tipo']})" for i in dados.get('interfaces', [])])

                    escritor.writerow([
                        ip,
                        hostname,
                        dados.get('sistema_operacional', 'N/A'),
                        dados.get('nucleos_cpu', 0),
                        dados.get('ram_livre_gb', 0),
                        info['status'],
                        interfaces_texto
                    ])
            self.registrar_auditoria(f"Relatório exportado: {caminho_completo}")
            return caminho_completo
        except Exception as e:
            self.registrar_auditoria(f"Erro ao exportar CSV: {e}")
            return None

    def servico_descoberta_udp(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind((self.host, self.porta_udp))
            while self.executando:
                try:
                    dados, endereco = sock.recvfrom(1024)
                    if dados.decode() == "ONDE_ESTA_O_SERVIDOR?":
                        sock.sendto("AQUI_ESTA_O_SERVIDOR".encode(), endereco)
                except:
                    pass

    def gerenciar_conexao_cliente(self, conexao, endereco):
        try:
            with conexao:
                dados_criptografados = conexao.recv(8192)
                if dados_criptografados:
                    try:
                        dados_bytes = self.cifrador.decrypt(dados_criptografados)
                        pacote = json.loads(dados_bytes.decode('utf-8'))

                        self.clientes[endereco[0]] = {
                            "dados": pacote,
                            "ultimo_visto": time.time(),
                            "status": "ONLINE"
                        }
                        self.registrar_auditoria(f"Dados recebidos e autenticados de {endereco[0]}")
                    except Exception:
                        print(f"!!! TENTATIVA DE ACESSO NÃO AUTORIZADO DE {endereco[0]} !!!")
                        self.registrar_auditoria(f"ALERTA DE SEGURANÇA: Falha de descriptografia de {endereco[0]}")
        except Exception as e:
            print(f"Erro na conexão com {endereco}: {e}")

    def servico_servidor_tcp(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock_servidor:
            sock_servidor.bind((self.host, self.porta_tcp))
            sock_servidor.listen(5)
            while self.executando:
                try:
                    conexao, endereco = sock_servidor.accept()
                    threading.Thread(target=self.gerenciar_conexao_cliente, args=(conexao, endereco)).start()
                except:
                    pass

    def verificar_inatividade(self):
        while self.executando:
            agora = time.time()
            for ip, info in list(self.clientes.items()):
                if agora - info['ultimo_visto'] > 30:
                    if info['status'] == "ONLINE":
                        info['status'] = "OFFLINE"
                        self.registrar_auditoria(f"Cliente {ip} ficou OFFLINE (Timeout)")
            time.sleep(5)

    def loop_painel(self):
        ultima_exportacao = time.time()

        while self.executando:
            os.system('cls' if os.name == 'nt' else 'clear')

            ram_total = 0
            contagem_online = 0
            contagem_offline = 0

            print("-" * 150)
            print(f" SISTEMA DE MONITORAMENTO - {datetime.now().strftime('%H:%M:%S')}")
            print("-" * 150)

            print(f"{'IP':<16} | {'SO':<10} | {'CPU%':<6} | {'DISCO':<8} | {'RAM':<6} | {'INTERFACES':<35} | {'STATUS':<8}")

            print("-" * 150)

            for ip, info in self.clientes.items():
                dados = info['dados']
                status = info['status']

                if status == "ONLINE":
                    contagem_online += 1
                    ram_total += dados.get('ram_livre_gb', 0)
                else:
                    contagem_offline += 1

                interfaces = dados.get('interfaces', [])


                interfaces_texto = "; ".join(
                    [f"{i['nome']}({i['status']},{i['tipo']})" for i in interfaces[:4]]
                )

                uso_cpu = dados.get('uso_cpu_percent', 0)
                disco_livre = dados.get('disco_livre_gb', 0)
                ram_livre = dados.get('ram_livre_gb', 0)
                so_nome = dados.get('sistema_operacional', 'N/A')
                status = info['status']

                print(
                    f"{ip:<16} | {so_nome[:10]:<10} | {uso_cpu:<6} | {disco_livre:<8} | "
                    f"{ram_livre:<6} | {interfaces_texto:<35} | {status:<8}"
                )

            print("-" * 150)
            media_ram = round(ram_total / contagem_online, 2) if contagem_online > 0 else 0
            print(
                f"RESUMO: Online: {contagem_online} | Offline: {contagem_offline} | Média RAM Livre (Online): {media_ram} GB")
            print("-" * 150)
            print("Pressione Ctrl+C para encerrar o servidor.")

            if time.time() - ultima_exportacao > 60:
                self.exportar_csv()
                ultima_exportacao = time.time()
                print(">> Relatório CSV exportado automaticamente.")

            time.sleep(2)

    def iniciar(self):
        threading.Thread(target=self.servico_descoberta_udp, daemon=True).start()
        threading.Thread(target=self.servico_servidor_tcp, daemon=True).start()
        threading.Thread(target=self.verificar_inatividade, daemon=True).start()

        try:
            self.loop_painel()
        except KeyboardInterrupt:
            self.executando = False
            self.registrar_auditoria("Servidor encerrado pelo usuário.")
            print("\nEncerrando...")


if __name__ == "__main__":
    servidor = ServidorMonitoramento()
    servidor.iniciar()