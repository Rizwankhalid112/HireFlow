"""Structured-output schemas.

These are passed to `messages.parse(output_format=...)`, so the API constrains
generation to them and the SDK hands back a validated instance. That removes the
whole class of "strip the markdown fence, catch JSONDecodeError, handle the case
where Claude returned a string instead of a list" handling the spec's Step 8
sketch carries — none of it is reachable any more.

Every field is required and every default is an empty value rather than None:
structured outputs are strictest and most reliable with a closed, fully-required
schema, and an empty string is easier to render than a null.
"""

from typing import Literal

from pydantic import BaseModel, Field

GapField = Literal['impact', 'scale', 'outcome', 'tech', 'timeframe', 'role']


class GapQuestion(BaseModel):
    """A fact that would strengthen the line, which we do not have.

    This is the entire anti-fabrication mechanism in one object: the model is
    told that when it wants a number it cannot source, it emits one of these
    instead of writing one.
    """

    field: GapField = Field(description='Which kind of fact is missing.')
    question: str = Field(description='A short question to the user, under 12 words.')
    why: str = Field(description='One clause on why this would strengthen the line.')


class TextVariant(BaseModel):
    text: str
    grounded_in: list[str] = Field(
        description='Short quotes from the user input that each claim rests on.',
    )


class BulletSuggestions(BaseModel):
    variants: list[TextVariant]
    gaps: list[GapQuestion]


class SummarySuggestions(BaseModel):
    variants: list[TextVariant]
    gaps: list[GapQuestion]


class ProjectSuggestions(BaseModel):
    """Project points are individually acceptable rather than variants of one
    line — a project usually needs several points, not a choice between three
    phrasings of the same point."""

    points: list[TextVariant]
    gaps: list[GapQuestion]


class SkillCandidate(BaseModel):
    name: str
    # Empty for a role-suggested skill. Populated with the phrase it was drawn
    # from for an evidenced one, which is what lets the UI show its provenance.
    evidence: str


class SkillSuggestions(BaseModel):
    evidenced: list[SkillCandidate] = Field(
        description='Skills demonstrated in text the user actually wrote.',
    )
    suggested_for_role: list[SkillCandidate] = Field(
        description='Skills common for the target role that are NOT on this CV.',
    )


class TitleVariant(BaseModel):
    text: str
    why: str


class TitleSuggestions(BaseModel):
    variants: list[TitleVariant]


# --- CV parse (spec Steps 7-8) ----------------------------------------------
#
# These carry the whole weight of mapping an arbitrary CV onto our models, and
# they do it by construction rather than by cleanup afterwards.
#
# Every constrained field below is a `Literal` holding exactly our model's
# choices. Structured outputs constrain *generation*, so the model cannot emit
# "Permanent" into `employment_type` — those tokens are not available to it. The
# mapping from whatever the CV said onto our vocabulary happens inside the model,
# guided by the prompt, instead of in a lookup table we would extend forever.
#
# `''` is a member of every one of them, and the prompt says so: "not stated" has
# to be expressible, or the model is forced to guess.
#
# Integers use `0` for "not stated" rather than `None`, following the convention
# at the top of this file — a closed, fully-required schema is the most reliable
# shape, and normalisation turns the zeros into nulls or into questions.

EmploymentType = Literal[
    'full_time', 'part_time', 'internship', 'contract', 'freelance', '',
]
LocationType = Literal['onsite', 'remote', 'hybrid', '']
DegreeType = Literal['bs', 'ms', 'phd', 'diploma', 'certificate', 'other', '']
SkillCategory = Literal[
    'Languages', 'Frameworks', 'Databases', 'Tools', 'Concepts', 'Cloud', 'Soft Skills', '',
]
SkillProficiency = Literal['beginner', 'intermediate', 'advanced', 'expert', '']
LanguageProficiency = Literal['native', 'fluent', 'professional', 'basic', '']


class ParsedPersonal(BaseModel):
    full_name: str
    professional_title: str
    email: str
    phone: str
    city: str
    country: str
    linkedin_url: str
    github_url: str
    portfolio_url: str
    summary: str


class ParsedExperience(BaseModel):
    company_name: str
    role_title: str
    employment_type: EmploymentType
    location: str
    location_type: LocationType
    start_month: int = Field(description='1-12, or 0 if the CV does not say.')
    start_year: int = Field(description='Four digits, or 0 if the CV does not say.')
    end_month: int
    end_year: int
    is_current: bool
    bullets: list[str] = Field(
        description='One entry per bullet, verbatim from the CV. Never one joined string.',
    )


class ParsedEducation(BaseModel):
    institution: str
    degree_type: DegreeType
    field_of_study: str
    # Deliberately a string, not a number. CVs write "3.3/4.0", "85%", "First
    # Class Honours" — asking the model for a float means asking it to decide
    # what "First Class" is worth. It reports what it saw; normalisation decides
    # what is storable, which is a rule we can test.
    cgpa: str = Field(description='Exactly as written in the CV, or empty.')
    start_year: int = Field(description='0 if the CV gives only a graduation year.')
    end_year: int
    is_current: bool
    thesis_title: str
    achievements: str


class ParsedSkill(BaseModel):
    name: str
    category: SkillCategory
    proficiency: SkillProficiency


class ParsedProject(BaseModel):
    name: str
    subtitle: str
    description: str
    tech_stack: list[str]
    project_url: str
    start_year: int
    end_year: int
    is_ongoing: bool
    is_professional: bool


class ParsedCertification(BaseModel):
    name: str
    issuing_organization: str
    issue_month: int
    issue_year: int
    expiry_year: int
    credential_url: str


class ParsedLanguage(BaseModel):
    """A *spoken* language. See the prompt and `parse_normalize` — a CV that
    heads its programming languages "Languages" is the collision this field is
    most likely to be wrong about, and it is guarded mechanically."""

    language_name: str
    proficiency: LanguageProficiency


class UnmappedSection(BaseModel):
    """A section of their CV we have nowhere to put.

    Publications, Awards, Volunteering, References, Hobbies, Patents. Silently
    discarding these is the worst thing this feature could do — the user would
    find out by noticing an absence, if ever. Carrying them here turns data loss
    into an informed choice, and doubles as the backlog signal for what to model
    next.
    """

    heading: str = Field(description='The heading as it appeared in their CV.')
    content: str = Field(description='The section text, up to about 500 characters.')


class ParsedCV(BaseModel):
    personal: ParsedPersonal
    work_experience: list[ParsedExperience]
    education: list[ParsedEducation]
    skills: list[ParsedSkill]
    projects: list[ParsedProject]
    certifications: list[ParsedCertification]
    languages: list[ParsedLanguage]
    unmapped_sections: list[UnmappedSection]


# --- Job match: keywords + cover letter ------------------------------------
#
# One call produces all of this, because the cover letter has to be written from
# the same reading of the CV and the job that produced the keyword analysis —
# splitting them would mean paying to send both documents twice and risking two
# different readings of the same pair.
#
# The three keyword buckets are the whole ethical design of the feature. They are
# the Evidenced / Ask-first / Never rungs from the suggestions work, applied to
# job keywords instead of to bullet points:
#
#   matched   — they have it and say so. Nothing to do.
#   reworded  — they have it, in different words. Safe to change, and this is
#               where most of the real value is.
#   missing   — they may not have it. We ASK. We never write it in.


class KeywordMatch(BaseModel):
    keyword: str = Field(description='The term as the job description writes it.')
    evidence: str = Field(description='A short quote from the CV showing they have it.')


class KeywordRewrite(BaseModel):
    """A skill the CV already demonstrates under a different name.

    The highest-value and lowest-risk change available: ATS matching is largely
    literal, so "Postgres" losing to "PostgreSQL" costs real interviews, and
    fixing it invents nothing.
    """

    keyword: str = Field(description="The job description's wording.")
    current_wording: str = Field(description='What the CV says instead.')
    where: str = Field(description='Which part of the CV — role, project, skills.')


class KeywordGap(BaseModel):
    """Something the job asks for that the CV does not show.

    This is a question, never a suggested edit. If the model proposes text here
    it is proposing that the user claim a skill we have no evidence they have.
    """

    keyword: str
    importance: Literal['required', 'preferred']
    question: str = Field(
        description='A short question asking whether they have this. Under 15 words.',
    )


class JobMatchResult(BaseModel):
    job_title: str = Field(description='Read from the job description, or empty.')
    company: str = Field(description='Read from the job description, or empty.')

    # Keyword alignment, 0-100. Explicitly NOT a prediction of being interviewed:
    # no model has the applicant pool, the callback history, or the competition.
    match_score: int = Field(
        description='0-100, how well the CV covers the terms this job asks for.',
    )
    summary: str = Field(description='Two sentences on where the CV stands. Plain.')

    matched: list[KeywordMatch]
    reworded: list[KeywordRewrite]
    missing: list[KeywordGap]

    cover_letter: str = Field(
        description='A complete cover letter, every claim traceable to the CV.',
    )
