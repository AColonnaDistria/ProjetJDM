import json
import os
import re
from typing import List, Dict, Any

class FactoidExtractor:
    """
    Classe permettant d'extraire des factoïdes (triplets étendus) à partir d'histoires structurées.
    Tous les factoïdes sont stockés dans un seul fichier JSON : all_factoids.json.
    """

    def __init__(self, stories_dir: str = "data/stories", output_file: str = "data/factoids/all_factoids.json"):
        self.stories_dir = stories_dir
        self.output_file = output_file
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        self.factoids = self._load_existing_factoids()
        self.counter = self._init_counter()

    def _init_counter(self) -> int:
        return max((f["id"] for f in self.factoids), default=0) + 1

    def _load_existing_factoids(self) -> List[Dict[str, Any]]:
        if os.path.exists(self.output_file):
            with open(self.output_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    def _extract_factoid_components(self, sentence: str) -> Dict[str, Any]:
        pattern = re.compile(r"\[(sujet|predicat|objet|lieu|temps)\]\s*([^\[]+)")
        matches = pattern.findall(sentence)
        factoid = {"subject": "", "predicate": "", "object": "", "location": "", "time": ""}
        for role, value in matches:
            if role == "sujet":
                factoid["subject"] = value.strip().lower()
            elif role == "predicat":
                factoid["predicate"] = value.strip().lower()
            elif role == "objet":
                factoid["object"] = value.strip().lower()
            elif role == "lieu":
                factoid["location"] = value.strip().lower()
            elif role == "temps":
                factoid["time"] = value.strip().lower()
        return factoid

    def extract_factoids_from_story(self, story: Dict[str, Any]) -> List[Dict[str, Any]]:
        sentences = story.get("original_sentences", [])
        story_id = story.get("id", "unknown")
        new_factoids = []

        for sentence in sentences:
            factoid = self._extract_factoid_components(sentence)
            factoid["original_sentence"] = sentence
            factoid["story_id"] = story_id

            factoid_record = {
                "id": self.counter,
                "subject": factoid["subject"],
                "predicate": factoid["predicate"],
                "object": factoid["object"],
                "location": factoid["location"],
                "time": factoid["time"],
                "stories": [story_id],
                "original_sentence": sentence
            }
            self.factoids.append(factoid_record)
            new_factoids.append(factoid_record)
            self.counter += 1

        return new_factoids

    def extract_all_factoids(self) -> List[Dict[str, Any]]:
        results = []

        for filename in os.listdir(self.stories_dir):
            if filename.endswith(".json"):
                file_path = os.path.join(self.stories_dir, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    story = json.load(f)
                extracted = self.extract_factoids_from_story(story)
                results.extend(extracted)

        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(self.factoids, f, ensure_ascii=False, indent=2)

        return results


if __name__ == "__main__":
    extractor = FactoidExtractor()
    result = extractor.extract_all_factoids()
    print(f"Extrait {len(result)} nouveaux factoïdes dans un seul fichier.")