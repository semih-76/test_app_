import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

uri = os.getenv("MONGODB_URI")
client = MongoClient(uri, serverSelectionTimeoutMS=5000)

try:
    client.admin.command("ping")
    print("Connexion réussie")
    db = client["station_meteo"]
    essais = db["essais"]

    # Créer un message
    essais.insert_one({"message": "test"})
    print("Message inséré avec succès")

    # Modifier un message
    essais.update_one({"message": "test"}, {"$set": {"valeur": 4}})
    print("Message modifié avec succès")

    #Supprimer un message
    essais.delete_one({"message": "test"})
    print("Message supprimé avec succès")

finally:
    client.close()