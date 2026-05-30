from flask import (
    Flask,
    request,
    jsonify,
    render_template,
    redirect,
    session
)

import chromadb
import os
import uuid
import time
import re
import sqlite3
from datetime import datetime

from llama_index.llms.ollama import Ollama
from llama_index.core.llms import ChatMessage
from gtts import gTTS

# ==========================================
# APP
# ==========================================

app = Flask(__name__)

app.secret_key = "super_segredo_123"

MAX_MSG_LEN = 500

# ==========================================
# MÉDICOS AUTORIZADOS
# ==========================================

MEDICOS_AUTORIZADOS = {
    "03768364070": "gustavo",
    "98765432100": "Dra. Maria Santos",
    "55555555555": "Dr. Pedro Costa"
}

# ==========================================
# LLM
# ==========================================

llm = Ollama(
    model="llama3",
    request_timeout=300.0
)

# ==========================================
# CHROMADB
# ==========================================

client = chromadb.PersistentClient(
    path="./db"
)

collection = client.get_or_create_collection(
    name="triagem"
)

# ==========================================
# LIMPAR TEXTO
# ==========================================


def limpar_texto(texto):

    if not texto:
        return ""

    texto = str(texto)

    texto = texto.strip()

    texto = re.sub(
        r"\s+",
        " ",
        texto
    )

    return texto[:MAX_MSG_LEN]

# ==========================================
# VALIDAR CPF
# ==========================================


def validar_cpf(cpf):

    cpf = re.sub(r"\D", "", cpf)

    if len(cpf) != 11:
        return False

    if cpf == cpf[0] * 11:
        return False

    soma = 0

    for i in range(9):

        soma += int(cpf[i]) * (10 - i)

    digito = (soma * 10) % 11

    if digito == 10:
        digito = 0

    if digito != int(cpf[9]):
        return False

    soma = 0

    for i in range(10):

        soma += int(cpf[i]) * (11 - i)

    digito = (soma * 10) % 11

    if digito == 10:
        digito = 0

    if digito != int(cpf[10]):
        return False

    return True

# ==========================================
# BUSCAR CONTEXTO RAG
# ==========================================


def buscar_similares(texto):

    try:

        results = collection.query(
            query_texts=[texto],
            n_results=3
        )

        documentos = results.get(
            "documents",
            [[]]
        )[0]

        documentos = [

            limpar_texto(doc)

            for doc in documentos

            if doc

        ]

        if not documentos:
            return "Sem contexto clínico."

        return "\n".join(documentos[:3])

    except Exception as erro:

        print("Erro busca:", erro)

        return "Erro na busca."

# ==========================================
# IA
# ==========================================


def responder(texto):

    texto = limpar_texto(texto)

    contexto = buscar_similares(texto)

    prompt = f"""
Você é um profissional especialista em triagem clínica.

OBJETIVO:
Classificar o risco do paciente.

REGRAS:
- Não inventar sintomas
- Ser objetivo
- Priorizar segurança
- Informar quando faltarem dados

CLASSIFICAÇÃO:
- Vermelho
- Laranja
- Amarelo
- Verde
- Azul

FORMATO:

Cor:
Justificativa:
Conduta:

DADOS:
{texto}

CONTEXTO:
{contexto}
"""

    mensagens = [

        ChatMessage(
            role="system",
            content="Especialista em triagem clínica."
        ),

        ChatMessage(
            role="user",
            content=prompt
        )

    ]

    resposta = llm.chat(mensagens)

    return resposta.message.content.strip()

# ==========================================
# LIMPAR ÁUDIOS ANTIGOS
# ==========================================


def limpar_audios():

    pasta = "static/audio"

    if not os.path.exists(pasta):
        return

    agora = time.time()

    for arquivo in os.listdir(pasta):

        if (
            arquivo.startswith("audio_")
            and arquivo.endswith(".mp3")
        ):

            caminho = os.path.join(
                pasta,
                arquivo
            )

            try:

                if os.path.getmtime(caminho) < (agora - 3600):

                    os.remove(caminho)

            except Exception:
                pass


# ==========================================
# SQLITE DB PARA RESPOSTAS DA IA
# ==========================================

DB_PATH = os.path.join("db", "ia_respostas.sqlite3")


def init_db():

    os.makedirs("db", exist_ok=True)

    conn = sqlite3.connect(DB_PATH)

    try:

        conn.execute(

            """
            CREATE TABLE IF NOT EXISTS respostas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT,
                cpf TEXT,
                tipo TEXT,
                pergunta TEXT,
                resposta TEXT,
                audio TEXT,
                created_at TEXT
            )
            """

        )

        conn.commit()

    finally:

        conn.close()


def salvar_resposta(nome, cpf, tipo, pergunta, resposta, audio_url=None):

    try:

        conn = sqlite3.connect(DB_PATH)

        conn.execute(

            "INSERT INTO respostas (nome, cpf, tipo, pergunta, resposta, audio, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",

            (

                nome,

                cpf,

                tipo,

                pergunta,

                resposta,

                audio_url,

                datetime.utcnow().isoformat()

            )

        )

        conn.commit()

    except Exception as e:

        print("Erro ao salvar resposta no DB:", e)

    finally:

        try:

            conn.close()

        except Exception:

            pass


def salvar_no_chroma(pergunta, resposta, usuario):

    try:

        if not pergunta or not resposta:

            return

        metadata = {

            "nome": usuario.get("nome", ""),

            "cpf": usuario.get("cpf", ""),

            "tipo": usuario.get("tipo", ""),

            "created_at": datetime.utcnow().isoformat(),

            "resposta": resposta

        }

        documento = f"PERGUNTA:\n{pergunta.strip()}\n\nRESPOSTA:\n{resposta.strip()}"

        collection.add(

            documents=[documento],

            metadatas=[metadata],

            ids=[str(uuid.uuid4())]

        )

    except Exception as e:

        print("Erro ao salvar no Chroma:", e)


# ==========================================
# ROTAS HTML
# ==========================================


@app.route("/")
@app.route("/login")
def login():

    return render_template(
        "login.html"
    )


@app.route("/triagem")
def triagem():

    if "usuario" not in session:

        return redirect("/login")

    return render_template(
        "triagem.html"
    )


@app.route("/medico")
def medico():

    if "usuario" not in session:

        return redirect("/login")

    usuario = session.get("usuario", {})

    if usuario.get("tipo") != "Medico":

        return redirect("/login")

    return render_template(
        "medico.html"
    )

# ==========================================
# API LOGIN
# ==========================================


@app.route("/api/login", methods=["POST"])
def api_login():

    try:

        data = request.get_json()

        if not data:

            return jsonify({
                "erro": "Dados inválidos"
            }), 400

        nome = limpar_texto(
            data.get("nome", "")
        )

        cpf = limpar_texto(
            data.get("cpf", "")
        )

        tipo = limpar_texto(
            data.get("tipo", "")
        )

        cpf = re.sub(r"\D", "", cpf)

        # VALIDAÇÕES

        if len(nome) < 3:

            return jsonify({
                "erro": "Nome inválido"
            }), 400

        if not validar_cpf(cpf):

            return jsonify({
                "erro": "CPF inválido"
            }), 400

        if tipo not in [
            "Autoatendimento",
            "Tecnico",
            "Medico"
        ]:

            return jsonify({
                "erro": "Tipo inválido"
            }), 400

        # VALIDA MÉDICO AUTORIZADO
        if tipo == "Medico":

            if cpf  not in MEDICOS_AUTORIZADOS:

                return jsonify({
                    "erro": "Médico não autorizado"
                }), 401

        # SESSÃO

        session["usuario"] = {

            "nome": nome,
            "cpf": cpf,
            "tipo": tipo

        }

        return jsonify({

            "ok": True,

            "usuario": session["usuario"]

        })

    except Exception as erro:

        print("Erro login:", erro)

        return jsonify({
            "erro": "Erro interno"
        }), 500

# ==========================================
# LOGOUT
# ==========================================


@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")

# ==========================================
# CHAT
# ==========================================


@app.route("/chat", methods=["POST"])
def chat():

    try:

        if "usuario" not in session:

            return jsonify({
                "erro": "Não autorizado"
            }), 401

        data = request.get_json()

        if not data:

            return jsonify({
                "erro": "Dados inválidos"
            }), 400

        texto = limpar_texto(
            data.get("mensagem", "")
        )

        if not texto:

            return jsonify({
                "erro": "Mensagem vazia"
            }), 400

        resposta = responder(texto)

        # ==========================================
        # ÁUDIO
        # ==========================================

        os.makedirs(
            "static/audio",
            exist_ok=True
        )

        nome_audio = (
            f"audio_{uuid.uuid4().hex}.mp3"
        )

        caminho_audio = os.path.join(
            "static/audio",
            nome_audio
        )

        audio_url = None

        try:

            gTTS(
                text=resposta[:800],
                lang="pt-br"
            ).save(caminho_audio)

            audio_url = (
                f"/static/audio/{nome_audio}"
            )

        except Exception as erro:

            print("Erro TTS:", erro)

        limpar_audios()

        # Salva no banco local de respostas para visualização pelo médico
        try:

            usuario = session.get("usuario")

            if usuario:

                salvar_resposta(

                    usuario.get("nome"),

                    usuario.get("cpf"),

                    usuario.get("tipo"),

                    texto,

                    resposta,

                    audio_url

                )

                salvar_no_chroma(texto, resposta, usuario)

        except Exception as e:

            print("Erro ao salvar resposta:", e)

        return jsonify({

            "resposta": resposta,

            "audio": audio_url

        })

    except Exception as erro:

        print("Erro geral:", erro)

        return jsonify({
            "erro": "Erro interno"
        }), 500


# API: listar respostas gravadas
@app.route("/api/respostas", methods=["GET"])
def api_respostas():

    try:

        conn = sqlite3.connect(DB_PATH)

        conn.row_factory = sqlite3.Row

        cur = conn.cursor()

        cur.execute(

            "SELECT id, nome, cpf, tipo, pergunta, resposta, audio, created_at FROM respostas ORDER BY created_at DESC LIMIT 200"

        )

        rows = cur.fetchall()

        result = []

        for r in rows:

            result.append({

                "id": r["id"],

                "nome": r["nome"],

                "cpf": r["cpf"],

                "tipo": r["tipo"],

                "pergunta": r["pergunta"],

                "resposta": r["resposta"],

                "audio": r["audio"],

                "created_at": r["created_at"]

            })

        return jsonify(result)

    except Exception as e:

        print("Erro listar respostas:", e)

        return jsonify([]), 500

    finally:

        try:

            conn.close()

        except Exception:

            pass


# API: atualizar resposta editada pelo médico
@app.route("/api/respostas/<int:id>", methods=["PUT"])
def api_atualizar_resposta(id):

    try:

        if "usuario" not in session:

            return jsonify({

                "erro": "Não autorizado"

            }), 401

        usuario = session.get("usuario", {})

        if usuario.get("tipo") != "Medico":

            return jsonify({

                "erro": "Apenas médico pode editar respostas"

            }), 403

        data = request.get_json()

        if not data:

            return jsonify({

                "erro": "Dados inválidos"

            }), 400

        nova_resposta = limpar_texto(

            data.get("resposta", "")

        )

        if not nova_resposta:

            return jsonify({

                "erro": "Resposta vazia"

            }), 400

        conn = sqlite3.connect(DB_PATH)

        conn.row_factory = sqlite3.Row

        cur = conn.cursor()

        cur.execute(

            "SELECT audio FROM respostas WHERE id = ?",

            (id,)

        )

        row = cur.fetchone()

        if not row:

            return jsonify({

                "erro": "Resposta não encontrada"

            }), 404

        audio_url = row["audio"]

        if audio_url:

            arquivo_antigo = audio_url.lstrip("/")

            if os.path.exists(arquivo_antigo):

                try:

                    os.remove(arquivo_antigo)

                except Exception as e:

                    print("Erro ao remover áudio antigo:", e)

        os.makedirs(

            "static/audio",

            exist_ok=True

        )

        nome_audio = f"audio_{uuid.uuid4().hex}.mp3"

        caminho_audio = os.path.join(

            "static/audio",

            nome_audio

        )

        novo_audio_url = None

        try:

            gTTS(

                text=nova_resposta[:800],

                lang="pt-br"

            ).save(caminho_audio)

            novo_audio_url = f"/static/audio/{nome_audio}"

        except Exception as erro:

            print("Erro TTS na edição:", erro)

        cur.execute(

            "UPDATE respostas SET resposta = ?, audio = ? WHERE id = ?",

            (

                nova_resposta,

                novo_audio_url,

                id

            )

        )

        conn.commit()

        return jsonify({

            "ok": True,

            "resposta": nova_resposta,

            "audio": novo_audio_url

        })

    except Exception as e:

        print("Erro ao atualizar resposta:", e)

        return jsonify({

            "erro": "Erro interno"

        }), 500


# API: enviar resposta existente para o Chroma
@app.route("/api/respostas/<int:id>/chroma", methods=["POST"])
def api_enviar_resposta_chroma(id):

    try:

        if "usuario" not in session:

            return jsonify({

                "erro": "Não autorizado"

            }), 401

        usuario = session.get("usuario", {})

        if usuario.get("tipo") != "Medico":

            return jsonify({

                "erro": "Apenas médico pode enviar para o Chroma"

            }), 403

        conn = sqlite3.connect(DB_PATH)

        conn.row_factory = sqlite3.Row

        cur = conn.cursor()

        cur.execute(

            "SELECT nome, cpf, tipo, pergunta, resposta FROM respostas WHERE id = ?",

            (id,)

        )

        row = cur.fetchone()

        if not row:

            return jsonify({

                "erro": "Resposta não encontrada"

            }), 404

        salvar_no_chroma(

            row["pergunta"],

            row["resposta"],

            {
                "nome": row["nome"],
                "cpf": row["cpf"],
                "tipo": row["tipo"]
            }

        )

        return jsonify({

            "ok": True,

            "mensagem": "Resposta enviada para o Chroma"

        })

    except Exception as e:

        print("Erro ao enviar resposta para o Chroma:", e)

        return jsonify({

            "erro": "Erro interno"

        }), 500

    finally:

        try:

            conn.close()

        except Exception:

            pass


# API: deletar resposta (e áudio)
@app.route("/api/respostas/<int:id>", methods=["DELETE"])
def api_deletar_resposta(id):

    try:

        conn = sqlite3.connect(DB_PATH)

        conn.row_factory = sqlite3.Row

        cur = conn.cursor()

        # busca a resposta
        cur.execute(
            "SELECT audio FROM respostas WHERE id = ?",
            (id,)
        )

        row = cur.fetchone()

        if not row:

            return jsonify({
                "erro": "Resposta não encontrada"
            }), 404

        # deleta arquivo de áudio
        if row["audio"]:

            audio_path = row["audio"].lstrip("/")

            full_path = os.path.join(".", audio_path)

            if os.path.exists(full_path):

                try:

                    os.remove(full_path)

                except Exception as e:

                    print("Erro ao deletar áudio:", e)

        # deleta da BD
        cur.execute(
            "DELETE FROM respostas WHERE id = ?",
            (id,)
        )

        conn.commit()

        return jsonify({
            "ok": True
        }), 200

    except Exception as e:

        print("Erro ao deletar resposta:", e)

        return jsonify({
            "erro": "Erro interno"
        }), 500

    finally:

        try:

            conn.close()

        except Exception:

            pass

# ==========================================
# START
# ==========================================


if __name__ == "__main__":

    os.makedirs(
        "static/audio",
        exist_ok=True
    )

    # inicializa DB local para respostas
    init_db()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
