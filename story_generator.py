import os
from typing import Dict, List, Any
from factoid_extractor import FactoidExtractor
from jdm_client import JDMClient
from story_database import StoryDatabase

class StoryGenerator:
    def __init__(self, input_file: str = "histoires.txt", output_dir: str = "data/stories"):
        self.input_file = input_file
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.extractor = FactoidExtractor()
        self.jdm = JDMClient()
        StoryDatabase.initialize(output_dir)

    def load_and_store_stories(self):
        current_domain = None
        factoid_sentences = []
        story_counter = 1

        with open(self.input_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if '[' not in line:
                    if current_domain and factoid_sentences:
                        self._create_and_add_story(current_domain, factoid_sentences, story_counter)
                        story_counter += 1
                    current_domain = line
                    factoid_sentences = []
                else:
                    factoid_sentences.append(line)

            if current_domain and factoid_sentences:
                self._create_and_add_story(current_domain, factoid_sentences, story_counter)

    def _create_and_add_story(self, domain: str, sentences: List[str], story_id: int):
        story_identifier = f"{domain.lower().replace(' ', '_')}_{story_id}"
        factoids = []
        for idx, sentence in enumerate(sentences):
            factoid = self.extractor._extract_factoid_components(sentence)
            factoid["original_sentence"] = sentence.lower()
            factoid["story_id"] = story_identifier
            factoid["id"] = f"{story_identifier}_f{idx+1}"
            factoids.append(factoid)

        story = {
            "id": story_identifier,
            "domain": domain,
            "factoids": factoids
        }

        if self.check_story_consistency(story, force = True):
            StoryDatabase.add_story(story)

    def check_story_consistency(self, story: Dict[str, Any], force: bool = False, ignore: bool = False) -> bool:
        relation_checks = [
            (["r_agent"], lambda f: (f["predicate"], f["subject"])),
            (["r_patient", "r_instr"], lambda f: (f["predicate"], f["object"])),
            (["r_action_lieu"], lambda f: (f["predicate"], f["location"])),
            (["r_time"], lambda f: (f["predicate"], f["time"]))
        ]

        for factoid in story.get("factoids", []):
            terms = [factoid['subject'], factoid['predicate']]
            if factoid['object']:
                terms.append(factoid['object'])
            if factoid['location']:
                terms.append(factoid['location'])
            if factoid['time']:
                terms.append(factoid['time'])

            for term in terms:
                if StoryDatabase.is_valid_term(term):
                    continue
                node = self.jdm.get_node_by_name(term)
                if not node or 'id' not in node:
                    print(f'Terme "{term}" introuvable dans JDM.')
                    if force:
                        StoryDatabase.add_valid_term(term)
                    elif ignore:
                        return False
                    else:
                        resp = input("Souhaitez-vous l’ajouter aux termes valides ? (o/n) ").strip().lower()
                        if resp == 'o':
                            StoryDatabase.add_valid_term(term)
                        else:
                            return False

            for rel_group, extractor in relation_checks:
                src, tgt = extractor(factoid)
                if not src or not tgt:
                    continue
                found = False
                for rel_key in rel_group:
                    if StoryDatabase.is_valid_relation(rel_key, src, tgt) or self.jdm.has_relation(src, tgt, rel_key):
                        found = True
                        break
                if not found:
                    #print(f"Aucune relation valide trouvée entre {src} et {tgt} dans {rel_group}")
                    if force:
                        StoryDatabase.add_valid_relation(rel_group[0], src, tgt)
                    elif ignore:
                        return False
                    else:
                        resp = input("L’une de ces relations est-elle acceptable ? (o/n) ").strip().lower()
                        if resp == 'o':
                            StoryDatabase.add_valid_relation(rel_group[0], src, tgt)
                        else:
                            return False

        return True

if __name__ == "__main__":
    generator = StoryGenerator()
    generator.load_and_store_stories()
    print("Histoires importées avec succès.")
