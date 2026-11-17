# Station Météo — Ingestion et stockage MongoDB Atlas

Ce projet permet de collecter, valider et stocker des mesures météorologiques au format JSON dans une base de données **MongoDB Atlas** (`station_meteo`), sans perte de données ni doublon, tout en journalisant les anomalies.

## Prérequis

* **Python 3.8+**
* Un cluster **MongoDB Atlas** actif avec :
  * Une base de données nommée `station_meteo`
  * Deux collections : `mesures` et `journaux`
  * Un **index unique** composé sur les champs `(reference_capteur, instant_mesure)` dans la collection `mesures`
  * Un utilisateur dédié disposant uniquement des droits de lecture et d'écriture (`readWrite`) sur `station_meteo`

---

## Structure du projet

```text
.
├── importer.py           # Validation des trames, insertion sans doublon et journalisation
├── requetes.py           # Requêtes d'analyse sur la collection mesures
├── collecteur.py         # Script de collecte en temps réel relié à MongoDB
├── mesures-exemple.json  # Jeu de données de test au format JSON
├── .env.example          # Modèle des variables d'environnement requises
├── .gitignore            # Fichiers exclus du suivi Git (dont .env)
└── README.md             # Documentation du projet
```

---


1. **Cloner le dépôt :**
   ```bash
   git clone <url-de-votre-depot-github>
   cd <nom-du-dossier>
   ```

2. **Créer et activer un environnement virtuel :**
   ```bash
   python -m venv venv
   venv\Scripts\activate           # Sur Windows
   ```

3. **Installer les dépendances Python :**
   ```bash
   pip install pymongo python-dotenv
   ```

4. **Configurer les variables d'environnement :**
   Copiez le fichier d'exemple `.env.example` vers un fichier `.env` à la racine du projet :
   ```bash
   cp .env.example .env
   ```
   Renseignez ensuite votre chaîne de connexion MongoDB Atlas dans le fichier `.env` :
   ```env
   MONGO_URI="mongodb+srv://<utilisateur>:<mot_de_passe>@<cluster>.mongodb.net/?retryWrites=true&w=majority"
   ```
   > **Note :** Ne versionnez jamais le fichier `.env`. Assurez-vous que votre adresse IP est autorisée dans *Network Access* sur MongoDB Atlas.

---

## Lancement et utilisation

### 1. Importer un fichier JSON de mesures
Exécutez le script d'importation pour contrôler et insérer les mesures de test :
```bash
python importer.py
```
* **Validation :** Vérifie la présence des champs obligatoires (`device`, `time`, `payload`), convertit la date au format UTC et contrôle les types et plages de valeurs du dictionnaire de données.
* **Gestion des doublons :** Grâce à l'index unique `(reference_capteur, instant_mesure)`, relancer le script ignore automatiquement les mesures déjà enregistrées.
* **Journalisation :** Toute mesure invalide ou hors plage est rejetée et enregistrée dans la collection `journaux` avec le motif exact du rejet.

### 2. Exécuter les requêtes d'analyse
Lancez le script de consultation pour afficher les indicateurs météorologiques :
```bash
python requetes.py
```
Ce script interroge la base pour extraire :
1. La dernière mesure reçue
2. Les mesures des dernières 24 heures
3. Le nombre total de mesures enregistrées
4. Les mesures enregistrées au-dessus de 30 °C
5. Les cinq plus fortes vitesses de vent

### 3. Lancer le collecteur temps réel
Démarrez le collecteur pour envoyer automatiquement chaque nouvelle mesure reçue vers MongoDB Atlas :
```bash
python collecteur.py
```