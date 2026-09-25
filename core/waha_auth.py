import time
import re
import subprocess
import requests

def get_waha_credentials():
    print("Verificando conexion con el contenedor Docker WAHA...")
    
    # Verificar si esta corriendo
    try:
        inspect = subprocess.check_output('docker inspect -f "{{.State.Running}}" waha', shell=True, text=True, stderr=subprocess.STDOUT, errors='ignore').strip()
    except Exception:
        inspect = "false"
        
    if "true" not in inspect.lower():
        print("Iniciando contenedor 'waha'...")
        subprocess.call('docker start waha', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Esperar hasta que el servidor HTTP responda y validar la clave exacta
    verified_pass = None
    for attempt in range(12):
        time.sleep(1)
        try:
            logs = subprocess.check_output('docker logs --tail 60 waha', shell=True, text=True, stderr=subprocess.STDOUT, errors='ignore')
            matches = re.findall(r'WAHA_DASHBOARD_PASSWORD=([a-zA-Z0-9]+)', logs)
            if matches:
                candidate = matches[-1]
                try:
                    r = requests.get('http://localhost:3000/dashboard/', auth=('admin', candidate), timeout=1.5)
                    if r.status_code in (200, 302):
                        verified_pass = candidate
                        break
                except Exception:
                    pass
        except Exception:
            pass

    print("")
    print("==============================================================================")
    print("CREDENCIALES ACTIVAS Y VERIFICADAS DE WHATSAPP (WAHA):")
    print("==============================================================================")
    print("  Panel Web:   http://localhost:3000/dashboard/")
    print("  Usuario:     admin")
    if verified_pass:
        print(f"  Contrasena:  {verified_pass}  [VERIFICADA EN VIVO]")
    else:
        print("  Contrasena:  (No requerida o consulte 'docker logs --tail 20 waha')")
    print("==============================================================================")
    print("")
    print("Instrucciones:")
    print("1. Abra http://localhost:3000/dashboard/ en su navegador.")
    print("2. Ingrese el Usuario 'admin' y la Contrasena mostrada arriba.")
    print("3. Inicie la sesion 'default' y escanee el codigo QR con WhatsApp.")
    print("")

if __name__ == "__main__":
    get_waha_credentials()
