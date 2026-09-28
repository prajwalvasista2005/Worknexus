import sys
import json
from typing import List

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')

from ml.extract import extract_skills
from ml.ingestion.loaders import load_linkedin_india_sample, load_naukri_sample

def test_contract_json_shape():
    print("\n--- TEST 1: Contract JSON Output Shape & Exact Fields ---")
    text = "EV technician experienced in BMS and CAN bus"
    result = extract_skills(text)
    
    print(f"Input:  '{text}'")
    print(f"Output: {json.dumps(result, indent=2)}")
    
    assert isinstance(result, list), "Output must be a list"
    assert len(result) >= 2, f"Expected at least 2 skills extracted, got {len(result)}"

    allowed_keys = {"skill_id", "confidence_score"}
    for item in result:
        assert isinstance(item, dict), "Each item must be a dictionary"
        assert set(item.keys()) == allowed_keys, f"Item has invalid keys: {item.keys()}. Must only have {allowed_keys}"
        assert isinstance(item["skill_id"], str) and item["skill_id"].startswith("SK_"), f"Invalid skill_id: {item['skill_id']}"
        assert isinstance(item["confidence_score"], (float, int)), f"Invalid confidence_score type: {type(item['confidence_score'])}"
        assert 0.0 <= item["confidence_score"] <= 1.0, f"Confidence score out of range: {item['confidence_score']}"

    print("  [PASS] Output matches frozen ML backend contract schema exactly.")


def test_fixed_confidence_scores():
    print("\n--- TEST 2: Deterministic Fixed Confidence Scores (0.99, 0.96, 0.90, 0.80) ---")
    
    # 1. Exact Canonical Name Match -> 0.99
    res1 = extract_skills("Specialist in Thermal Management for EVs")
    thermal = next((s for s in res1 if s["skill_id"] == "SK_THERMAL"), None)
    assert thermal is not None, "SK_THERMAL not found"
    print(f"  Exact Canonical Name ('Thermal Management'): {thermal}")
    assert thermal["confidence_score"] == 0.99, f"Expected 0.99, got {thermal['confidence_score']}"

    # 2. Exact Alias Match -> 0.96
    res2 = extract_skills("Looking for technician with BMS knowledge")
    bms = next((s for s in res2 if s["skill_id"] == "SK_BMS"), None)
    assert bms is not None, "SK_BMS not found"
    print(f"  Exact Alias ('BMS'): {bms}")
    assert bms["confidence_score"] == 0.96, f"Expected 0.96, got {bms['confidence_score']}"

    # 3. Normalized Phrase Match -> 0.90
    res3 = extract_skills("Proficient in Scikit / Learn modeling")
    sklearn = next((s for s in res3 if s["skill_id"] == "SK_SCIKIT_LEARN"), None)
    assert sklearn is not None, "SK_SCIKIT_LEARN not found"
    print(f"  Normalized Phrase ('Scikit / Learn'): {sklearn}")
    assert sklearn["confidence_score"] == 0.90, f"Expected 0.90, got {sklearn['confidence_score']}"

    # 4. Conservative Fuzzy Match -> 0.80
    # Multi-word minor typo: "Control Panel Wirng" (missing 'i' in wiring)
    res4 = extract_skills("Experienced in Control Panel Wirng for industrial plants")
    panel = next((s for s in res4 if s["skill_id"] == "SK_PANEL_WIRING"), None)
    assert panel is not None, "SK_PANEL_WIRING fuzzy match not found"
    print(f"  Conservative Fuzzy Match ('Control Panel Wirng'): {panel}")
    assert panel["confidence_score"] == 0.80, f"Expected 0.80, got {panel['confidence_score']}"

    print("  [PASS] All fixed deterministic confidence tiers verified.")


def test_fuzzy_false_positive_regressions():
    print("\n--- TEST 3: Six False-Positive Regression Tests ---")

    test_cases = [
        ("contractor role for software engineer", "SK_RELAYS", "contractor -> contactor"),
        ("transform data pipelines using python", "SK_TRANSFORMER", "transform -> transformer"),
        ("set up blockchain nodes and validators", "SK_NODEJS", "nodes -> nodejs"),
        ("lead backend engineer with cluster management expertise", "SK_CRM_RETAIL", "cluster management -> customer management"),
        ("the employee plays a vital role in our security architecture", "SK_VITAL_SIGNS", "vital -> vitals"),
        ("first and second level technical support", "SK_FIRST_AID", "first and -> first aid")
    ]

    for text, forbidden_skill_id, desc in test_cases:
        extracted = extract_skills(text)
        extracted_ids = [s["skill_id"] for s in extracted]
        print(f"  Testing: '{text}'")
        print(f"    Forbidden: {forbidden_skill_id} ({desc}) | Extracted: {extracted_ids}")
        assert forbidden_skill_id not in extracted_ids, f"REGRESSION DETECTED: '{text}' falsely triggered {forbidden_skill_id}!"
        print("    [PASS] Correctly rejected.")

    print("  [PASS] All 6 false-positive regressions successfully eliminated.")


def test_false_positive_avoidance():
    print("\n--- TEST 4: Word Boundary & Acronym Stopword Protection ---")
    
    negative_text = "The doctor is scanning patient records for cancer treatment, taking possession of task updates without broadcast."
    result = extract_skills(negative_text)
    
    extracted_ids = [s["skill_id"] for s in result]
    print(f"Negative Text: '{negative_text}'")
    print(f"Extracted IDs: {extracted_ids}")

    assert "SK_CAN" not in extracted_ids, "False positive: 'scanning' or 'cancer' triggered SK_CAN!"
    assert "SK_CAD_ELECTRICAL" not in extracted_ids, "False positive: 'broadcast' triggered CAD!"
    assert "SK_POS_SYSTEMS" not in extracted_ids, "False positive: 'possession' triggered POS!"
    assert "SK_AWS" not in extracted_ids, "False positive: 'task' triggered AWS!"

    print("  [PASS] Word boundary and false positive guards functioning correctly.")


def main():
    print("="*70)
    print("WORKNEXUS PHASE 1D — SKILL EXTRACTION & FUZZY SAFETY TEST")
    print("="*70)

    test_contract_json_shape()
    test_fixed_confidence_scores()
    test_fuzzy_false_positive_regressions()
    test_false_positive_avoidance()

    print("\n" + "="*70)
    print("[SUCCESS] ALL PHASE 1D TESTS PASSED FULLY!")
    print("="*70)

if __name__ == "__main__":
    main()
