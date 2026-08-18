"""Template registry for CV rendering.

This is the allowlist. `template_id` arrives from the client, so a template file
is ALWAYS looked up through this dict — never built by interpolating user input
into a path, which would let a crafted id steer render_to_string() elsewhere.
"""

DEFAULT_TEMPLATE_ID = 'minimal'

CV_TEMPLATES = {
    'minimal': {
        'name': 'Minimal',
        'file': 'cv_templates/minimal.html',
        'description': 'Clean and spacious. Best for early career.',
        'columns': 1,
        'ats_safe': True,
        'photo': False,
        'max_pages': 1,
    },
    'classic': {
        'name': 'Classic',
        'file': 'cv_templates/classic.html',
        'description': 'Traditional serif layout for conservative industries.',
        'columns': 1,
        'ats_safe': True,
        'photo': False,
        'max_pages': 2,
    },
    'technical': {
        'name': 'Technical',
        'file': 'cv_templates/technical.html',
        'description': 'Skills grid up top. Built for engineers with long stacks.',
        'columns': 1,
        'ats_safe': True,
        'photo': False,
        'max_pages': 2,
    },
    'compact': {
        'name': 'Compact',
        'file': 'cv_templates/compact.html',
        'description': 'Tight spacing to fit long careers onto one page.',
        'columns': 1,
        'ats_safe': True,
        'photo': False,
        'max_pages': 1,
    },
    'modern': {
        'name': 'Modern',
        'file': 'cv_templates/modern.html',
        'description': 'Two-column sidebar with a photo. Not ATS-safe.',
        'columns': 2,
        'ats_safe': False,
        'photo': True,
        'max_pages': 2,
    },
    'executive': {
        'name': 'Executive',
        'file': 'cv_templates/executive.html',
        'description': 'Photo in a header band, single column so it stays ATS-safe.',
        'columns': 1,
        'ats_safe': True,
        'photo': True,
        'max_pages': 2,
    },
}


def get_template(template_id):
    """Resolve a client-supplied id to its registry entry, or None."""
    if not template_id:
        return None
    return CV_TEMPLATES.get(template_id)


def resolve_template(template_id):
    """Registry entry for `template_id`, falling back to the default."""
    return get_template(template_id) or CV_TEMPLATES[DEFAULT_TEMPLATE_ID]


def template_choices():
    """`choices` for the model field, so admin and validation agree."""
    return [(key, value['name']) for key, value in CV_TEMPLATES.items()]


def public_registry():
    """Registry as the frontend consumes it — drives the picker and fit banner."""
    return [
        {
            'id': key,
            'name': value['name'],
            'description': value['description'],
            'columns': value['columns'],
            'ats_safe': value['ats_safe'],
            'photo': value['photo'],
            'max_pages': value['max_pages'],
        }
        for key, value in CV_TEMPLATES.items()
    ]
