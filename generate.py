import requests
import brotli
import json
import re
import os
import base64

GH_TOKEN = os.environ.get("GH_TOKEN", "")
GH_REPO = "Fullflam/swgoh-gamedata"

URLS = {
    "en": "https://raw.githubusercontent.com/swgoh-utils/gamedata/main/Loc_ENG_US.txt.json.br",
    "fr": "https://raw.githubusercontent.com/swgoh-utils/gamedata/main/Loc_FRE_FR.txt.json.br"
}

def telecharger_et_decompresser(url):
    res = requests.get(url, timeout=60)
    res.raise_for_status()
    return json.loads(brotli.decompress(res.content))["data"]

def nettoyer(texte):
    return re.sub(r'\[.*?\]', '', texte).strip()

def parser_effet(texte):
    texte = nettoyer(texte)
    if ":" in texte:
        parties = texte.split(":", 1)
        return parties[0].strip(), parties[1].strip()
    return texte.strip(), texte.strip()

def generer_dict():
    print("Téléchargement EN...")
    en = telecharger_et_decompresser(URLS["en"])
    print("Téléchargement FR...")
    fr = telecharger_et_decompresser(URLS["fr"])

    dico = {}
    for k in en:
        if not k.startswith("BattleEffect_"):
            continue

        name_en, desc_en = parser_effet(en[k])
        name_fr, desc_fr = parser_effet(fr.get(k, ""))

        cle = name_en.lower()

        # Si la clé existe déjà (variantes d'un même effet) on skip
        if cle in dico:
            continue

        dico[cle] = {
            "name_en": name_en,
            "name_fr": name_fr,
            "desc_en": desc_en,
            "desc_fr": desc_fr,
            "internal_key": k[13:]
        }

    print(f"{len(dico)} effets générés.")
    return dico

def get_fichier_actuel(nom_fichier):
    headers = {
        "Authorization": f"token {GH_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{nom_fichier}"
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        data = res.json()
        return data["sha"], base64.b64decode(data["content"]).decode("utf-8")
    return None, None

def committer_json(nom_fichier, contenu_json):
    headers = {
        "Authorization": f"token {GH_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{nom_fichier}"
    contenu_b64 = base64.b64encode(contenu_json.encode("utf-8")).decode("utf-8")

    sha, contenu_actuel = get_fichier_actuel(nom_fichier)

    if contenu_actuel and contenu_actuel == contenu_json:
        print(f"{nom_fichier} : aucun changement, skip.")
        return

    payload = {
        "message": f"Mise à jour {nom_fichier}",
        "content": contenu_b64
    }
    if sha:
        payload["sha"] = sha

    res = requests.put(url, headers=headers, json=payload)
    if res.status_code in (200, 201):
        print(f"{nom_fichier} commité avec succès !")
    else:
        print(f"Erreur commit : {res.status_code} — {res.text}")

if __name__ == "__main__":
    dico = generer_dict()
    contenu_json = json.dumps(dico, ensure_ascii=False, indent=2)
    committer_json("battle_effects_dict.json", contenu_json)
