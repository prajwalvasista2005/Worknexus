import unittest
from app.db.session import MockDatabaseSession
from app.models.entities import User, Skill, TargetRole, RoleSkill, StudentProfile, StudentSkillEvidence
from app.schemas.schemas import (
    TargetRoleCreateSchema,
    StudentProfileCreateSchema,
    StudentSkillEvidenceCreateSchema
)
from app.services.role_service import RoleService
from app.services.student_service import StudentService
from app.db.seed import seed_canonical_skills, seed_benchmark_roles, seed_demo_students

class TestPhase10DatabaseFoundation(unittest.TestCase):

    def setUp(self):
        self.db = MockDatabaseSession()
        # Seed skills
        seed_canonical_skills(self.db)

    def test_01_target_role_creation_and_retrieval(self):
        """Test TargetRole creation and retrieval with valid canonical skills."""
        schema = TargetRoleCreateSchema(
            id="ROLE_CLOUD_ARCHITECT",
            name="Cloud Solutions Architect",
            description="Designs resilient cloud infrastructures.",
            skill_ids=["SK_AWS", "SK_DOCKER", "SK_PYTHON"]
        )
        res = RoleService.create_role(self.db, schema)
        self.assertEqual(res.id, "ROLE_CLOUD_ARCHITECT")
        self.assertEqual(len(res.required_skills), 3)

        retrieved = RoleService.get_role(self.db, "ROLE_CLOUD_ARCHITECT")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "Cloud Solutions Architect")
        self.assertEqual(retrieved.required_skills, ["SK_AWS", "SK_DOCKER", "SK_PYTHON"])

    def test_02_target_role_invalid_skill_rejection(self):
        """Test TargetRole creation rejects non-existent skill IDs."""
        schema = TargetRoleCreateSchema(
            id="ROLE_INVALID",
            name="Invalid Role",
            skill_ids=["SK_NON_EXISTENT_999"]
        )
        with self.assertRaises(ValueError) as ctx:
            RoleService.create_role(self.db, schema)
        self.assertIn("not found in canonical taxonomy", str(ctx.exception))

    def test_03_student_profile_creation(self):
        """Test StudentProfile creation linked to existing User."""
        user = User(id=10, email="alice@student.org", role="Student")
        self.db.add(user)

        # Seed benchmark roles so target_role_id is valid
        seed_benchmark_roles(self.db)

        schema = StudentProfileCreateSchema(user_id=10, target_role_id="ROLE_DATA_ENGINEER")
        profile = StudentService.create_or_get_profile(self.db, schema)
        self.assertEqual(profile.user_id, 10)
        self.assertEqual(profile.target_role_id, "ROLE_DATA_ENGINEER")

        retrieved = StudentService.get_profile_by_user_id(self.db, 10)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.target_role_id, "ROLE_DATA_ENGINEER")

    def test_04_student_profile_invalid_user_rejection(self):
        """Test StudentProfile creation rejects non-existent user."""
        schema = StudentProfileCreateSchema(user_id=99999)
        with self.assertRaises(ValueError) as ctx:
            StudentService.create_or_get_profile(self.db, schema)
        self.assertIn("does not exist", str(ctx.exception))

    def test_05_student_skill_evidence_valid_types_and_strengths(self):
        """Test adding skill evidence with valid types and strength categories."""
        user = User(id=11, email="bob@student.org", role="Student")
        self.db.add(user)

        valid_types = ["self_reported", "course_completed", "project", "certification", "assessment"]
        valid_strengths = ["basic", "intermediate", "advanced"]

        for idx, (ev_type, strength) in enumerate(zip(valid_types, ["basic", "intermediate", "advanced", "advanced", "intermediate"])):
            ev_schema = StudentSkillEvidenceCreateSchema(
                skill_id="SK_PYTHON",
                evidence_type=ev_type,
                strength=strength,
                metadata={"test_idx": idx}
            )
            ev = StudentService.add_skill_evidence(self.db, user_id=11, evidence_in=ev_schema)
            self.assertEqual(ev.evidence_type, ev_type)
            self.assertEqual(ev.strength, strength)

        all_evidence = StudentService.get_student_evidence(self.db, user_id=11)
        self.assertEqual(len(all_evidence), 5)

    def test_06_student_skill_evidence_invalid_type_rejection(self):
        """Test student skill evidence rejects invalid evidence_type."""
        user = User(id=12, email="charlie@student.org", role="Student")
        self.db.add(user)

        ev_schema = StudentSkillEvidenceCreateSchema(
            skill_id="SK_PYTHON",
            evidence_type="magic_guess",
            strength="advanced"
        )
        with self.assertRaises(ValueError) as ctx:
            StudentService.add_skill_evidence(self.db, user_id=12, evidence_in=ev_schema)
        self.assertIn("Invalid evidence_type", str(ctx.exception))

    def test_07_student_skill_evidence_invalid_strength_rejection(self):
        """Test student skill evidence rejects invalid strength category."""
        user = User(id=13, email="david@student.org", role="Student")
        self.db.add(user)

        ev_schema = StudentSkillEvidenceCreateSchema(
            skill_id="SK_PYTHON",
            evidence_type="project",
            strength="expert_level_100"
        )
        with self.assertRaises(ValueError) as ctx:
            StudentService.add_skill_evidence(self.db, user_id=13, evidence_in=ev_schema)
        self.assertIn("Invalid strength category", str(ctx.exception))

    def test_08_multiple_legitimate_evidence_records_same_skill(self):
        """Test student can hold multiple distinct evidence records for the same skill."""
        user = User(id=14, email="emma@student.org", role="Student")
        self.db.add(user)

        # Record 1: Project with intermediate strength
        ev1 = StudentService.add_skill_evidence(
            self.db,
            user_id=14,
            evidence_in=StudentSkillEvidenceCreateSchema(
                skill_id="SK_PYTHON",
                evidence_type="project",
                strength="intermediate",
                metadata={"repo": "github.com/emma/fastapi-app"}
            )
        )
        # Record 2: Certification with advanced strength
        ev2 = StudentService.add_skill_evidence(
            self.db,
            user_id=14,
            evidence_in=StudentSkillEvidenceCreateSchema(
                skill_id="SK_PYTHON",
                evidence_type="certification",
                strength="advanced",
                metadata={"cert_name": "Certified Python Developer"}
            )
        )

        all_ev = StudentService.get_student_evidence(self.db, user_id=14)
        self.assertEqual(len(all_ev), 2)
        types = {e.evidence_type for e in all_ev}
        self.assertEqual(types, {"project", "certification"})

    def test_09_seed_benchmark_roles_integrity(self):
        """Test seed_benchmark_roles seeds exact Phase 6B synthetic roles and skills."""
        stats = seed_benchmark_roles(self.db)
        self.assertEqual(stats["roles_seeded"], 5)
        self.assertEqual(stats["role_skills_seeded"], 26) # 5+6+6+5+4 = 26

        roles = RoleService.list_roles(self.db)
        self.assertEqual(len(roles), 5)
        role_map = {r.id: r for r in roles}

        self.assertIn("ROLE_DATA_ENGINEER", role_map)
        self.assertEqual(role_map["ROLE_DATA_ENGINEER"].required_skills, ["SK_AIRFLOW", "SK_AWS", "SK_PYTHON", "SK_SPARK", "SK_SQL"])

        self.assertIn("ROLE_EV_TECHNICIAN", role_map)
        self.assertEqual(role_map["ROLE_EV_TECHNICIAN"].required_skills, ["SK_BATTERY_CELL", "SK_BMS", "SK_CAN", "SK_DIAG", "SK_HIGH_VOLTAGE", "SK_THERMAL"])

    def test_10_seed_demo_students_integrity(self):
        """Test seed_demo_students seeds benchmark demo student fixtures."""
        seed_benchmark_roles(self.db)
        stats = seed_demo_students(self.db)
        self.assertEqual(stats["students_seeded"], 5)
        self.assertGreaterEqual(stats["evidence_records_seeded"], 15)

        # Inspect STU_001 (User 1001)
        p1 = StudentService.get_profile_by_user_id(self.db, 1001)
        self.assertIsNotNone(p1)
        self.assertEqual(p1.target_role_id, "ROLE_DATA_ENGINEER")
        self.assertGreaterEqual(len(p1.evidence_records), 3)

if __name__ == "__main__":
    unittest.main()
