import os
import json
from typing import List, Dict
from story_database import StoryDatabase
from factoid_extractor import FactoidExtractor
from factoid_predict_1 import FactoidPredict1

class StoryTest:
    def __init__(self, test_file: str = "tests.txt"):
        self.test_file = test_file
        self.predictor = FactoidPredict1(include_generalized=True)

    def run_all_tests(self):
        with open(self.test_file, 'r', encoding='utf-8') as f:
            story_counter = 0
            current_story = []

            for line in f:
                line = line.strip()
                if not line:
                    continue
                if '[' not in line and '?' not in line:
                    self._run_and_print(f"Histoire {story_counter}", current_story)
                    story_counter += 1
                    current_story = []
                else:
                    current_story.append(line)

            if current_story:
                self._run_and_print(f"Histoire {story_counter}", current_story)

    def _run_and_print(self, title: str, story_lines: List[str]):
        print(f"\n=== {title} ===")
        prediction = self.predictor.predict_missing(story_lines)
        id_prediction = 0
        for ligne in story_lines:
            if ligne == "?":
                print(">", prediction[id_prediction])
                id_prediction += 1
            else:
                print(ligne)

if __name__ == "__main__":
    storyTest = StoryTest()
    storyTest.run_all_tests()