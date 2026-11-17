import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from pymongo import MongoClient, DESCENDING
from pymongo.errors import PyMongoError

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "station_meteo"

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    db = client[DB_NAME]
    collection_mesures = db["mesures"]
    print("Connexion à MongoDB réussie.\n")
except PyMongoError as e:
    print(f"Erreur de connexion à MongoDB : {e}")
    exit(1)


def derniere_mesure():
    print("--- 1. Dernière mesure reçue ---")
    mesure = collection_mesures.find_one(sort=[("instant_mesure", DESCENDING)])
    if mesure:
        print(f"Capteur : {mesure.get('reference_capteur')} | Date : {mesure.get('instant_mesure')} | Temp : {mesure.get('temperature')} °C")
    else:
        print("Aucune mesure trouvée.")
    print()


def mesures_dernieres_24h():
    print("--- 2. Mesures des dernières 24 heures ---")
    il_y_a_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    mesures = list(collection_mesures.find({"instant_mesure": {"$gte": il_y_a_24h}}).sort("instant_mesure", DESCENDING))
    
    print(f"{len(mesures)} mesure(s) trouvée(s) sur les dernières 24h :")
    for m in mesures:
        print(f"- {m.get('instant_mesure')} | Capteur : {m.get('reference_capteur')} | Temp : {m.get('temperature')} °C")
    print()


def nombre_total_mesures():
    print("--- 3. Nombre total de mesures ---")
    total = collection_mesures.count_documents({})
    print(f"Nombre total de mesures enregistrées : {total}\n")


def mesures_sup_30_degres():
    print("--- 4. Mesures au-dessus de 30 °C ---")
    mesures = list(collection_mesures.find({"temperature": {"$gt": 30}}).sort("temperature", DESCENDING))
    
    print(f"{len(mesures)} mesure(s) au-dessus de 30 °C :")
    for m in mesures:
        print(f"- {m.get('temperature')} °C le {m.get('instant_mesure')} (Capteur : {m.get('reference_capteur')})")
    print()


def top_5_vitesses_vent():
    print("--- 5. Cinq plus fortes vitesses de vent ---")
    mesures = list(collection_mesures.find({"vent_vitesse": {"$exists": True}}).sort("vent_vitesse", DESCENDING).limit(5))
    
    for i, m in enumerate(mesures, 1):
        print(f"{i}. {m.get('vent_vitesse')} m/s le {m.get('instant_mesure')} (Capteur : {m.get('reference_capteur')})")
    print()


if __name__ == "__main__":
    derniere_mesure()
    mesures_dernieres_24h()
    nombre_total_mesures()
    mesures_sup_30_degres()
    top_5_vitesses_vent()