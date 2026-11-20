import paho.mqtt.client as mqtt
import json
import smtplib
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from email.message import EmailMessage
from dotenv import load_dotenv
from importer import inserer_une_mesure

load_dotenv()


def envoyer_alerte(type_alerte, valeur, seuil):
    msg = EmailMessage()
    msg.set_content(f"L'alerte '{type_alerte}' a été déclenchée.\nValeur relevée : {valeur}\nSeuil autorisé : {seuil}")
    msg['Subject'] = f"⚠️ Alerte Météo : {type_alerte}"
    msg['From'] = os.getenv("EMAIL_SENDER")
    msg['To'] = os.getenv("EMAIL_RECEIVER")
    try:
        s = smtplib.SMTP('smtp.gmail.com', 587)
        s.starttls()
        s.login(os.getenv("EMAIL_SENDER"), os.getenv("EMAIL_PASSWORD"))
        s.send_message(msg)
        s.quit()
        print(f"Email d'alerte envoyé pour : {type_alerte}")
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email d'alerte : {e}")


def decoder_hexa(payload):
    """Ancien format : payload hexadécimal (ton décodage d'origine)."""
    return {
        "temperature": int(payload[2:6], 16) / 10.0,
        "humidite": int(payload[6:8], 16) / 10.0,
        "luminosite": int(payload[8:16], 16),
        "indice_uv": int(payload[16:18], 16) / 10.0,
        "vent_vitesse": int(payload[18:22], 16) / 10.0,
        "vent_direction": int(round(int(payload[24:28], 16) / 10.0)),
        "precipitation": int(payload[28:36], 16) / 1000.0,
        "pression_atmospherique": int(payload[36:40], 16) / 10.0,
        "rafale_max": int(payload[42:46], 16) / 10.0,
        "pluie_cumul": int(payload[46:54], 16) / 10.0,
    }


def lire_json_clair(d):
    """Format en clair (SenseCAP S2120 / simulateur)."""
    return {
        "temperature": float(d["temperature"]),
        "humidite": float(d["humidity"]),
        "vent_vitesse": float(d["wind_speed"]),
        "vent_direction": int(d["wind_direction"]),
        "rafale_max": float(d["peak_wind"]),
        "indice_uv": float(d["uv_index"]),
        "luminosite": int(d["illumination"]),
        "precipitation": float(d["rainfall"]),
        "pluie_cumul": float(d["rain_accumulation"]),
        "pression_atmospherique": float(d["air_pressure"]),
    }


def heure_en_utc(valeur):
    if not valeur:
        return datetime.now(timezone.utc).isoformat()
    t = datetime.fromisoformat(str(valeur).replace("Z", "+00:00"))
    if t.tzinfo is None:
        t = t.replace(tzinfo=ZoneInfo("Europe/Paris"))
    return t.astimezone(timezone.utc).isoformat()


def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected with result code {reason_code}")
    topic = os.getenv("MQTT_TOPIC")
    print(f"Abonné à : {topic}")
    client.subscribe(topic)


def on_message(client, userdata, msg):
    try:
        donnees = json.loads(msg.payload.decode("utf-8"))
        if not isinstance(donnees, dict):
            print("Message ignoré (pas un objet JSON)")
            return

        print("Topic     :", msg.topic)
        print("Données reçues :", donnees)

        if "payload" in donnees:
            mesures = decoder_hexa(donnees["payload"])
            device = str(donnees.get("device", "inconnu"))
            brut = donnees["payload"]
        elif "temperature" in donnees:
            mesures = lire_json_clair(donnees)
            device = str(donnees.get("device_id", "inconnu"))
            brut = json.dumps(donnees)
        else:
            print("Message ignoré (format inconnu)")
            return

        instant = heure_en_utc(donnees.get("time"))

        inserer_une_mesure({
            "device": device,
            "time": instant,
            "payload": brut,
            "mesures": mesures,
        })

        with open("releves_meteo.json", "w", encoding="utf-8") as f:
            json.dump({"device": device, "time": instant, **mesures},
                      f, indent=4, ensure_ascii=False)

        seuils = {
            "Chaleur": (mesures["temperature"] >= float(os.getenv("ALERTE_CHALEUR")), mesures["temperature"], "ALERTE_CHALEUR"),
            "Froid": (mesures["temperature"] <= float(os.getenv("ALERTE_FROID")), mesures["temperature"], "ALERTE_FROID"),
            "Vent Violent": (mesures["vent_vitesse"] >= float(os.getenv("ALERTE_VENT")), mesures["vent_vitesse"], "ALERTE_VENT"),
            "Pluie Abondante": (mesures["pluie_cumul"] >= float(os.getenv("ALERTE_PLUIE")), mesures["pluie_cumul"], "ALERTE_PLUIE"),
        }
        for nom, (declenchee, valeur, cle) in seuils.items():
            if declenchee:
                envoyer_alerte(nom, valeur, float(os.getenv(cle)))

    except Exception as e:
        print(f"Erreur de traitement du message : {e}")


mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqttc.on_connect = on_connect
mqttc.on_message = on_message

mqttc.connect(os.getenv("MQTT_BROKER"), int(os.getenv("MQTT_PORT")), 60)
mqttc.loop_forever()