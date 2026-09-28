import unittest
import json
from pathlib import Path
from ml.demand.demand_aggregator import DemandAggregator, DEFAULT_INPUT_ARTIFACT_PATH, DEFAULT_TAXONOMY_PATH

class TestDemandAggregator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.aggregator = DemandAggregator()
        cls.artifact = cls.aggregator.aggregate()

    def test_01_total_job_count_matches_phase2(self):
        with open(DEFAULT_INPUT_ARTIFACT_PATH, 'r', encoding='utf-8') as f:
            p2_data = json.load(f)
        expected_total = len(p2_data['jobs'])
        self.assertEqual(self.artifact['metadata']['total_jobs'], expected_total)
        self.assertEqual(self.artifact['metadata']['total_jobs'], 295)

    def test_02_job_based_counting(self):
        # Verify that for any skill, job_count <= total_jobs and matches unique jobs containing that skill
        with open(DEFAULT_INPUT_ARTIFACT_PATH, 'r', encoding='utf-8') as f:
            p2_data = json.load(f)

        expected_counts = {}
        for job in p2_data['jobs']:
            seen_in_job = {s['skill_id'] for s in job.get('skills', [])}
            for sid in seen_in_job:
                expected_counts[sid] = expected_counts.get(sid, 0) + 1

        for skill_entry in self.artifact['skills']:
            sid = skill_entry['skill_id']
            self.assertEqual(skill_entry['job_count'], expected_counts[sid])

    def test_03_demand_share_calculation(self):
        total_jobs = self.artifact['metadata']['total_jobs']
        for skill_entry in self.artifact['skills']:
            expected_share = round(skill_entry['job_count'] / total_jobs, 4)
            expected_pct = round((skill_entry['job_count'] / total_jobs) * 100.0, 2)
            self.assertEqual(skill_entry['demand_share'], expected_share)
            self.assertEqual(skill_entry['demand_percentage'], expected_pct)

    def test_04_source_normalization(self):
        source_demand = self.artifact['source_demand']
        self.assertIn('linkedin_india', source_demand)
        self.assertIn('naukri', source_demand)
        self.assertIn('parquet', source_demand)

        for src_name, src_data in source_demand.items():
            src_total = src_data['source_total_jobs']
            self.assertGreater(src_total, 0)
            for s in src_data['skills']:
                expected_share = round(s['source_job_count'] / src_total, 4)
                expected_pct = round((s['source_job_count'] / src_total) * 100.0, 2)
                self.assertEqual(s['source_demand_share'], expected_share)
                self.assertEqual(s['source_demand_percentage'], expected_pct)

    def test_05_zero_skill_jobs_in_denominator(self):
        meta = self.artifact['metadata']
        self.assertEqual(meta['total_jobs'], 295)
        self.assertEqual(meta['jobs_with_skills'], 211)
        self.assertEqual(meta['zero_skill_jobs'], 84)
        self.assertEqual(meta['jobs_with_skills'] + meta['zero_skill_jobs'], meta['total_jobs'])

    def test_06_all_skills_resolve_to_taxonomy(self):
        with open(DEFAULT_TAXONOMY_PATH, 'r', encoding='utf-8') as f:
            tax = json.load(f)
        valid_ids = {s['id'] for s in tax}
        for skill_entry in self.artifact['skills']:
            self.assertIn(skill_entry['skill_id'], valid_ids)

    def test_07_source_coverage_count(self):
        for skill_entry in self.artifact['skills']:
            sources = skill_entry['sources_present']
            self.assertEqual(skill_entry['source_coverage_count'], len(sources))
            self.assertTrue(1 <= skill_entry['source_coverage_count'] <= 3)

    def test_08_category_unique_job_counts(self):
        total_jobs = self.artifact['metadata']['total_jobs']
        for cat in self.artifact['categories']:
            self.assertLessEqual(cat['unique_jobs_with_category_skill'], total_jobs)
            expected_pct = round((cat['unique_jobs_with_category_skill'] / total_jobs) * 100.0, 2)
            self.assertEqual(cat['percentage_of_jobs_with_any_category_skill'], expected_pct)

    def test_09_co_occurrence_pairs(self):
        for pair in self.artifact['co_occurrence']:
            self.assertLess(pair['skill_a_id'], pair['skill_b_id'])
            self.assertGreater(pair['co_occurrence_count'], 0)
            self.assertLessEqual(pair['co_occurrence_count'], self.artifact['metadata']['total_jobs'])

    def test_10_determinism(self):
        second_run = DemandAggregator().aggregate()
        self.assertEqual(json.dumps(self.artifact, sort_keys=True), json.dumps(second_run, sort_keys=True))

    def test_11_no_raw_data_dependency(self):
        # DemandAggregator only requires Phase 2 artifact and skills.json
        agg = DemandAggregator(
            input_artifact_path=DEFAULT_INPUT_ARTIFACT_PATH,
            taxonomy_path=DEFAULT_TAXONOMY_PATH
        )
        res = agg.aggregate()
        self.assertEqual(res['metadata']['total_jobs'], 295)

    def test_12_temporal_safety_reporting(self):
        temp = self.artifact['temporal_analysis']
        self.assertEqual(temp['status'], 'not_available')
        self.assertIn('reason', temp)

if __name__ == '__main__':
    unittest.main()
