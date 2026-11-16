from pymongo import MongoClient
import json

uri = "mongodb+srv://semihsisman_db_user:jwwxEaQGxDlE0HnJ@station-meteo.svenv9c.mongodb.net/?compressors=zlib&tlsAllowInvalidCertificates=true"
client = MongoClient(uri)

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


