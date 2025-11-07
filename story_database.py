import os
import json
from typing import List, Dict, Optional

class StoryDatabase:
    stories: Dict[str, Dict] = {}
    factoids: Dict[str, List[Dict]] = {"generalized": [], "not_generalized": []}
    valid_terms: List[str] = []
    valid_relations: Dict[str, List[Dict[str, str]]] = {}

    storage_dir: str = "data/stories"
    factoids_file: str = "data/factoids.json"
    valid_terms_file: str = "data/valid_terms.json"
    valid_relations_file: str = "data/valid_relations.json"

    @staticmethod
    def initialize(storage_dir: str = "data/stories"):
        StoryDatabase.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        StoryDatabase.load_all_stories()
        StoryDatabase.load_all_factoids()
        StoryDatabase.load_valid_terms()
        StoryDatabase.load_valid_relations()

    @staticmethod
    def add_story(story: Dict, generalized: bool = False):
        story_id = story.get("id")
        if not story_id:
            raise ValueError("Story must have an 'id' field.")

        StoryDatabase.stories[story_id] = story
        StoryDatabase.stories[story_id]["generalized"] = generalized
        StoryDatabase._save_story_to_file(story)

        factoid_list_key = "generalized" if generalized else "not_generalized"
        for new_factoid in story.get("factoids", []):
            matched = False
            for existing in StoryDatabase.factoids[factoid_list_key]:
                if (existing.get("subject") == new_factoid.get("subject") and
                    existing.get("predicate") == new_factoid.get("predicate") and
                    existing.get("object") == new_factoid.get("object") and
                    existing.get("location") == new_factoid.get("location") and
                    existing.get("time") == new_factoid.get("time")):

                    stories_id = existing.setdefault("stories_id", [])
                    if story_id not in stories_id:
                        stories_id.append(story_id)
                    matched = True
                    break

            if not matched:
                factoid_copy = new_factoid.copy()
                factoid_copy["stories_id"] = [story_id]
                StoryDatabase.factoids[factoid_list_key].append(factoid_copy)

        StoryDatabase._save_all_factoids()

    @staticmethod
    def _save_story_to_file(story: Dict):
        story_id = story["id"]
        filepath = os.path.join(StoryDatabase.storage_dir, f"{story_id}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(story, f, ensure_ascii=False, indent=4)

    @staticmethod
    def _save_all_factoids():
        with open(StoryDatabase.factoids_file, "w", encoding="utf-8") as f:
            json.dump(StoryDatabase.factoids, f, ensure_ascii=False, indent=4)

    @staticmethod
    def save_valid_terms():
        os.makedirs(os.path.dirname(StoryDatabase.valid_terms_file), exist_ok=True)
        with open(StoryDatabase.valid_terms_file, "w", encoding="utf-8") as f:
            json.dump(StoryDatabase.valid_terms, f, ensure_ascii=False, indent=4)

    @staticmethod
    def save_valid_relations():
        os.makedirs(os.path.dirname(StoryDatabase.valid_relations_file), exist_ok=True)
        with open(StoryDatabase.valid_relations_file, "w", encoding="utf-8") as f:
            json.dump(StoryDatabase.valid_relations, f, ensure_ascii=False, indent=4)

    @staticmethod
    def load_valid_terms():
        if os.path.exists(StoryDatabase.valid_terms_file):
            with open(StoryDatabase.valid_terms_file, "r", encoding="utf-8") as f:
                StoryDatabase.valid_terms = json.load(f)

    @staticmethod
    def load_valid_relations():
        if os.path.exists(StoryDatabase.valid_relations_file):
            with open(StoryDatabase.valid_relations_file, "r", encoding="utf-8") as f:
                StoryDatabase.valid_relations = json.load(f)

    @staticmethod
    def is_valid_term(term: str) -> bool:
        return term in StoryDatabase.valid_terms

    @staticmethod
    def is_valid_relation(relation_type: str, node1: str, node2: str) -> bool:
        if relation_type not in StoryDatabase.valid_relations:
            return False
        return any(rel.get("node1") == node1 and rel.get("node2") == node2 for rel in StoryDatabase.valid_relations[relation_type])

    @staticmethod
    def add_valid_term(term: str):
        if term not in StoryDatabase.valid_terms:
            StoryDatabase.valid_terms.append(term)
        StoryDatabase.save_valid_terms()

    @staticmethod
    def add_valid_relation(relation_type: str, node1: str, node2: str):
        if relation_type not in StoryDatabase.valid_relations:
            StoryDatabase.valid_relations[relation_type] = []
        if not any(rel.get("node1") == node1 and rel.get("node2") == node2 for rel in StoryDatabase.valid_relations[relation_type]):
            StoryDatabase.valid_relations[relation_type].append({"node1": node1, "node2": node2})
        StoryDatabase.save_valid_relations()

    @staticmethod
    def get_factoid_by_id(factoid_id: str) -> Optional[Dict]:
        for group in ["generalized", "not_generalized"]:
            for factoid in StoryDatabase.factoids[group]:
                if factoid.get("id") == factoid_id:
                    return factoid
        return None

    @staticmethod
    def find_factoid(subject: str, predicate: str, object_: str = None, location: str = None, time: str = None, generalized: Optional[bool] = None) -> Optional[Dict]:
        keys = ["generalized", "not_generalized"] if generalized is None else (
            ["generalized"] if generalized else ["not_generalized"]
        )
        for key in keys:
            for factoid in StoryDatabase.factoids[key]:
                if (factoid.get("subject") == subject and
                    factoid.get("predicate") == predicate and
                    factoid.get("object") == object_ and
                    factoid.get("location") == location and
                    factoid.get("time") == time):
                    return factoid
        return None

    @staticmethod
    def list_factoids(generalized: Optional[bool] = None) -> List[Dict]:
        if generalized is None:
            return StoryDatabase.factoids["generalized"] + StoryDatabase.factoids["not_generalized"]
        key = "generalized" if generalized else "not_generalized"
        return StoryDatabase.factoids[key]

    @staticmethod
    def get_story(story_id: str) -> Dict:
        return StoryDatabase.stories.get(story_id)

    @staticmethod
    def load_all_stories():
        for filename in os.listdir(StoryDatabase.storage_dir):
            if filename.endswith(".json") and filename != os.path.basename(StoryDatabase.factoids_file):
                with open(os.path.join(StoryDatabase.storage_dir, filename), "r", encoding="utf-8") as f:
                    story = json.load(f)
                    StoryDatabase.stories[story["id"]] = story

    @staticmethod
    def load_all_factoids():
        if os.path.exists(StoryDatabase.factoids_file):
            with open(StoryDatabase.factoids_file, "r", encoding="utf-8") as f:
                StoryDatabase.factoids = json.load(f)
        else:
            StoryDatabase.factoids = {"generalized": [], "not_generalized": []}

    @staticmethod
    def list_stories() -> List[str]:
        return list(StoryDatabase.stories.keys())
