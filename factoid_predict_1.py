import os
import json
from typing import List, Dict
from story_database import StoryDatabase
from story_generator import StoryGenerator
from factoid_extractor import FactoidExtractor
from jdm_client import JDMClient

class FactoidPredict1:
    def __init__(self, sample_size: int = 4, subject_weight : float = 1.0, predicate_weight : float = 2, object_weight : float = 1, location_weight : float = 0.25, time_weight : float = 0.25, include_generalized: bool = False, stories_dir: str = "data/stories", factoids_dir: str = "data/factoids"):
        self.stories_dir = stories_dir
        self.factoids_dir = factoids_dir
        self.extractor = FactoidExtractor()

        self.subject_weight = subject_weight
        self.predicate_weight = predicate_weight
        self.object_weight = object_weight
        self.location_weight = location_weight
        self.time_weight = time_weight

        self.include_generalized = include_generalized

        self.jdm = JDMClient(logging=False)

        self.sample_size = sample_size

        self.story_generator = StoryGenerator()

        StoryDatabase.initialize()

    def _factoid_text(self, factoid: Dict) -> str:
        parts = []
        if factoid.get("subject"):
            parts.append(f"[sujet] {factoid['subject']}")
        if factoid.get("predicate"):
            parts.append(f"[predicat] {factoid['predicate']}")
        if factoid.get("object"):
            parts.append(f"[objet] {factoid['object']}")
        if factoid.get("location"):
            parts.append(f"[lieu] {factoid['location']}")
        if factoid.get("time"):
            parts.append(f"[temps] {factoid['time']}")
        return " ".join(parts)

    def predict_missing(self, story_lines: List[str]) -> List[str]:
        predictions = []
        all_subjects = set()

        for line in story_lines:
            if '?' not in line:
                all_subjects.add(self.extractor._extract_factoid_components(line)["subject"].lower())

        for i in range(len(story_lines)):
            if story_lines[i].strip() == "?":
                prev_line = story_lines[i - 1] if i > 0 else None
                next_line = story_lines[i + 1] if i < len(story_lines) - 1 else None

                pred_previous = self._predict_from_previous(prev_line, all_subjects)
                pred_next = self._predict_from_next(next_line, all_subjects)

                pred_possibles = pred_previous + pred_next
                pred_possibles = sorted(pred_possibles, key = lambda x: x[0], reverse=True)

                if pred_possibles == []:
                    pred = "?"
                else:
                    pred_subject = pred_possibles[0][1]["subject"]
                    story_id_origin = pred_possibles[0][2]
                    if not pred_subject.lower() in all_subjects:
                        # sélectionne un sujet le plus sémantiquement proche
                        # checker r_syn, r_masc, r_fem
                        
                        subject_found = None
                        if not '(' in pred_subject:
                            for subject in all_subjects:
                                if self.jdm.has_relation(pred_subject, subject, "r_masc"):
                                    # derivation masculin
                                    print("Deriv masculin")
                                    subject_found = subject
                                elif self.jdm.has_relation(pred_subject, subject, "r_fem"):
                                    # derivation feminin
                                    print("Deriv feminin")
                                    subject_found = subject
                                elif self.jdm.has_relation(pred_subject, subject, "r_syn"):
                                    # derivation synonyme
                                    print("Deriv syn")
                                    subject_found = subject
                        else:
                            print(pred_subject)
                            p_subject = pred_subject.strip("()")
                            if ':' in p_subject:
                                p_subject = p_subject.split(':')[0]
                            # on suppose a present qu'on remplace toutes les occurences de pred_subject par subject dans l'histoire originale
                            origin_story = StoryDatabase.get_story(story_id_origin)
                            for subject in all_subjects:
                                new_factoids = []
                                for factoid in origin_story["factoids"]:
                                    new_factoid = factoid.copy()
                                    if factoid["subject"] == pred_subject:
                                        new_factoid["subject"] = subject
                                    elif factoid["object"] == pred_subject:
                                        new_factoid["object"] = subject

                                    new_factoid["subject"] = new_factoid["subject"].strip("()")
                                    new_factoid["object"] = new_factoid["object"].strip("()")
                                    if ':' in new_factoid["subject"]:
                                        new_factoid["subject"] = new_factoid["subject"].split(':')[0]
                                    if ':' in new_factoid["object"]:
                                        new_factoid["object"] = new_factoid["object"].split(':')[0]
                                    
                                    new_factoids.append(new_factoid)
                                            
                                test_story = {
                                    "id": "test",
                                    "domain": "test",
                                    "factoids": new_factoids
                                }         

                                if StoryGenerator.check_story_consistency(self, test_story, ignore = True):
                                    subject_found = subject

                        if subject_found != None:
                            pred_possibles[0][1]["subject"] = subject_found
                    pred = self._factoid_text(pred_possibles[0][1])

                predictions.append(pred)
        
        return predictions

    def check_terms(self, term1: str, term2: str, type:str) -> bool:
        if term1 == term2:
            return True
        
        return False
    
    def check_pattern1(self, factoid1, factoid2) -> bool:
        # [sujet] X [predicate] Y [object] Z
        # [sujet] Z [predicate] V [object] X

        if self.check_terms(factoid1.get("subject"), factoid2.get("object"), "subject"):
            return True
        #if self.jdm.has_relation(factoid1.get("subject"), factoid2.get("object"), "r_syn") and self.jdm.has_relation(factoid1.get("predicate"), factoid2.get("subject"), "r_patient") and self.jdm.has_relation(factoid2.get("predicate"), factoid1.get("subject"), "r_agent"):
        #    return True
        
        return False

    def check_pattern2(self, factoid1, factoid2) -> bool:
        # [sujet] X [predicate] Y [object] Z
        # [sujet] X [predicate] V [object] Z

        if self.check_terms(factoid1.get("subject"), factoid2.get("subject"), "subject") and self.check_terms(factoid1.get("object"), factoid2.get("object"), "object"):
            return True
        #if self.jdm.has_relation(factoid1.get("subject"), factoid2.get("subject"), "r_syn") and self.jdm.has_relation(factoid1.get("predicate"), factoid2.get("subject"), "r_agent") and self.jdm.has_relation(factoid2.get("predicate"), factoid1.get("subject"), "r_agent"):
        #    if self.jdm.has_relation(factoid1.get("object"), factoid2.get("object"), "r_syn") and self.jdm.has_relation(factoid1.get("predicate"), factoid2.get("object"), "r_patient") and self.jdm.has_relation(factoid2.get("predicate"), factoid1.get("object"), "r_patient"):
        #        return True
        
        return False
    
    def check_pattern3(self, factoid1, factoid2) -> bool:
        # [sujet] X [predicate] Y [object] Z
        # [sujet] X [predicate] V [object] W

        if self.check_terms(factoid1.get("subject"), factoid2.get("subject"), "subject"):
            return True
        #if self.jdm.has_relation(factoid1.get("subject"), factoid2.get("subject"), "r_syn") and self.jdm.has_relation(factoid1.get("predicate"), factoid2.get("subject"), "r_agent") and self.jdm.has_relation(factoid2.get("predicate"), factoid1.get("subject"), "r_agent"):
        #    return True
        
        return False
        
    def check_pattern4(self, factoid1, factoid2) -> bool:
        # [sujet] X1 [predicate] Y [object] Z
        # [sujet] X2 [predicate] V [object] Z

        if self.check_terms(factoid1.get("object"), factoid2.get("object"), "object"):
            return True
        #if self.jdm.has_relation(factoid1.get("object"), factoid2.get("object"), "r_syn") and self.jdm.has_relation(factoid1.get("predicate"), factoid2.get("object"), "r_patient") and self.jdm.has_relation(factoid2.get("predicate"), factoid1.get("object"), "r_patient"):
        #    return True
        
        return False

    def _predict_from_previous(self, prev_line: str, all_subjects: List[str]) -> str:
        candidates = []

        prev_factoid = self.extractor._extract_factoid_components(prev_line)
        for factoid in StoryDatabase.list_factoids():
            if len(candidates) >= self.sample_size:
                return candidates
            else:
                score = 0
                if self.check_terms(factoid.get("subject"), prev_factoid.get("subject"), "subject"):
                    score += self.subject_weight
                if self.check_terms(factoid.get("predicate"), prev_factoid.get("predicate"), "predicate"):
                    score += self.predicate_weight
                if self.check_terms(factoid.get("object"), prev_factoid.get("object"), "object"):
                    score += self.object_weight

                if factoid.get("location") != "" and self.check_terms(factoid.get("location"), prev_factoid.get("location"), "location"):
                    score += self.location_weight
                if factoid.get("time") != "" and self.check_terms(factoid.get("time"), prev_factoid.get("time"), "time"):
                    score += self.time_weight

                if score >= 2.0:
                    found = False
                    for story_id in factoid.get("stories_id", []):
                        story = StoryDatabase.get_story(story_id)
                        if (self.include_generalized and story["generalized"]) or (not story["generalized"]):
                            factoids = story.get("factoids", [])
                            for i, f in enumerate(factoids):
                                if f["id"] == factoid["id"] and i + 1 < len(factoids):
                                    next_factoid = factoids[i + 1].copy()
                                    if self.check_pattern1(factoids[i], next_factoid):
                                        # [sujet] X [predicate] Y [object] Z
                                        # [sujet] Z [predicate] V [object] X
                                        next_factoid["object"] = prev_factoid.get("subject")
                                    elif self.check_pattern2(factoids[i], next_factoid):
                                        # [sujet] X [predicate] Y [object] Z
                                        # [sujet] X [predicate] V [object] Z
                                        next_factoid["subject"] = prev_factoid.get("subject")
                                        next_factoid["object"] = prev_factoid.get("object")
                                    elif self.check_pattern3(factoids[i], next_factoid):
                                        # [sujet] X [predicate] Y [object] Z
                                        # [sujet] X [predicate] V [object] W
                                        next_factoid["subject"] = prev_factoid.get("subject")
                                    elif self.check_pattern4(factoids[i], next_factoid):
                                        # [sujet] X1 [predicate] Y [object] Z
                                        # [sujet] X2 [predicate] V [object] Z
                                        next_factoid["object"] = prev_factoid.get("object")
                                    
                                    candidates.append((score, next_factoid, story_id))
                                    break
                            if found:
                                break
                
        return candidates

    def _predict_from_next(self, next_line: str, all_subjects: List[str]) -> str:
        candidates = []

        next_factoid = self.extractor._extract_factoid_components(next_line)
        for factoid in StoryDatabase.list_factoids():
            if len(candidates) >= self.sample_size:
                return candidates
            else:
                score = 0
                if factoid.get("subject") == next_factoid.get("subject"):
                    score += self.subject_weight
                if factoid.get("predicate") == next_factoid.get("predicate"):
                    score += self.predicate_weight
                if factoid.get("object") == next_factoid.get("object"):
                    score += self.object_weight

                if factoid.get("location") != "" and factoid.get("location") == next_factoid.get("location"):
                    score += self.location_weight
                if factoid.get("time") != "" and factoid.get("time") == next_factoid.get("time"):
                    score += self.time_weight

                if score >= 2.0:
                    found = False
                    for story_id in factoid.get("stories_id", []):
                        story = StoryDatabase.get_story(story_id)
                        factoids = story.get("factoids", [])
                        for i, f in enumerate(factoids):
                            if f["id"] == factoid["id"] and i > 0:
                                prev_factoid = factoids[i - 1].copy()

                                if self.check_pattern1(prev_factoid, factoids[i]):
                                    # [sujet] X [predicate] Y [object] Z
                                    # [sujet] Z [predicate] V [object] X
                                    prev_factoid["subject"] = next_factoid.get("object")
                                elif self.check_pattern2(prev_factoid, factoids[i]):
                                    # [sujet] X [predicate] Y [object] Z
                                    # [sujet] X [predicate] V [object] Z
                                    prev_factoid["subject"] = next_factoid.get("subject")
                                    prev_factoid["object"] = next_factoid.get("object")
                                elif self.check_pattern3(prev_factoid, factoids[i]):
                                    # [sujet] X [predicate] Y [object] Z
                                    # [sujet] X [predicate] V [object] W
                                    prev_factoid["subject"] = next_factoid.get("subject")
                                elif self.check_pattern4(factoids[i], next_factoid):
                                    # [sujet] X1 [predicate] Y [object] Z
                                    # [sujet] X2 [predicate] V [object] Z
                                    prev_factoid["object"] = next_factoid.get("object")
                                
                                found = True
                                candidates.append((score, prev_factoid, story_id))
                                break
                        if found:
                            break
        return candidates
