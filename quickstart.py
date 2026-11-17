from pymongo import MongoClient
import json

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)

try:
    database = client.get_database("station_meteo")
    mesures = database.get_collection("mesures")

    # Récupération d'une donnée
    query = { "Air Temperature": "27.6 °C"}
    donnee = mesures.count_documents({})
    print("Exemple de donnée :", json.dumps(donnee, indent=4, default=str))

    client.close()

except Exception as e:
    raise Exception("Unable to find the document due to the following error: ", e)


