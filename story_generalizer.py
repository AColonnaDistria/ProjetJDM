import json
import os
from typing import Dict, Any, List
from jdm_client import JDMClient
from factoid_extractor import FactoidExtractor
from story_generator import StoryGenerator
from story_database import StoryDatabase

class StoryGeneralizer:
    def __init__(self, valid_terms_path: str = "data/valid_terms.json", valid_relations_path: str = "data/valid_relations.json"):
        self.jdm = JDMClient(logging = False)
        self.extractor = FactoidExtractor()
        self.story_checker = StoryGenerator()  # Utilise le mode auto pour valider sans prompt
        self.good_generalizators = ["humain", "être humain", "personne", "individu", "employé", "convive", "artiste", "visiteur", "animal domestique", "animal", "nourriture"]

    def _get_generalizations1(self, term: str) -> list:        
        rels = []
        for good_generalizator in self.good_generalizators:
            rel = self.jdm.get_relations_from_to(term, good_generalizator, types_ids=[self.jdm.relation_type_ids["r_isa"]], min_weight=5)
            if not (not rel or "relations" not in rel or not rel["relations"]):
                rels.append((good_generalizator, rel["relations"][0]["w"]))

        rels = sorted(rels, key=lambda x: x[1], reverse=True)[:5]
        return rels

    def _get_generalizations(self, term: str) -> list:
        """Retourne les hyperonymes (r_isa) d’un terme via JDM"""
        relations = self.jdm.get_relations_from(term, types_ids=[self.jdm.relation_type_ids["r_isa"]], min_weight=5)

        if not relations or "relations" not in relations:
            return []
        
        rels = [
            (relations["nodes"][idx]["name"], relations["relations"][idx]["w"])
            for idx in range(len(relations["relations"]))
            if ':' not in relations["nodes"][idx]["name"]
        ]

        rels = sorted(rels, key=lambda x: x[1], reverse=True)[:5]
        return rels

    def generalize_factoid_story(self, story_id: str, factoids: List[Dict[str, Any]], domain: str) -> Dict[str, Any]:
        """Généralise tous les sujets ET objets distincts des factoïdes si possible"""
        final_mappings = {}
        reverse_mappings = {}

        # Collecte des sujets et objets uniques
        elements = []
        for f in factoids:
            if f.get("subject"):
                elements.append(("subject", f["subject"]))
            #if f.get("object"):
            #    elements.append(("object", f["object"]))

        # Tentative de généralisation de chaque élément
        for role, value in elements:
            candidates1 = self._get_generalizations1(value)
            candidate_found = None

            for candidate, _ in candidates1:
                if candidate != value and not (">" in candidate and candidate.split(">")[0] == value):
                    # Appliquer temporairement la généralisation
                    test_factoids = [
                        {
                            **f,
                            role: candidate if f.get(role) == value else f.get(role)
                        }
                        for f in factoids
                    ]
                    test_story = {
                        "id": story_id + "_generalized_test",
                        "domain": domain,
                        "factoids": test_factoids
                    }
                    if self.story_checker.check_story_consistency(test_story, ignore=True):
                        candidate_found = candidate
                        print(f"Généralisation {role} réussie : {value} → {candidate_found}")
                        break
            
            if not candidate_found:
                candidates2 = self._get_generalizations(value)

                for candidate, _ in candidates2:
                    if candidate != value and not (">" in candidate and candidate.split(">")[0] == value):
                        # Appliquer temporairement la généralisation
                        test_factoids = [
                            {
                                **f,
                                role: candidate if f.get(role) == value else f.get(role)
                            }
                            for f in factoids
                        ]
                        test_story = {
                            "id": story_id + "_generalized_test",
                            "domain": domain,
                            "factoids": test_factoids
                        }
                        if self.story_checker.check_story_consistency(test_story, ignore=True):
                            candidate_found = candidate
                            self.good_generalizators.append(candidate_found)
                            print(f"Généralisation {role} réussie : {value} → {candidate_found}")
                            break

            if candidate_found:
                if not candidate_found in self.good_generalizators:
                    self.good_generalizators.append(candidate_found)

                if ">" in candidate_found:
                    candidate_found = candidate_found.split(">")[0]
                final_mappings[(role, value)] = candidate_found
                if (role, candidate_found) in reverse_mappings:
                    reverse_mappings[(role, candidate_found)].append(value)
                else:
                    reverse_mappings[(role, candidate_found)] = [value]
                
        # Gestion des collisions
        for (role, general), originals in reverse_mappings.items():
            if len(originals) == 1:
                continue
            for i, original in enumerate(originals, start=1):
                final_mappings[(role, original)] = f"{general}:{i}"

        # Application des remplacements
        generalized_factoids = []
        for f in factoids:
            f = f.copy()
            subj = f.get("subject")
            obj = f.get("object")
            if ("subject", subj) in final_mappings:
                f["subject"] = f"({final_mappings[('subject', subj)]})"
            #if ("object", obj) in final_mappings:
            #    f["object"] = f"({final_mappings[('object', obj)]})"
            if ("subject", obj) in final_mappings:
                f["object"] = f"({final_mappings[('subject', obj)]})"
            generalized_factoids.append(f)

        return {
            "id": story_id + "_generalized",
            "domain": domain,
            "factoids": generalized_factoids
        }


    def _rebuild_factoid_sentence(self, f: Dict[str, str]) -> str:
        parts = [f"[sujet] {f['subject']}", f"[predicat] {f['predicate']}"]
        if f.get("object"): parts.append(f"[objet] {f['object']}")
        if f.get("location"): parts.append(f"[lieu] {f['location']}")
        if f.get("time"): parts.append(f"[temps] {f['time']}")
        return " ".join(parts)
    
def test_all_stories():
    StoryDatabase.initialize()
    story_ids = StoryDatabase.list_stories()
    for story_id in story_ids:
        test_story(story_id, save_story=True)

def test_story(story_id, save_story: bool = False):
    new_stories = []
    StoryDatabase.initialize()
    story = StoryDatabase.get_story(story_id)

    if story["generalized"]:
        return

    factoids = story.get("factoids")

    print("\nHistoire originale :")
    for f in factoids:
        parts = [f"[sujet] {f['subject']}", f"[predicat] {f['predicate']}"]
        if f.get("object"): parts.append(f"[objet] {f['object']}")
        if f.get("location"): parts.append(f"[lieu] {f['location']}")
        if f.get("time"): parts.append(f"[temps] {f['time']}")
        print(" ".join(parts))

    generalizer = StoryGeneralizer()
    generalized_story = generalizer.generalize_factoid_story(story["id"], factoids, story["domain"])

    if save_story:
        StoryDatabase.add_story(generalized_story, generalized=True)

    print("\nHistoire originale :")
    for f in factoids:
        parts = [f"[sujet] {f['subject']}", f"[predicat] {f['predicate']}"]
        if f.get("object"): parts.append(f"[objet] {f['object']}")
        if f.get("location"): parts.append(f"[lieu] {f['location']}")
        if f.get("time"): parts.append(f"[temps] {f['time']}")
        print(" ".join(parts))

    print("\nHistoire généralisée :")
    if generalized_story == None:
        print("Pas de généralisation trouvée")
    else:
        new_stories.append(generalized_story)
        for f in generalized_story["factoids"]:
            parts = [f"[sujet] {f['subject']}", f"[predicat] {f['predicate']}"]
            if f.get("object"): parts.append(f"[objet] {f['object']}")
            if f.get("location"): parts.append(f"[lieu] {f['location']}")
            if f.get("time"): parts.append(f"[temps] {f['time']}")
            print(" ".join(parts))

if __name__ == "__main__":
    test_all_stories()