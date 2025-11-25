import json
import os
from pathlib import Path

def load_all_professions(data_dir: str) -> dict:
    """
    Carrega todas as profissões a partir dos arquivos JSON em data_dir.
    Espera objetos com pelo menos:
        {
            "category": "...",
            "items": [ ... ]   # ou chave equivalente ("professions", "list"...)
        }
    Registros sem 'category' ou sem lista de itens são ignorados com aviso.
    """
    result = {}

    # Ajusta aqui de acordo com como você está organizando os arquivos
    # Ex: se for só um arquivo, troca o glob por algo fixo
    for file in Path(data_dir).glob("*.json"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[ERRO] Não foi possível ler {file.name}: {e}")
            continue

        if not isinstance(data, list):
            # Se o JSON for um dict, adapta se precisar
            print(f"[AVISO] {file.name} não contém uma lista de objetos, ignorando.")
            continue

        for idx, obj in enumerate(data):
            if not isinstance(obj, dict):
                print(f"[AVISO] Registro não-dict em {file.name}[{idx}], ignorando: {obj!r}")
                continue

            category = obj.get("category")
            if not category:
                print(f"[AVISO] Registro sem 'category' em {file.name}[{idx}]: {obj!r}")
                continue

            # tenta descobrir onde está a lista de itens
            items = None
            if "items" in obj:
                items = obj["items"]
            elif "professions" in obj:
                items = obj["professions"]
            elif "list" in obj:
                items = obj["list"]

            if items is None:
                print(f"[AVISO] Registro sem 'items' em {file.name}[{idx}] (category={category!r}): {obj!r}")
                continue

            if not isinstance(items, list):
                print(f"[AVISO] 'items' não é lista em {file.name}[{idx}] (category={category!r}): {items!r}")
                continue

            result[category] = items

    return result
