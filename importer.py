import os
import json
from datetime import datetime, timezone
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError, BulkWriteError, DuplicateKeyError

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "station_meteo"

if not MONGO_URI:
    print("Erreur : La variable MONGO_URI est absente du fichier .env.")
    exit(1)

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    db = client[DB_NAME]
    collection_mesures = db["mesures"]
    collection_journaux = db["journaux"]
    print("Connexion à MongoDB réussie.")
except PyMongoError as e:
    print(f"Erreur de connexion à MongoDB : {e}")
    exit(1)

CONTRAINTES = {
    "temperature": (float, -40, 85),
    "humidite": (float, 0, 100),
    "vent_vitesse": (float, 0, 60),
    "rafale_max": (float, 0, 60),
    "vent_direction": (int, 0, 359),
    "precipitation": (float, 0, 240),
    "pluie_cumul": (float, 0, float("inf")),
    "luminosite": (int, 0, 200000),
    "indice_uv": (float, 0, 15),
    "pression_atmospherique": (float, 300, 1100),
    "niveau_batterie": (int, 0, 100),
    "qualite_signal": (int, -140, 0),
}


def journaliser(type_evenement, statut, message, detail=None):
    """Enregistre un événement dans la collection journaux."""
    log = {
        "type_evenement": type_evenement,
        "statut": statut,
        "date_evenement": datetime.now(timezone.utc),
        "message": message,
    }
    if detail is not None:
        log["detail"] = detail
    collection_journaux.insert_one(log)


def valider_et_transformer_trame(trame):
    """
    Contrôle une trame JSON selon le dictionnaire de données.
    Retourne (document_valide, None) si conforme, ou (None, "raison du rejet").
    """
    champs_obligatoires = ["device", "time", "payload"]
    for champ in champs_obligatoires:
        if champ not in trame or trame[champ] is None:
            return None, f"Champ obligatoire manquant ou nul : '{champ}'"

    try:
        date_str = str(trame["time"]).replace("Z", "+00:00")
        instant_mesure = datetime.fromisoformat(date_str)
        if instant_mesure.tzinfo is None:
            instant_mesure = instant_mesure.replace(tzinfo=timezone.utc)
        else:
            instant_mesure = instant_mesure.astimezone(timezone.utc)
    except ValueError:
        return None, f"Format de date invalide : '{trame['time']}'"

    doc = {
        "reference_capteur": str(trame["device"]),
        "instant_mesure": instant_mesure,
        "payload_brut": str(trame["payload"]),
    }

    mesures_brutes = trame.get("mesures")
    if not isinstance(mesures_brutes, dict) or len(mesures_brutes) == 0:
        return None, "Le bloc 'mesures' est absent, vide ou mal formé"

    for cle_json, valeur in mesures_brutes.items():
        cle_norm = cle_json.lower()

        if cle_norm not in CONTRAINTES:
            return None, f"Champ de mesure inconnu du dictionnaire : '{cle_json}'"

        type_attendu, val_min, val_max = CONTRAINTES[cle_norm]

        if isinstance(valeur, bool) or valeur is None:
            return None, f"Valeur invalide (booléen ou nul) pour '{cle_norm}'"

        try:
            if type_attendu is int and isinstance(valeur, float) and not valeur.is_integer():
                return None, f"Entier attendu pour '{cle_norm}', décimal reçu : {valeur}"
            val_convertie = type_attendu(valeur)
        except (ValueError, TypeError):
            return None, f"Type invalide pour '{cle_norm}' : '{valeur}' (attendu {type_attendu.__name__})"

        if not (val_min <= val_convertie <= val_max):
            return None, f"Valeur hors plage pour '{cle_norm}' : {val_convertie} (attendu entre {val_min} et {val_max})"

        doc[cle_norm] = val_convertie

    return doc, None


def traiter_et_inserer_donnees(fichier_json):
    """Lit un fichier JSON, valide les trames et les insère sans doublon."""
    try:
        with open(fichier_json, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Erreur : Le fichier '{fichier_json}' est introuvable.")
        return
    except json.JSONDecodeError as e:
        print(f"Erreur : Le fichier JSON est mal formé ({e}).")
        return

    documents_valides = []
    nb_rejets = 0

    for trame in data:
        doc, erreur = valider_et_transformer_trame(trame)
        if erreur:
            nb_rejets += 1
            journaliser("MESURE_REJETEE", "ECHEC", erreur, detail=trame)
        else:
            documents_valides.append(doc)

    nb_inseres = 0
    nb_doublons = 0

    if documents_valides:
        try:
            resultat = collection_mesures.insert_many(documents_valides, ordered=False)
            nb_inseres = len(resultat.inserted_ids)
        except BulkWriteError as bwe:
            nb_inseres = bwe.details.get("nInserted", 0)
            erreurs_ecriture = bwe.details.get("writeErrors", [])
            nb_doublons = sum(1 for err in erreurs_ecriture if err.get("code") == 11000)

    bilan = f"Import terminé : {nb_inseres} insérée(s), {nb_doublons} doublon(s) ignoré(s), {nb_rejets} rejetée(s)."
    print(bilan)
    journaliser("INGESTION", "SUCCES", bilan)
    bilan = f"Import terminé : {nb_inseres} insérée(s), {nb_doublons} doublon(s) ignoré(s), {nb_rejets} rejetée(s)."
    print(bilan)
    journaliser("INGESTION", "SUCCES", bilan)


def inserer_une_mesure(trame):
    """Valide une trame reçue en MQTT et l'insère dans la collection mesures."""
    doc, erreur = valider_et_transformer_trame(trame)
    if erreur:
        print(f"Mesure rejetée : {erreur}")
        journaliser("MESURE_REJETEE", "ECHEC", erreur, detail=trame)
        return False

    try:
        collection_mesures.insert_one(doc)
        print("Mesure insérée dans MongoDB.")
        return True
    except DuplicateKeyError:
        print("Doublon ignoré.")
        return False
    except PyMongoError as e:
        print(f"Erreur d'insertion MongoDB : {e}")
        return False


if __name__ == "__main__":
    traiter_et_inserer_donnees("mesures-exemple.json")

if __name__ == "__main__":
    traiter_et_inserer_donnees("mesures-exemple.json")