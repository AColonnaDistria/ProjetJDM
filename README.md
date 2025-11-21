
# Projet Jeux de Mots — Chaînes de triplet de narration

## Objectif

Ce projet a pour but de :
- Représenter des histoires sous forme de chaînes de **factoïdes structurés** (`[sujet]`, `[prédicat]`, `[objet]`, etc.)
- Vérifier la cohérence des faits en interrogeant le réseau **Jeux de Mots (JDM)**
- Généraliser les termes (hyperonymes)
- Prédire les lignes manquantes dans des histoires incomplètes

---

## Structure du projet

| Fichier / Dossier            | Description |
|-----------------------------|-------------|
| `main.py`                   | Interface en ligne de commande (CLI) |
| `story_generator.py`        | Chargement et validation d'histoires |
| `story_generalizer.py`      | Généralisation des termes dans les histoires |
| `factoid_predict_1.py`      | Prédiction des lignes manquantes |
| `factoid_extractor.py`      | Extraction des composantes des factoïdes |
| `story_database.py`         | Gestion de la base de données locale |
| `jdm_client.py`             | Client API JDM avec cache |
| `tests.txt`, `histoires.txt`| Exemples de fichiers d'entrée |

---

## Installation

1. **Télécharger le projet**

2. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

3. **Créer les dossiers nécessaires**
```bash
mkdir -p data/stories data/factoids data/cache
```

---

## Utilisation (CLI)

Lancer le programme :
```bash
python main.py <commande> [options]
```

### Commandes disponibles

| Commande              | Description                                                      |
|-----------------------|------------------------------------------------------------------|
| `import`              | Importe et structure les histoires depuis `histoires.txt`        |
| `generalize`          | Applique la généralisation sémantique sur toutes les histoires   |
| `list`                | Affiche tous les identifiants d’histoires chargées               |
| `show <id>`           | Affiche les détails d’une histoire donnée                        |
| `test <id>`           | Teste la généralisation d’une histoire (sans sauvegarde)         |
| `predict`             | Complète une histoire à trous via saisie utilisateur             |
| `predict-from-file`   | Complète une histoire à trous depuis un fichier texte            |

---

## Format d’entrée attendu

Chaque ligne représente un fait :
```text
[sujet] client [predicat] commander [objet] soupe [lieu] table [temps] soir
```

Les lignes contenant `?` sont considérées comme **manquantes** et seront prédites.

---

## Exemple

```bash
python main.py predict
```

Entrée utilisateur :
```text
[sujet] homme [predicat] entrer [objet] restaurant
?
[sujet] serveur [predicat] accueillir [objet] homme
```

Le système prédit automatiquement la ligne manquante.

---

## Documentation

La documentation détaillée (PDF) se trouve dans le fichier Documentation.pdf

---


## Dépendances principales

- `requests`

---

## Auteur

Projet pédagogique basé sur le réseau lexical **JeuxDeMots** – www.jeuxdemots.org
