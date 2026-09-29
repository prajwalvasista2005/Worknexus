import re
import json
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple, Optional
import difflib

DEFAULT_SKILLS_PATH = Path(__file__).resolve().parent.parent / "data" / "skills.json"

# Fixed deterministic confidence scores per contract specifications
CONF_EXACT_NAME = 0.99
CONF_EXACT_ALIAS = 0.96
CONF_NORM_PHRASE = 0.90
CONF_FUZZY = 0.80

# Words that collide with common English lowercase words / stopwords
CASE_SENSITIVE_ACRONYMS = {"CAN", "IT", "IS", "AS", "IN", "AI", "OR", "AND", "BE", "DO", "GO", "R", "C"}

def normalize_phrase(text: str) -> str:
    """Normalizes a phrase for phrase-level matching (collapses spaces, removes hyphens/punctuation)."""
    if not text:
        return ""
    t = re.sub(r"[\/\-_\.]", " ", text.lower())
    t = re.sub(r"[^\w\s]", "", t)
    return " ".join(t.strip().split())

class SkillExtractor:
    """
    NLP/Rule-based Skill Extraction engine connected directly to canonical taxonomy normalization.
    Implements deterministic confidence scoring:
      - Exact canonical name match: 0.99
      - Exact alias match:          0.96
      - Normalized phrase match:    0.90
      - Conservative fuzzy match:   0.80
    """

    def __init__(self, skills_json_path: Optional[str] = None):
        path = Path(skills_json_path) if skills_json_path else DEFAULT_SKILLS_PATH
        if not path.exists():
            raise FileNotFoundError(f"Canonical skill taxonomy not found at {path}")

        with open(path, "r", encoding="utf-8") as f:
            self.taxonomy: List[Dict[str, Any]] = json.load(f)

        self._build_index()

    def _build_index(self):
        """Builds lookup structures for rapid boundary-safe matching."""
        self.skills_by_id: Dict[str, Dict[str, Any]] = {}
        self.exact_name_patterns: List[Tuple[re.Pattern, str, str]] = []
        self.exact_alias_patterns: List[Tuple[re.Pattern, str, str]] = []
        self.norm_phrase_map: Dict[str, List[str]] = {}

        # Indexed fuzzy targets grouped by word count:
        # word_count -> list of (norm_target_phrase, skill_id, list_of_words, first_char)
        self.fuzzy_targets_by_len: Dict[int, List[Tuple[str, str, List[str], str]]] = {}

        for skill in self.taxonomy:
            s_id = skill["id"]
            name = skill["name"]
            aliases = skill.get("aliases", [])
            self.skills_by_id[s_id] = skill

            # 1. Exact Canonical Name Pattern (0.99)
            esc_name = re.escape(name)
            p_name = re.compile(rf"(?<!\w){esc_name}(?!\w)", re.IGNORECASE)
            self.exact_name_patterns.append((p_name, s_id, name))

            norm_name = normalize_phrase(name)
            if norm_name and norm_name not in [w.lower() for w in CASE_SENSITIVE_ACRONYMS]:
                self.norm_phrase_map.setdefault(norm_name, []).append(s_id)
                w_list = norm_name.split()
                w_cnt = len(w_list)
                # Only index multi-word phrases or long technical terms for fuzzy matching
                if (w_cnt == 1 and len(norm_name) >= 10) or (w_cnt >= 2 and len(norm_name) >= 6):
                    self.fuzzy_targets_by_len.setdefault(w_cnt, []).append((norm_name, s_id, w_list, norm_name[0]))

            # 2. Exact Alias Patterns (0.96)
            for alias in aliases:
                alias_clean = alias.strip()
                if not alias_clean:
                    continue
                esc_alias = re.escape(alias_clean)

                if alias_clean.upper() in CASE_SENSITIVE_ACRONYMS:
                    p_alias = re.compile(rf"(?<!\w){esc_alias}(?!\w)")
                else:
                    p_alias = re.compile(rf"(?<!\w){esc_alias}(?!\w)", re.IGNORECASE)

                self.exact_alias_patterns.append((p_alias, s_id, alias_clean))

                norm_alias = normalize_phrase(alias_clean)
                if norm_alias and norm_alias not in [w.lower() for w in CASE_SENSITIVE_ACRONYMS]:
                    self.norm_phrase_map.setdefault(norm_alias, []).append(s_id)
                    w_list = norm_alias.split()
                    w_cnt = len(w_list)
                    if (w_cnt == 1 and len(norm_alias) >= 10) or (w_cnt >= 2 and len(norm_alias) >= 6):
                        self.fuzzy_targets_by_len.setdefault(w_cnt, []).append((norm_alias, s_id, w_list, norm_alias[0]))

    def _is_conservative_fuzzy_match(
        self,
        candidate_phrase: str,
        cand_words: List[str],
        target_phrase: str,
        target_words: List[str]
    ) -> bool:
        """
        Conservative fuzzy verification ensuring false negatives are preferred over false positives.
        - Single words: only permitted for technical terms length >= 10 chars, requiring similarity >= 0.95.
        - Multi-word phrases: exact word count match, each constituent word token >= 0.88 similarity,
          and overall phrase similarity >= 0.92.
        """
        w_cnt = len(target_words)
        if len(cand_words) != w_cnt:
            return False

        if w_cnt == 1:
            cand_w = cand_words[0]
            targ_w = target_words[0]
            if len(cand_w) < 10 or len(targ_w) < 10:
                return False
            if abs(len(cand_w) - len(targ_w)) > 1:
                return False
            ratio = difflib.SequenceMatcher(None, cand_w, targ_w).ratio()
            # Must exceed 0.95 (e.g. 18/19 = 0.947 is rejected to block contractor vs contactor)
            return ratio >= 0.95

        else:
            # Multi-word: check every constituent word token alignment
            for c_w, t_w in zip(cand_words, target_words):
                if c_w == t_w:
                    continue
                # For short tokens within multi-word (e.g. "and" vs "aid"), require exact match
                if len(t_w) <= 4 and c_w != t_w:
                    return False
                w_ratio = difflib.SequenceMatcher(None, c_w, t_w).ratio()
                if w_ratio < 0.88:
                    return False

            phrase_ratio = difflib.SequenceMatcher(None, candidate_phrase, target_phrase).ratio()
            return phrase_ratio >= 0.92

    def extract_skills(self, text: str) -> List[Dict[str, Any]]:
        """
        Extracts skills from text and returns canonical skill_id and confidence_score.
        Output shape: [{"skill_id": "SK_...", "confidence_score": float}]
        """
        if not text or not isinstance(text, str):
            return []

        extracted: Dict[str, float] = {}

        # Step 1: Exact Canonical Name Match (0.99)
        for pattern, s_id, _ in self.exact_name_patterns:
            if pattern.search(text):
                extracted[s_id] = max(extracted.get(s_id, 0.0), CONF_EXACT_NAME)

        # Step 2: Exact Alias Match (0.96)
        for pattern, s_id, _ in self.exact_alias_patterns:
            if pattern.search(text):
                extracted[s_id] = max(extracted.get(s_id, 0.0), CONF_EXACT_ALIAS)

        # Step 3: Normalized Phrase Match (0.90)
        norm_text = normalize_phrase(text)
        words = norm_text.split()
        num_words = len(words)

        for n in range(1, 6):
            for i in range(num_words - n + 1):
                phrase = " ".join(words[i : i + n])
                if phrase in self.norm_phrase_map:
                    for s_id in self.norm_phrase_map[phrase]:
                        if s_id not in extracted:
                            extracted[s_id] = CONF_NORM_PHRASE

        # Step 4: Conservative Fuzzy Match (0.80)
        for n, targets in self.fuzzy_targets_by_len.items():
            if n > num_words:
                continue
            for i in range(num_words - n + 1):
                cand_words = words[i : i + n]
                phrase = " ".join(cand_words)
                first_c = phrase[0]

                for target_phrase, s_id, target_words, target_first_c in targets:
                    if extracted.get(s_id, 0.0) >= CONF_NORM_PHRASE:
                        continue
                    if first_c == target_first_c:
                        if self._is_conservative_fuzzy_match(phrase, cand_words, target_phrase, target_words):
                            extracted[s_id] = max(extracted.get(s_id, 0.0), CONF_FUZZY)

        result = [
            {"skill_id": s_id, "confidence_score": round(score, 2)}
            for s_id, score in sorted(
                extracted.items(),
                key=lambda x: (-x[1], x[0])
            )
        ]
        return result


_default_extractor: Optional[SkillExtractor] = None

def get_extractor() -> SkillExtractor:
    global _default_extractor
    if _default_extractor is None:
        _default_extractor = SkillExtractor()
    return _default_extractor

def extract_skills(text: str) -> List[Dict[str, Any]]:
    extractor = get_extractor()
    return extractor.extract_skills(text)
