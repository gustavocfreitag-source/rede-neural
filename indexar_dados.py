import os
import hashlib
import chromadb
import torch
import pandas as pd
import numpy as np
from transformers import AutoTokenizer, AutoModel

# =========================
# CONFIG
# =========================
DB_PATH = "./db"
DATASET_PATH = "./datasets"
MODEL_NAME = "pucpr/biobertpt-clin"
BATCH_SIZE = 32

# =========================
# DEVICE
# =========================
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("Device:", device)

# =========================
# MODELO
# =========================
print("Carregando modelo...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModel.from_pretrained(MODEL_NAME).to(device)
model.eval()
print("Modelo carregado!")

# =========================
# FUNÇÕES
# =========================


def clean_text(text):
    return " ".join(str(text).split()).lower()


def gerar_id(texto, doenca):
    # 🔥 ID único por combinação (resolve duplicados de sintomas)
    base = f"{texto}|{doenca}"
    return hashlib.md5(base.encode("utf-8")).hexdigest()


def embed_batch(texts):
    inputs = tokenizer(
        texts,
        return_tensors="pt",
        truncation=True,
        padding=True
    ).to(device)

    with torch.no_grad():
        outputs = model(**inputs)

    emb = outputs.last_hidden_state.mean(dim=1).cpu().numpy()

    norms = np.linalg.norm(emb, axis=1, keepdims=True)
    emb = emb / np.clip(norms, 1e-8, None)

    return emb


# =========================
# DIMENSÃO
# =========================
test_emb = embed_batch(["teste"])
EMB_DIM = test_emb.shape[1]
print("Dimensão:", EMB_DIM)

# =========================
# CHROMA
# =========================
COLLECTION_NAME = f"triagem_{MODEL_NAME.split('/')[-1]}_{EMB_DIM}"

client = chromadb.PersistentClient(path=DB_PATH)

try:
    collection = client.get_collection(COLLECTION_NAME)
    print("Usando collection:", COLLECTION_NAME)
except:
    collection = client.create_collection(COLLECTION_NAME)
    print("Criada collection:", COLLECTION_NAME)

# =========================
# INDEXAÇÃO
# =========================


def indexar(path):
    textos, metadados, ids = [], [], []
    ids_batch = set()  # 🔥 controle de duplicados no batch
    total = 0

    for dirname, _, files in os.walk(path):
        for file in files:
            if not file.endswith(".csv"):
                continue

            caminho = os.path.join(dirname, file)
            print(f"Lendo: {caminho}")

            try:
                df = pd.read_csv(caminho)
            except Exception as e:
                print(f"Erro ao ler {file}: {e}")
                continue

            if "sintomas" not in df.columns or "doenca" not in df.columns:
                print(f"Colunas inválidas em {file}")
                continue

            for _, row in df.iterrows():
                sintomas = clean_text(row["sintomas"])
                doenca = clean_text(row["doenca"])

                if not sintomas:
                    continue

                texto = f"sintomas: {sintomas}"
                uid = gerar_id(texto, doenca)

                # 🔥 evita duplicado dentro do batch
                if uid in ids_batch:
                    continue

                ids_batch.add(uid)

                textos.append(texto)
                metadados.append({"doenca": doenca})
                ids.append(uid)

                if len(textos) >= BATCH_SIZE:
                    embeddings = embed_batch(textos)

                    collection.upsert(
                        embeddings=embeddings.tolist(),
                        documents=textos,
                        metadatas=metadados,
                        ids=ids
                    )

                    total += len(textos)

                    textos, metadados, ids = [], [], []
                    ids_batch.clear()  # 🔥 limpa controle

    # final
    if textos:
        embeddings = embed_batch(textos)

        collection.upsert(
            embeddings=embeddings.tolist(),
            documents=textos,
            metadatas=metadados,
            ids=ids
        )

        total += len(textos)

    print("\nIndexação finalizada!")
    print("Registros processados:", total)
    print("Total na collection:", collection.count())


# =========================
# MAIN
# =========================
if __name__ == "__main__":
    indexar(DATASET_PATH)
