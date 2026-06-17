COMPLETE_THRESHOLD = 75
SUMMARY_MIN_LENGTH = 80
SKILLS_MIN_COUNT = 5


def _has_contact_info(cv_profile):
    return all([
        cv_profile.full_name.strip(),
        cv_profile.email.strip(),
        cv_profile.phone.strip(),
        cv_profile.city.strip(),
    ])


def _has_summary(cv_profile):
    return len(cv_profile.summary.strip()) >= SUMMARY_MIN_LENGTH


def _has_work_experience(cv_profile):
    if not cv_profile.pk:
        return False
    for experience in cv_profile.work_experiences.all():
        if experience.bullets.count() >= 2:
            return True
    return False


def _has_education(cv_profile):
    return cv_profile.pk and cv_profile.education_entries.exists()


def _has_skills(cv_profile):
    return cv_profile.pk and cv_profile.skills.count() >= SKILLS_MIN_COUNT


def _has_projects(cv_profile):
    return cv_profile.pk and cv_profile.projects.exists()


def calculate_section_completion(cv_profile):
    return {
        'contact': _has_contact_info(cv_profile),
        'summary': _has_summary(cv_profile),
        'experience': _has_work_experience(cv_profile),
        'education': _has_education(cv_profile),
        'skills': _has_skills(cv_profile),
        'projects': _has_projects(cv_profile),
    }


def compute_completion(cv_profile):
    score = 0
    sections = calculate_section_completion(cv_profile)

    if sections['contact']:
        score += 25
    if sections['summary']:
        score += 10
    if sections['experience']:
        score += 25
    if sections['education']:
        score += 15
    if sections['skills']:
        score += 15
    if sections['projects']:
        score += 10

    score = min(score, 100)
    is_complete = score >= COMPLETE_THRESHOLD
    return score, is_complete
