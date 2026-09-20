from typing import List, Optional
from ..models.entities import Employer, EmployerFeedback, EmployerFeedbackSignal
from ..schemas.schemas import (
    EmployerFeedbackCreateSchema,
    EmployerFeedbackResponseSchema,
    EmployerFeedbackSignalItem
)
from .ml_adapter import MLAdapter

class EmployerService:

    @staticmethod
    def submit_feedback(
        db,
        feedback_in: EmployerFeedbackCreateSchema,
        ml_adapter: MLAdapter
    ) -> EmployerFeedbackResponseSchema:
        # 1. Fetch Employer to obtain authoritative trust_weight
        employer = None
        if hasattr(db, "employers") and feedback_in.employer_id in db.employers:
            employer = db.employers[feedback_in.employer_id]
        elif hasattr(db, "query"):
            employer = db.query(Employer).filter(lambda e: e.id == feedback_in.employer_id).first()
            
        trust_weight = float(employer.trust_weight) if employer and getattr(employer, "trust_weight", None) is not None else 1.0

        # 2. Persist feedback entity
        fb = EmployerFeedback(
            id=None,
            employer_id=feedback_in.employer_id,
            course_id=feedback_in.course_id,
            rating=feedback_in.rating,
            comments=feedback_in.comments
        )
        db.add(fb)
        db.flush()

        # 3. Invoke ML Engine via MLAdapter
        ml_result = ml_adapter.analyze_employer_feedback({
            "feedback_id": str(fb.id),
            "employer_id": fb.employer_id,
            "course_id": fb.course_id,
            "trust_weight": trust_weight,
            "comments": fb.comments
        })

        # 4. Persist detected signals
        signal_items: List[EmployerFeedbackSignalItem] = []
        for sig in ml_result.detected_skills:
            sk_id = sig["skill_id"]
            conf = float(sig.get("confidence_score", 0.96))
            sig_trust = float(sig.get("trust_weight", trust_weight))
            w_sig = float(sig.get("weighted_signal", round(conf * sig_trust, 4)))

            fb_signal = EmployerFeedbackSignal(
                id=None,
                feedback_id=fb.id,
                skill_id=sk_id,
                confidence_score=conf,
                trust_weight=sig_trust,
                weighted_signal=w_sig
            )
            db.add(fb_signal)
            signal_items.append(EmployerFeedbackSignalItem(
                skill_id=sk_id,
                confidence_score=conf,
                trust_weight=sig_trust,
                weighted_signal=w_sig
            ))

        db.commit()
        db.refresh(fb)

        return EmployerFeedbackResponseSchema(
            id=fb.id,
            employer_id=fb.employer_id,
            course_id=fb.course_id,
            comments=fb.comments,
            rating=fb.rating,
            signals=signal_items
        )
