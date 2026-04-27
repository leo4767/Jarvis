import requests
import json
import os
import queue
import sounddevice as sd
import vosk
import pyttsx3
import subprocess

# ---------------- MEMORIA ----------------
def guardar_memoria(usuario, respuesta):
    with open("memoria.json", "r") as f:
        data = json.load(f)

    data["conversaciones"].append({
        "usuario": usuario,
        "jarvis": respuesta
    })

    with open("memoria.json", "w") as f:
        json.dump(data, f, indent=4)


def guardar_dato(clave, valor):
    with open("memoria.json", "r") as f:
        data = json.load(f)

    data["datos_usuario"][clave] = valor

    with open("memoria.json", "w") as f:
        json.dump(data, f, indent=4)


def cargar_memoria():
    with open("memoria.json", "r") as f:
        return json.load(f)

# ---------------- IA ----------------
def ia(prompt):
    data = cargar_memoria()
    memoria = data["conversaciones"][-5:]
    datos = data["datos_usuario"]

    contexto = ""
    for m in memoria:
        contexto += f"Usuario: {m['usuario']}\nJarvis: {m['jarvis']}\n"

    info_usuario = ""
    for k, v in datos.items():
        info_usuario += f"{k}: {v}\n"

    prompt_final = f"""
Eres Jarvis, asistente personal inteligente.

Datos del usuario:
{info_usuario}

Historial:
{contexto}

Usuario: {prompt}
"""

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llama3",
            "prompt": prompt_final,
            "stream": False
        }
    )

    return response.json()["response"]
def analizar_error(error):
    respuesta = ia(f"Explica y soluciona este error:\n{error}")
    return respuesta

# ---------------- VOZ ----------------
engine = pyttsx3.init()

def hablar(texto):
    print("Jarvis:", texto)
    engine.stop()
    engine.say(texto)
    engine.runAndWait()

# ---------------- ESCUCHAR ----------------
model = vosk.Model("model")
q = queue.Queue()

def callback(indata, frames, time, status):
    q.put(bytes(indata))

def escuchar():
    with sd.RawInputStream(samplerate=16000, blocksize=8000,
                           dtype='int16', channels=1, callback=callback):

        rec = vosk.KaldiRecognizer(model, 16000)

        while True:
            data = q.get()
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                texto = result.get("text", "")
                if texto:
                    print("Tú:", texto)
                    return texto

# ---------------- ACCIONES ----------------
def acciones(user):
    if "abre google" in user:
        os.system("start https://google.com")
        return "Abriendo Google"

    elif "abre bloc" in user:
        os.system("notepad")
        return "Abriendo bloc"

    elif "apaga pc" in user:
        return "Di confirmar apagado"

    elif "mi nombre es" in user:
        nombre = user.replace("mi nombre es", "").strip()
        guardar_dato("nombre", nombre)
        return f"Entendido, te llamaré {nombre}"

    elif "como me llamo" in user:
        data = cargar_memoria()
        nombre = data["datos_usuario"].get("nombre", "no lo sé aún")
        return f"Te llamas {nombre}"
    
    elif "abre" in user:
        programa = user.replace("abre", "").strip()
        os.system(f"start {programa}")
        return f"Abriendo {programa}"

    elif "ejecuta comando" in user:
        cmd = user.replace("ejecuta comando", "").strip()
        resultado = os.popen(cmd).read()
        return resultado if resultado else "Comando ejecutado"

    elif "terminal" in user:
        comando = user.replace("terminal", "").strip()

        try:
            resultado = subprocess.check_output(
                comando,
                shell=True,
                stderr=subprocess.STDOUT,
                text=True
            )
            return resultado

        except subprocess.CalledProcessError as e:
            return analizar_error(e.output)

    else:
        return None
# ---------------- LOOP ----------------
while True:
    texto = escuchar()

    if "jarvis" in texto or "hey jarvis" in texto:
        hablar("Te escucho")

        while True:
            comando = escuchar()

            if not comando:
                continue

            if "salir" in comando:
                hablar("Hasta luego")
                exit()

            accion = acciones(comando)

            if accion:
                respuesta = accion
            else:
                respuesta = ia(comando)

            guardar_memoria(comando, respuesta)
            hablar(respuesta)