import argparse
from story_generator import StoryGenerator
from story_generalizer import test_all_stories, test_story
from factoid_extractor import FactoidExtractor
from story_database import StoryDatabase
from factoid_predict_1 import FactoidPredict1
from story_test import StoryTest

def importer_histoires(input_file="histoires.txt"):
    generator = StoryGenerator(input_file=input_file)
    generator.load_and_store_stories()
    print("\nImportation des histoires terminée.")

def generaliser_histoires():
    test_all_stories()
    print("\nGénéralisation des histoires terminée.")

def tester_histoire(story_id):
    test_story(story_id, save_story=False)

def lister_histoires():
    StoryDatabase.initialize()
    stories = StoryDatabase.list_stories()
    print("\nHistoires disponibles :")
    for sid in stories:
        print("-", sid)

def afficher_histoire(story_id):
    StoryDatabase.initialize()
    story = StoryDatabase.get_story(story_id)
    if not story:
        print("Aucune histoire trouvée avec cet ID.")
        return
    print(f"\nHistoire : {story_id} (domaine : {story.get('domain')})")
    for f in story.get("factoids", []):
        parts = [f"[sujet] {f['subject']}", f"[predicat] {f['predicate']}"]
        if f.get("object"): parts.append(f"[objet] {f['object']}")
        if f.get("location"): parts.append(f"[lieu] {f['location']}")
        if f.get("time"): parts.append(f"[temps] {f['time']}")
        print(" ".join(parts))

def prediction_incomplete():
    print("\nEntrer une histoire ligne par ligne ('?' pour les trous, ligne vide pour terminer) :")
    lines = []
    while True:
        line = input("> ").strip()
        if not line:
            break
        lines.append(line)

    predictor = FactoidPredict1()
    predictions = predictor.predict_missing(lines)

    print("\nHistoire complétée :")
    pid = 0
    for l in lines:
        if l == "?":
            print(">", predictions[pid])
            pid += 1
        else:
            print(l)

def prediction_incomplete_from_file():
    print("\nEntrer le chemin d'accès d'un fichier histoire ('?' pour les trous) (eg 'tests.txt'):")
    file_path = input()
    storyTest = StoryTest(test_file = file_path)
    storyTest.run_all_tests()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interface CLI pour le projet Jeux de Mots")
    subparsers = parser.add_subparsers(dest="commande", required=True)

    subparsers.add_parser("import", help="Importer les histoires depuis un fichier texte")
    subparsers.add_parser("generalize", help="Généraliser toutes les histoires")
    subparsers.add_parser("list", help="Lister toutes les histoires disponibles")
    subparsers.add_parser("predict", help="Compléter une histoire à trous")
    subparsers.add_parser("predict-from-file", help="Compléter une histoire à trous à partir d'un fichier")

    aff_parser = subparsers.add_parser("show", help="Afficher une histoire spécifique")
    aff_parser.add_argument("id", help="ID de l'histoire")

    test_parser = subparsers.add_parser("test", help="Tester une histoire spécifique")
    test_parser.add_argument("id", help="ID de l'histoire")

    args = parser.parse_args()

    if args.commande == "import":
        importer_histoires()
    elif args.commande == "generalize":
        generaliser_histoires()
    elif args.commande == "list":
        lister_histoires()
    elif args.commande == "show":
        afficher_histoire(args.id)
    elif args.commande == "test":
        tester_histoire(args.id)
    elif args.commande == "predict":
        prediction_incomplete()
    elif args.commande == "predict-from-file":
        prediction_incomplete_from_file()
