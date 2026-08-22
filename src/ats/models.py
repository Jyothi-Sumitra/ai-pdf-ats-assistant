from pydantic import BaseModel, Field
from typing import List


class ATSAnalysis(BaseModel):
    """
    Analysis produced by the LLM.
    The LLM does NOT calculate the final ATS score.
    """

    matching_skills: List[str] = Field(
        description=(
            "Skills or skill concepts from the job description "
            "that are clearly demonstrated in the resume"
        )
    )

    missing_skills: List[str] = Field(
        description=(
            "Important skills or requirements from the job description "
            "that are not clearly demonstrated in the resume"
        )
    )

    matching_keywords: List[str] = Field(
        description=(
            "Important keywords or concepts represented in both "
            "the job description and resume"
        )
    )

    missing_keywords: List[str] = Field(
        description=(
            "Important keywords or concepts from the job description "
            "that are not represented in the resume"
        )
    )

    experience_match: str = Field(
        description=(
            "Assessment of how well the candidate's experience and "
            "projects align with the job requirements"
        )
    )

    strengths: List[str] = Field(
        description="Strong aspects of the resume for this specific job"
    )

    recommendations: List[str] = Field(
        description=(
            "Specific and actionable suggestions for improving "
            "the resume for this job"
        )
    )


class ATSResult(BaseModel):
    """
    Final result shown to the user.
    """

    overall_score: int = Field(
        ge=0,
        le=100,
        description="Final overall ATS score from 0 to 100"
    )

    match_level: str = Field(
        description=(
            "Overall match category. Must be exactly one of: "
            "'Excellent Match', 'Strong Match', 'Moderate Match', "
            "'Weak Match', or 'Poor Match'."
        )
    )

    analysis: ATSAnalysis