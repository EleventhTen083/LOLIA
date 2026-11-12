import base64
import os
import sqlite3
import uuid
from datetime import datetime
import streamlit as st
import streamlit.components.v1 as components
from groq import Groq
from zoneinfo import ZoneInfo

# ==========================================
# 1. CONFIGURACIÓN GENERAL
# ==========================================
# ==========================================
# HORA LOCAL DE SAMIRA
# ==========================================

def obtener_hora_mexico():
    return datetime.now(ZoneInfo("America/Mexico_City"))


def obtener_saludo():
    hora_actual = obtener_hora_mexico().hour

    if 5 <= hora_actual < 12:
        return "Buenos días ☀️"

    elif 12 <= hora_actual < 19:
        return "Buenas tardes 🌤️"

    else:
        return "Buenas noches 🌙"
        
st.set_page_config(
    page_title="Samira - League of Legends",
    page_icon="⚔️",
    layout="wide"
)

st.title("⚔️ Samira - La Rosa del Desierto")

st.write(
    "¡Hey, invocador! Soy Samira. "
    "La vida es una aventura, y yo nací para el espectáculo. "
    "Pregúntame lo que quieras... ¡pero hazlo con estilo!"
)

# ==========================================
# 2. ESTILO VISUAL
# ==========================================

st.markdown("""
<style>

/* FONDO GENERAL */
.stApp {
    background: linear-gradient(135deg, #100c18, #281522, #111827);
    color: #ffffff !important;
}

/* TÍTULO DEL CHAT */
.chat-title {
    color: #e9b76b !important;
    font-size: 14px;
    margin-bottom: 10px;
}

/* MENSAJES DEL CHAT */
[data-testid="stChatMessage"] {
    background: rgba(120, 55, 70, 0.20) !important;
    border: 1px solid rgba(190, 100, 110, 0.25);
    border-radius: 15px;
    padding: 12px;
    margin-bottom: 12px;
}

/* TEXTO DE LOS MENSAJES */
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li,
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] {
    color: #ffffff !important;
}

/* CAMPO DONDE ESCRIBES */
[data-testid="stChatInput"] textarea {
    color: #222222 !important;
    -webkit-text-fill-color: #222222 !important;
    caret-color: #a34c5b !important;
    background-color: #ffffff !important;
}

/* TEXTO DE EJEMPLO DEL CAMPO */
[data-testid="stChatInput"] textarea::placeholder {
    color: #777777 !important;
    -webkit-text-fill-color: #777777 !important;
    opacity: 1 !important;
}

/* BORDE DEL CAMPO */
[data-testid="stChatInput"] {
    border: 1px solid #a34c5b !important;
    border-radius: 15px !important;
}

/* TEXTO SELECCIONADO */
::selection {
    background: #a83250;
    color: #ffffff;
}

/* SIDEBAR */
[data-testid="stSidebar"] {
    color: #ffffff !important;
}

</style>
""", unsafe_allow_html=True)


# ==========================================
# 3. SISTEMA DE MEMORIA (BASE DE DATOS)
# ==========================================

DB_PATH = "loli_memoria.db"

def conectar_db():
    return sqlite3.connect(DB_PATH)

def inicializar_memoria():
    with conectar_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversaciones (
                id TEXT PRIMARY KEY,
                fecha TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mensajes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversacion_id TEXT,
                rol TEXT,
                contenido TEXT,
                fecha TEXT,
                FOREIGN KEY (conversacion_id)
                REFERENCES conversaciones(id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recuerdos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                categoria TEXT,
                contenido TEXT UNIQUE,
                fecha TEXT
            )
        """)
        conn.commit()

def crear_conversacion():
    identificador = str(uuid.uuid4())
    with conectar_db() as conn:
        conn.execute("""
            INSERT INTO conversaciones (id, fecha)
            VALUES (?, ?)
        """, (identificador, datetime.now().isoformat()))
    return identificador

def guardar_mensaje(conversacion_id, rol, contenido):
    with conectar_db() as conn:
        conn.execute("""
            INSERT INTO mensajes
            (conversacion_id, rol, contenido, fecha)
            VALUES (?, ?, ?, ?)
        """, (
            conversacion_id,
            rol,
            contenido,
            datetime.now().isoformat()
        ))

def obtener_historial(conversacion_id):
    with conectar_db() as conn:
        cursor = conn.execute("""
            SELECT rol, contenido
            FROM mensajes
            WHERE conversacion_id = ?
            ORDER BY id ASC
        """, (conversacion_id,))
        return [
            {"role": rol, "content": contenido}
            for rol, contenido in cursor.fetchall()
        ]

def guardar_recuerdo(categoria, contenido):
    with conectar_db() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO recuerdos
            (categoria, contenido, fecha)
            VALUES (?, ?, ?)
        """, (
            categoria,
            contenido,
            datetime.now().isoformat()
        ))

def obtener_recuerdos():
    with conectar_db() as conn:
        cursor = conn.execute("""
            SELECT categoria, contenido
            FROM recuerdos
            ORDER BY id DESC
        """)
        return cursor.fetchall()

def eliminar_recuerdo(contenido):
    with conectar_db() as conn:
        conn.execute("""
            DELETE FROM recuerdos
            WHERE contenido = ?
        """, (contenido,))

def obtener_ultima_conversacion():
    with conectar_db() as conn:
        cursor = conn.execute("""
            SELECT id
            FROM conversaciones
            ORDER BY fecha DESC
            LIMIT 1
        """)
        resultado = cursor.fetchone()
        return resultado[0] if resultado else None

# Inicializar base de datos y estados
inicializar_memoria()

if "conversacion_id" not in st.session_state:
    ultima = obtener_ultima_conversacion()
    if ultima:
        st.session_state.conversacion_id = ultima
    else:
        st.session_state.conversacion_id = crear_conversacion()

if "messages" not in st.session_state:
    st.session_state.messages = obtener_historial(st.session_state.conversacion_id)
    if not st.session_state.messages:
        st.session_state.messages = []


# ==========================================
# 4. CONEXIÓN CON GROQ
# ==========================================

@st.cache_resource
def obtener_cliente():
    return Groq(
        api_key=st.secrets["GROQ_API_KEY"]
    )


# ==========================================
# 5. PERSONALIDAD DE SAMIRA
# ==========================================

INSTRUCCIONES = """
Eres Samira, la Rosa del Desierto de League of Legends.

PERSONALIDAD:
- Eres atrevida, segura de ti misma y competitiva.
- Tienes un carácter desafiante y divertido.
- Te encantan las aventuras y los combates.
- Hablas en español.
- Utilizas expresiones propias de Samira.
- Puedes utilizar emojis como ⚔️🔥😎.

COMPORTAMIENTO:
- Responde de manera natural y conversacional.
- Recuerda el contexto de la conversación.
- Responde preguntas sobre League of Legends.
- Explica estrategias, campeones, objetos y habilidades.
- También puedes conversar sobre otros temas.
- Si no sabes algo, dilo honestamente.
- No repitas siempre las mismas frases.
- Mantén respuestas claras y entretenidas.
SALUDOS:
- Utiliza el saludo que el sistema te proporciona.
- No inventes la hora ni cambies el saludo proporcionado.
- No saludes con buenas noches durante el día.
- Si ya saludaste al usuario en la conversación,
  no repitas el saludo en cada respuesta.
  
REGLAS DE ORTOGRAFÍA Y COMPRENSIÓN:. 
-Dependiendo de la hora del dia saluda conforme lo es si es de dia o de noche.
-Comprende las solicitudes aunque tengan errores ortográficos,
palabras incompletas, abreviaciones o falten acentos.
-Interpreta correctamente las preguntas aunque el usuario no utilice los signos de interrogación iniciales y finales.
-No rechaces una solicitud únicamente por tener errores de escritura o puntuación.
-Responde siempre con buena ortografía, utilizando correctamente acentos, comas, puntos y signos de interrogación.
-Cuando respondas una pregunta, utiliza los signos de interrogación correspondientes: ¿...?
7. Si una solicitud es demasiado ambigua para comprenderla,
   pregunta con tu personalidad qué quiso decir.

REGLAS DE ESCRITURA:

Antes de responder cualquier solicitud, verifica que el mensaje
del usuario tenga una escritura adecuada.

Comprueba:
- Ortografía y acentuación.
- Uso de mayúsculas.
- Signos de interrogación (¿?).
- Signos de exclamación (¡!).
- Puntuación básica.

Si el usuario escribe una pregunta sin los signos de interrogación,
tiene errores ortográficos o presenta una redacción incorrecta:

Si el usuario escribe una pregunta que no es sobre League of legends no respondas
e indicale que eso no es informacion sobre league of legends 

1. No respondas todavía la pregunta.
2. Indica con tu personalidad que debe corregir su escritura.
3. Muestra un ejemplo de cómo debería escribirla.
4. Espera a que el usuario envíe nuevamente su mensaje corregido.


No exijas una escritura perfecta ni rechaces abreviaciones
que no afecten la comprensión.
Nunca abandones tu personalidad de Samira.
"""


# ==========================================
# 6. FUNCIÓN DE INTELIGENCIA ARTIFICIAL
# ==========================================

def generar_respuesta(historial):
    cliente = obtener_cliente()
    recuerdos = obtener_recuerdos()

    saludo_actual = obtener_saludo()

    texto_recuerdos = "\n".join(
        [f"- {categoria}: {contenido}"
         for categoria, contenido in recuerdos]
    )

    if not texto_recuerdos:
        texto_recuerdos = "Todavía no hay recuerdos guardados."

    instrucciones_memoria = f"""
    {INSTRUCCIONES}
    HORA ACTUAL Y SALUDO:
    La hora local del sistema es:
    {obtener_hora_mexico().strftime("%H:%M")}

    El saludo correspondiente es:
    {saludo_actual}

    Si es el primer mensaje de la conversación,
    utiliza este saludo al dar la bienvenida.

    No inventes otro saludo según la hora.

    MEMORIA PERSONAL DEL USUARIO:
    Estos son los recuerdos almacenados de conversaciones anteriores:
    {texto_recuerdos}

    Utiliza esta información cuando sea relevante.
    No inventes recuerdos ni afirmes conocer datos que no aparecen aquí.
    """
    MEMORIA PERSONAL DEL USUARIO:
    Estos son los recuerdos almacenados de conversaciones anteriores:
    {texto_recuerdos}

    Utiliza esta información cuando sea relevante.
    No inventes recuerdos ni afirmes conocer datos que no aparecen aquí.
    """

    mensajes = [
        {
            "role": "system",
            "content": instrucciones_memoria
        }
    ]

    mensajes.extend(historial[-20:])

    respuesta = cliente.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=mensajes,
        temperature=0.8,
        max_tokens=1024
    )

    return respuesta.choices[0].message.content


def procesar_recuerdo(texto):
    texto = texto.strip()
    prefijo = "recuerda que"
    if texto.lower().startswith(prefijo):
        contenido = texto[len(prefijo):].strip()
        if contenido:
            guardar_recuerdo("Información personal", contenido)
            return (
                "¡Entendido! He guardado ese recuerdo "
                "en mi memoria, recluta. No se me escapará."
            )
    return None


# ==========================================
# 7. DISTRIBUCIÓN DE LA INTERFAZ
# ==========================================

col1, col2 = st.columns([1.2, 1])


# ==========================================
# BUSCADOR AUTOMÁTICO DEL MODELO 3D
# ==========================================

rutas_posibles = [
    os.path.join(os.path.dirname(__file__), "static", "samira.glb"),
    os.path.join(os.path.dirname(__file__), "LOLIA", "static", "samira.glb"),
    "static/samira.glb",
    "LOLIA/static/samira.glb"
]

ruta_modelo = None
for r in rutas_posibles:
    if os.path.exists(r):
        ruta_modelo = r
        break

data_url = ""
if ruta_modelo:
    with open(ruta_modelo, "rb") as f:
        bytes_modelo = f.read()
    b64_modelo = base64.b64encode(bytes_modelo).decode("utf-8")
    data_url = f"data:model/gltf-binary;base64,{b64_modelo}"

with col1:
    st.subheader("🔥 Samira Soul Fighters 🔥")

    if not data_url:
        st.error("⚠️ No se encontró el archivo samira.glb. Revisa que esté dentro de la carpeta 'static' en GitHub.")
    else:
        components.html(f"""
        <script type="module"
        src="https://ajax.googleapis.com/ajax/libs/model-viewer/4.0.0/model-viewer.min.js">
        </script>

        <div style="
            background: radial-gradient(circle, #542c37, #15101b);
            border-radius: 20px;
            padding: 12px;
        ">
            <model-viewer
                id="samira"
                src="{data_url}"
                camera-controls
                auto-rotate
                autoplay
                loop
                shadow-intensity="1"
                exposure="1"
                style="width:100%; height:500px; background:transparent;">
            </model-viewer>
        
            <div style="padding:12px; color:white;">
                <label for="animations">
                    ⚔️ Selecciona una animación:
                </label>
                <select id="animations" style="
                    width:100%;
                    padding:12px;
                    margin-top:10px;
                    border-radius:8px;
                    background:#29232f;
                    color:white;
                    border:1px solid #a34c5b;
                ">
                    <option>Buscando animaciones...</option>
                </select>

                <div style="display:flex; gap:10px; margin-top:12px;">
                    <button id="play" style="
                        flex:1;
                        padding:12px;
                        background:#9d3048;
                        color:white;
                        border:0;
                        border-radius:8px;
                        cursor:pointer;
                    ">▶ Reproducir</button>

                    <button id="pause" style="
                        flex:1;
                        padding:12px;
                        background:#39313f;
                        color:white;
                        border:0;
                        border-radius:8px;
                        cursor:pointer;
                    ">⏸ Pausar</button>
                </div>

                <p id="status" style="color:#ddd; font-size:13px;">
                    Cargando modelo 3D...
                </p>
            </div>
        </div>

        <script>
        const viewer = document.querySelector("#samira");
        const selector = document.querySelector("#animations");
        const status = document.querySelector("#status");

        viewer.addEventListener("load", () => {{
            const animations = viewer.availableAnimations;
            selector.innerHTML = "";
            if (animations.length === 0) {{
                selector.innerHTML = '<option>No se encontraron animaciones</option>';
                status.textContent = "Tu modelo no contiene animaciones disponibles.";
                return;
            }}
            animations.forEach((animation) => {{
                const option = document.createElement("option");
                option.value = animation;
                option.textContent = animation;
                selector.appendChild(option);
            }});
            viewer.animationName = animations[0];
            viewer.play();
            status.textContent = "Animaciones encontradas: " + animations.length;
        }});

        selector.addEventListener("change", () => {{
            viewer.animationName = selector.value;
            viewer.play();
            status.textContent = "Reproduciendo: " + selector.value;
        }});

        document.querySelector("#play").addEventListener("click", () => {{
            viewer.play();
        }});
        document.querySelector("#pause").addEventListener("click", () => {{
            viewer.pause();
        }});
        </script>
        """, height=730)

    st.caption("Puedes girar, acercar y alejar el modelo de Samira.")

    # ==========================================
    # NUEVO: ENTORNO 3D CON EL MODELO DE SAMIRA Y LÍMITES
    # ==========================================
    st.markdown("### 🏟️ Arena 3D de Samira")
    
    if not data_url:
        st.warning("No se pudo cargar a Samira en la arena porque no se encontró el modelo .glb")
    else:
        components.html(f"""
        <!-- Carga de Three.js y GLTFLoader -->
        <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js"></script>
        
        <div id="canvas-3d" style="
            width: 100%; 
            height: 320px; 
            border-radius: 15px; 
            overflow: hidden;
            border: 2px solid #a34c5b;
        "></div>

        <p style="color: #ddd; font-size: 12px; text-align: center; margin-top: 6px;">
            Usa <b>W, A, S, D</b> para mover a Samira en el espacio 3D. ¡Estás limitado por las paredes!
        </p>

        <script>
        // 1. Escena y Cámara
        const container = document.getElementById('canvas-3d');
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x15101b);

        const camera = new THREE.PerspectiveCamera(60, container.clientWidth / container.clientHeight, 0.1, 1000);
        camera.position.set(0, 6, 10);
        camera.lookAt(0, 1, 0);

        const renderer = new THREE.WebGLRenderer({{ antialias: true }});
        renderer.setSize(container.clientWidth, container.clientHeight);
        container.appendChild(renderer.domElement);

        // 2. Iluminación
        const ambientLight = new THREE.AmbientLight(0xffffff, 1.2);
        scene.add(ambientLight);

        const dirLight = new THREE.DirectionalLight(0xffffff, 1);
        dirLight.position.set(5, 10, 7);
        scene.add(dirLight);

        // 3. Arena y Límites Visuales
        const arenaSize = 12;
        const floorGeo = new THREE.PlaneGeometry(arenaSize, arenaSize);
        const floorMat = new THREE.MeshStandardMaterial({{ color: 0x281522, roughness: 0.6 }});
        const floor = new THREE.Mesh(floorGeo, floorMat);
        floor.rotation.x = -Math.PI / 2;
        scene.add(floor);

        // Paredes del borde (límites)
        const borderGeo = new THREE.BoxGeometry(arenaSize, 0.4, 0.2);
        const borderMat = new THREE.MeshBasicMaterial({{ color: 0xa34c5b }});
        
        const wall1 = new THREE.Mesh(borderGeo, borderMat);
        wall1.position.set(0, 0.2, -arenaSize/2);
        scene.add(wall1);

        const wall2 = new THREE.Mesh(borderGeo, borderMat);
        wall2.position.set(0, 0.2, arenaSize/2);
        scene.add(wall2);

        // 4. Cargar el Modelo .glb de Samira
        let player = null;
        let mixer = null;
        const loader = new THREE.GLTFLoader();

        loader.load('{data_url}', (gltf) => {{
            player = gltf.scene;
            
            // Ajustar la escala si el modelo es muy grande/pequeño
            player.scale.set(1.5, 1.5, 1.5);
            player.position.set(0, 0, 0);
            scene.add(player);

            // Si el modelo contiene animaciones, reproducir la primera
            if (gltf.animations && gltf.animations.length > 0) {{
                mixer = new THREE.AnimationMixer(player);
                const action = mixer.clipAction(gltf.animations[0]);
                action.play();
            }}
        }});

        // 5. Controles de Movimiento y Física de Límites
        const keys = {{ w: false, a: false, s: false, d: false }};
        const speed = 0.1;
        const limit = (arenaSize / 2) - 0.8;
        const clock = new THREE.Clock();

        window.addEventListener('keydown', (e) => {{
            if (e.key === 'w' || e.key === 'W' || e.key === 'ArrowUp') keys.w = true;
            if (e.key === 's' || e.key === 'S' || e.key === 'ArrowDown') keys.s = true;
            if (e.key === 'a' || e.key === 'A' || e.key === 'ArrowLeft') keys.a = true;
            if (e.key === 'd' || e.key === 'D' || e.key === 'ArrowRight') keys.d = true;
        }});

        window.addEventListener('keyup', (e) => {{
            if (e.key === 'w' || e.key === 'W' || e.key === 'ArrowUp') keys.w = false;
            if (e.key === 's' || e.key === 'S' || e.key === 'ArrowDown') keys.s = false;
            if (e.key === 'a' || e.key === 'A' || e.key === 'ArrowLeft') keys.a = false;
            if (e.key === 'd' || e.key === 'D' || e.key === 'ArrowRight') keys.d = false;
        }});

        // Bucle de Animación
        function animate() {{
            requestAnimationFrame(animate);

            const delta = clock.getDelta();
            if (mixer) mixer.update(delta);

            if (player) {{
                if (keys.w) {{ player.position.z -= speed; player.rotation.y = Math.PI; }}
                if (keys.s) {{ player.position.z += speed; player.rotation.y = 0; }}
                if (keys.a) {{ player.position.x -= speed; player.rotation.y = -Math.PI / 2; }}
                if (keys.d) {{ player.position.x += speed; player.rotation.y = Math.PI / 2; }}

                // Restricción estricta de límites (paredes transparentes/físicas)
                player.position.x = Math.max(-limit, Math.min(limit, player.position.x));
                player.position.z = Math.max(-limit, Math.min(limit, player.position.z));
            }}

            renderer.render(scene, camera);
        }}
        animate();
        </script>
        """, height=380)


# ==========================================
# 9. CHAT CON SAMIRA (COLUMNA 2)
# ==========================================

with col2:
    st.subheader("💬 Habla con Samira")
    st.markdown(
        '<div class="chat-title">'
        '⚔️ Conversación privada con la Rosa del Desierto'
        '</div>',
        unsafe_allow_html=True
    )

    col_title, col_clear = st.columns([3, 1])
    with col_title:
        st.caption("🟢 Samira está lista para hablar")
    with col_clear:
        if st.button("🗑️ Limpiar", key="clear_chat"):
            st.session_state.messages = []
            st.rerun()

    # Mostrar historial dentro de un contenedor
    with st.container(height=420, border=True):
        if not st.session_state.messages:
            with st.chat_message("assistant", avatar="⚔️"):
                st.markdown(
                    "**Samira:** ¡Ja! Bienvenido, invocador. "
                    "¿Qué aventura nos espera hoy? 🔥"
                )

        for message in st.session_state.messages:
            avatar = "⚔️" if message["role"] == "assistant" else "🧑"
            with st.chat_message(message["role"], avatar=avatar):
                st.markdown(message["content"])

    # Entrada del chat única
    if prompt := st.chat_input("Escribe un mensaje a Samira... ⚔️"):
        
        # 🔊 BUSCADOR AUTOMÁTICO DE AUDIO SEGURO
        rutas_audio_posibles = [
            "static/samira_passive_lol.mp3",
            "LOLIA/static/samira_passive_lol.mp3",
            os.path.join(os.path.dirname(__file__), "static", "samira_passive_lol.mp3"),
            os.path.join(os.path.dirname(__file__), "LOLIA", "static", "samira_passive_lol.mp3")
        ]
        
        ruta_audio_encontrada = None
        for r in rutas_audio_posibles:
            if os.path.exists(r):
                ruta_audio_encontrada = r
                break
                
        if ruta_audio_encontrada:
            st.audio(ruta_audio_encontrada, autoplay=True)

        # Guardar mensaje del usuario
        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })
        guardar_mensaje(st.session_state.conversacion_id, "user", prompt)

        with st.chat_message("user", avatar="🧑"):
            st.markdown(prompt)

        try:
            # Comprobar si el usuario quiere guardar un recuerdo
            recuerdo_respuesta = procesar_recuerdo(prompt)

            with st.chat_message("assistant", avatar="⚔️"):
                if recuerdo_respuesta:
                    respuesta = recuerdo_respuesta
                    st.markdown(respuesta)
                else:
                    with st.spinner("Samira está pensando..."):
                        response = generar_respuesta(st.session_state.messages)
                    
                    respuesta = st.write_stream(
                        (palabra + " " for palabra in response.split())
                    )

            # Guardar respuesta de Samira
            st.session_state.messages.append({
                "role": "assistant",
                "content": respuesta
            })
            guardar_mensaje(st.session_state.conversacion_id, "assistant", respuesta)

        except Exception as e:
            st.error(f"Error de conexión con la IA: {e}")
            st.info("Revisa tu API Key, tu conexión y la configuración de Groq.")


# ==========================================
# 10. SIDEBAR - MEMORIA Y RECUERDOS
# ==========================================

with st.sidebar:
    st.subheader("🧠 Memoria de LOLI.AI")
    recuerdos = obtener_recuerdos()

    if recuerdos:
        for categoria, contenido in recuerdos:
            st.write(f"**{categoria}**")
            st.caption(contenido)

            if st.button("Eliminar recuerdo", key=f"eliminar_{contenido}"):
                eliminar_recuerdo(contenido)
                st.rerun()
    else:
        st.info("Todavía no tengo recuerdos.")
