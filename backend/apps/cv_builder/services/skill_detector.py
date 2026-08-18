from django.core.cache import cache

from apps.cv_builder.models import SkillCanonical

CACHE_KEY = 'cv_builder:canonical_skill_names'
CACHE_TIMEOUT = 3600


def _load_skill_names():
    names = set()
    for canonical_name, aliases in SkillCanonical.objects.values_list('canonical_name', 'aliases'):
        names.add(canonical_name)
        for alias in aliases or []:
            names.add(alias)
    return sorted(names, key=len, reverse=True)


def get_all_skill_names():
    cached = cache.get(CACHE_KEY)
    if cached is not None:
        return cached
    names = _load_skill_names()
    cache.set(CACHE_KEY, names, CACHE_TIMEOUT)
    return names


def extract_skills_from_bullet(text: str) -> list[str]:
    found = []
    text_lower = text.lower()
    for skill_name in get_all_skill_names():
        if skill_name.lower() in text_lower and skill_name not in found:
            found.append(skill_name)
    return found
