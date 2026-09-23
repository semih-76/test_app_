import paho.mqtt.client as mqtt
import json
import smtplib
import os
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

# 2. Définition de la fonction d'envoi d'email
def envoyer_alerte(type_alerte, valeur, seuil):

    msg = EmailMessage()
    texte_alerte = f"L'alerte '{type_alerte}' a été déclenchée.\nValeur relevée : {valeur}\nSeuil autorisé : {seuil}"
    msg.set_content(texte_alerte)

    msg['Subject'] = f"⚠️ Alerte Météo : {type_alerte}"
    msg['From'] = os.getenv("EMAIL_SENDER")
    msg['To'] = os.getenv("EMAIL_RECEIVER")

    if True:
        s = smtplib.SMTP('smtp.gmail.com', 587)
        s.starttls()
        s.login(os.getenv("EMAIL_SENDER"), os.getenv("EMAIL_PASSWORD"))
        s.send_message(msg)
        s.quit()
        print(f"📧 ✅ Email d'alerte envoyé pour : {type_alerte}")




def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected with result code {reason_code}")

    client.subscribe(os.getenv("MQTT_TOPIC"))


def on_message(client, userdata, msg):
    print("Topic     : " + msg.topic)

    texte_decode = msg.payload.decode("utf-8")

    donnees = json.loads(texte_decode)

    print("Données décodées :", donnees)

    payload = donnees["payload"]

    bloc_ID1 = payload[0:2]
    decoded_Id1 = int(bloc_ID1, 16)
    print(f"{decoded_Id1} ID")

    bloc_Temperature = payload[2:6]
    decode_temperature = int(bloc_Temperature, 16)
    print(f"Air Temperature : {decode_temperature / 10.0} ℃")

    bloc_Humidity = payload[6:8]
    decode_Humidity = int(bloc_Humidity, 16)
    print(f"Air Humidity : {decode_Humidity / 10.0} %RH")

    bloc_Light = payload[8:16]
    decode_Light = int(bloc_Light, 16)
    print(f"Light Intensity : {decode_Light} Lux")

    bloc_uv = payload[16:18]
    decoded_uv = int(bloc_uv, 16)
    print(f"UV Index : {decoded_uv / 10.0} UV")

    bloc_speed = payload[18:22]
    decoded_speed = int(bloc_speed, 16)
    print(f"Wind Speed : {decoded_speed / 10.0} m/s")

    bloc_ID2 = payload[22:24]
    decoded_ID2 = int(bloc_ID2, 16)
    print(f"{decoded_ID2} ID")

    bloc_direction = payload[24:28]
    decoded_direction = int(bloc_direction, 16)
    print(f"Wind Direction :  {decoded_direction / 10.0 } °")

    bloc_rainfall = payload[28:36]
    decoded_rainfall = int(bloc_rainfall, 16)
    print(f"Rainfall Intensity : {decoded_rainfall / 1000 } mm/hour")

    bloc_pressure = payload[36:40]
    decoded_pressure = int(bloc_pressure, 16)
    print(f"Barometric Pressure : {decoded_pressure} Pa")

    bloc_Id3 = payload[40:42]
    decoded_Id3 = int(bloc_Id3, 16)
    print(f"{decoded_Id3} ID")

    bloc_peak = payload[42:46]
    decoded_peak = int(bloc_peak, 16)
    print(f"Peak Wind Gust : { decoded_peak / 10.0 } m/s")

    bloc_cumulative_rainfall = payload[46:54]
    decoded_cumulative_rainfall = int(bloc_cumulative_rainfall, 16)
    print(f"Cumulative Rainfall : { decoded_cumulative_rainfall / 10.0 } mm")

    donnees_decodes = {
        "Air Temperature" : f"{decode_temperature / 10.0} ℃",
        "Air Humidity" : f"{decode_Humidity / 10.0} % RH",
        "Light Intensity" : f"{decode_Light} Lux",
        "UV Index" : f"{decoded_uv / 10.0} UV",
        "Wind Speed" : f"{decoded_speed / 10.0} m/s",
        "Wind Direction" :  f"{decoded_direction / 10.0} °",
        "Rainfall Intensity" : f"{decoded_rainfall / 1000} mm/hour",
        "Barometric Pressure" : f"{decoded_pressure}Pa",
        "Peak Wind Gust" : f"{decoded_peak / 10.0} m/s",
        "Cumulative Rainfall" : f"{decoded_cumulative_rainfall / 10.0} mm"
    }

    # 1. On récupère les seuils du .env en forçant le format décimal (float)
    seuil_chaleur = float(os.getenv("ALERTE_CHALEUR"))
    seuil_froid = float(os.getenv("ALERTE_FROID"))
    seuil_vent = float(os.getenv("ALERTE_VENT"))
    seuil_pluie = float(os.getenv("ALERTE_PLUIE"))


    temp_actuelle = decode_temperature / 10.0
    vent_actuel = decoded_speed / 10.0
    pluie_actuelle = decoded_cumulative_rainfall / 10.0

    # 3. On teste les conditions et on déclenche la fonction d'envoi d'email
    if temp_actuelle >= seuil_chaleur:
        envoyer_alerte("Chaleur", temp_actuelle, seuil_chaleur)

    if temp_actuelle <= seuil_froid:
        envoyer_alerte("Froid", temp_actuelle, seuil_froid)

    if vent_actuel >= seuil_vent:
        envoyer_alerte("Vent Violent", vent_actuel, seuil_vent)

    if pluie_actuelle >= seuil_pluie:
        envoyer_alerte("Pluie Abondante", pluie_actuelle, seuil_pluie)

    with open("releves_meteo.json", "w", encoding="utf-8") as fichier:
        json.dump(donnees_decodes, fichier, indent=4,  ensure_ascii=False)



mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqttc.on_connect = on_connect
mqttc.on_message = on_message

broker = os.getenv("MQTT_BROKER")
port = int(os.getenv("MQTT_PORT"))


mqttc.connect(broker, port, 60)
mqttc.loop_forever()