import os
import sys
import time
import webbrowser
import threading
import subprocess

def main():
    print("=" * 60)
    print(" 📦  GESTÃO DE PRODUTOS • PRECIFICAÇÃO INTELIGENTE & NF-E")
    print("=" * 60)
    print("  Iniciando servidor de alta performance FastAPI + React...")
    
    # Define diretório base
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)

    # Verifica se o frontend/dist existe
    dist_dir = os.path.join(base_dir, "frontend", "dist")
    if not os.path.exists(dist_dir):
        print("  [Build] Compilando frontend React pela primeira vez...")
        try:
            subprocess.run(["npm", "run", "build"], cwd=os.path.join(base_dir, "frontend"), shell=True, check=True)
            print("  [Build] Frontend compilado com sucesso!")
        except Exception as e:
            print(f"  [Aviso] Falha ao compilar frontend: {e}")

    # Abre o navegador após 1.5s
    def abrir_navegador():
        time.sleep(1.5)
        url = "http://localhost:8000"
        print(f"\n  🚀 Aplicação pronta! Abrindo no navegador: {url}\n")
        webbrowser.open(url)

    threading.Thread(target=abrir_navegador, daemon=True).start()

    # Executa uvicorn
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, log_level="info")

if __name__ == "__main__":
    main()
