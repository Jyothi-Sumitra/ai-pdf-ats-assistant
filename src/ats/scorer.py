from .models import ATSAnalysis, ATSResult


def calculate_score(
    analysis: ATSAnalysis,
    resume_text: str,
    job_description: str
) -> ATSResult:

    # ---------------------------------
    # 1. Skill Match
    # ---------------------------------

    total_skills = (
        len(analysis.matching_skills)
        + len(analysis.missing_skills)
    )

    if total_skills > 0:
        skill_score = (
            len(analysis.matching_skills)
            / total_skills
        ) * 50
    else:
        skill_score = 0

    # ---------------------------------
    # 2. Keyword Match
    # ---------------------------------

    total_keywords = (
        len(analysis.matching_keywords)
        + len(analysis.missing_keywords)
    )

    if total_keywords > 0:
        keyword_score = (
            len(analysis.matching_keywords)
            / total_keywords
        ) * 20
    else:
        keyword_score = 0

    # ---------------------------------
    # 3. Experience Match
    # ---------------------------------

    experience_text = analysis.experience_match.lower()

    if any(
        phrase in experience_text
        for phrase in [
            "excellent",
            "strong",
            "highly matched",
            "well matched"
        ]
    ):
        experience_score = 15

    elif any(
        phrase in experience_text
        for phrase in [
            "moderate",
            "partial",
            "partially",
            "somewhat"
        ]
    ):
        experience_score = 10

    elif any(
        phrase in experience_text
        for phrase in [
            "limited",
            "weak"
        ]
    ):
        experience_score = 5

    else:
        experience_score = 0

    # ---------------------------------
    # 4. Resume Evidence
    # ---------------------------------

    if len(analysis.strengths) >= 4:
        evidence_score = 10

    elif len(analysis.strengths) >= 2:
        evidence_score = 7

    elif len(analysis.strengths) >= 1:
        evidence_score = 4

    else:
        evidence_score = 0

    # ---------------------------------
    # Final Score
    # ---------------------------------

    score = round(
        skill_score
        + keyword_score
        + experience_score
        + evidence_score
    )

    score = max(0, min(score, 100))

    # ---------------------------------
    # Match Level
    # ---------------------------------

    if score >= 90:
        match_level = "Excellent Match"

    elif score >= 75:
        match_level = "Strong Match"

    elif score >= 60:
        match_level = "Moderate Match"

    elif score >= 40:
        match_level = "Weak Match"

    else:
        match_level = "Poor Match"

    return ATSResult(
        overall_score=score,
        match_level=match_level,
        analysis=analysis
    )