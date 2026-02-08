import subprocess
import sys

def instalar_e_testar():
    try:
        import psutil
        print("Sucesso! psutil já encontra-se nessa máquina.")
        print(f"CPU atual: {psutil.cpu_percent()}%")
    except ImportError:
        print("psutil não foi encontrado. Instalando agora...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])
        print("psutil instalado! rode o script novamente.")

instalar_e_testar()