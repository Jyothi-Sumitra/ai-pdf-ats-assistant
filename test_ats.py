from src.chatbot import get_llm
from src.ats.parser import extract_pdf_text
from src.ats.analyzer import analyze_resume
from src.ats.scorer import calculate_score


llm = get_llm()

resume = extract_pdf_text(
    "data/ats/resume.pdf"
)

job_description = extract_pdf_text(
    "data/ats/job_description.pdf"
)

analysis = analyze_resume(
    resume_text=resume,
    job_description=job_description,
    llm=llm
)

result = calculate_score(
    analysis=analysis,
    resume_text=resume,
    job_description=job_description
)

print("\nATS SCORE:")
print(result.overall_score)

print("\nMATCH LEVEL:")
print(result.match_level)

print("\nMATCHING SKILLS:")
for skill in result.analysis.matching_skills:
    print("-", skill)

print("\nMISSING SKILLS:")
for skill in result.analysis.missing_skills:
    print("-", skill)

print("\nMATCHING KEYWORDS:")
for keyword in result.analysis.matching_keywords:
    print("-", keyword)

print("\nMISSING KEYWORDS:")
for keyword in result.analysis.missing_keywords:
    print("-", keyword)

print("\nEXPERIENCE MATCH:")
print(result.analysis.experience_match)

print("\nSTRENGTHS:")
for strength in result.analysis.strengths:
    print("-", strength)

print("\nRECOMMENDATIONS:")
for recommendation in result.analysis.recommendations:
    print("-", recommendation)