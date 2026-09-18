"""Demo CV data used to populate the template gallery.

The gallery shows each template filled with a realistic CV rather than an empty
skeleton, so a user can see how their own content will look before choosing.

Returns the same dict shape as build_cv_context(), so templates cannot tell the
difference and no database row is needed.

Contact details are deliberately placeholders: these thumbnails are shown to
every user, so a real phone number or address here would be published to all of
them. Change SAMPLE_CONTACT if you want different demo values.
"""

import base64
import io

SAMPLE_NAME = 'Muhammad Rizwan-ul-Hassan'
SAMPLE_TITLE = 'Full Stack Web App Developer'
SAMPLE_CONTACT = [
    'name@example.com',
    '+92 3XX XXXXXXX',
    'Lahore, Pakistan',
]
SAMPLE_LINKS = [
    {'label': 'LinkedIn', 'url': 'linkedin.com/in/your-profile'},
]

SAMPLE_SUMMARY = (
    'Results-driven Full Stack Software Engineer with hands-on professional experience '
    'building and scaling web applications using Python and React. Demonstrated ability '
    'to own end-to-end feature delivery, drive significant improvements in code quality '
    'and test coverage, and contribute to complex data engineering initiatives. Proficient '
    'in agile environments with a strong foundation in backend architecture, database '
    'optimization, and automated workflows.'
)

SAMPLE_SKILLS_GROUPED = [
    {
        'category': 'Core Tech',
        'items': [
            'Python (FastAPI)', 'ReactJS', 'JavaScript (ES6+)', 'HTML5', 'CSS3',
            'Celery', 'SQLAlchemy', 'RESTful APIs',
        ],
    },
    {'category': 'Databases', 'items': ['PostgreSQL', 'MySQL', 'Redis']},
    {
        'category': 'Tools & DevOps',
        'items': [
            'Docker', 'Git/GitHub', 'CI/CD Pipelines', 'Linux (Ubuntu)',
            'Postman', 'Firebase', 'VS Code',
        ],
    },
    {
        'category': 'Concepts',
        'items': [
            'OOP', 'DSA', 'DBMS', 'JWT Authentication', 'Microservices',
            'Agile Methodology', 'Automated Testing (Pytest)',
        ],
    },
]

SAMPLE_EXPERIENCES = [
    {
        'company_name': 'INOVAQO Tech Solutions Pvt. Ltd.',
        'role_title': 'Associate Software Engineer',
        'employment_type': 'Full-time',
        'location': 'Lahore, Pakistan',
        'location_type': 'Onsite',
        'date_range': 'October 2025 — Present',
        'bullets': [
            'Delivered end-to-end full-stack features across multiple client-facing products, '
            'working across Python (FastAPI) backend services and ReactJS frontends in a '
            'fast-paced agile environment.',
            'Contributed to platform stability, data engineering pipelines, and real-time '
            'communication systems, consistently meeting delivery milestones and maintaining '
            'high code quality standards.',
        ],
    },
    {
        'company_name': 'INOVAQO Tech Solutions Pvt. Ltd.',
        'role_title': 'Python Developer Intern',
        'employment_type': 'Internship',
        'location': 'Lahore, Pakistan',
        'location_type': 'Onsite',
        'date_range': '2024 (3 months)',
        'bullets': [
            'Implemented backend data validation schemas, database query optimizations, and '
            'error-logging middleware for an internal system.',
            'Built reusable ReactJS components with client-side validation logic and '
            'streamlined staging CI/CD pipeline configurations to accelerate release cycles.',
        ],
    },
]

SAMPLE_PROJECTS = [
    {
        'name': 'FieldFlow360',
        'subtitle': 'Field Operations Management Platform',
        'description': (
            'Engineered a synchronized two-way communication module for real-time note and '
            'file tracking, and built geospatial data ingestion pipelines processing '
            'large-scale LiDAR datasets via STAC APIs. Drove a testing initiative '
            'implementing 180+ automated test cases to raise API module coverage from 54% '
            'to 93%.'
        ),
        'tech_stack': ['Python', 'FastAPI', 'Celery', 'Redis', 'PostgreSQL'],
        'url': '',
        'date_range': '2025 — 2026',
    },
    {
        'name': 'Internal HRMS',
        'subtitle': 'Human Resource Management System',
        'description': (
            'Architected backend validation schemas and optimized database query performance '
            'for faster employee record retrieval. Developed modular, reusable React '
            'components with asynchronous API communication to maximize responsiveness.'
        ),
        'tech_stack': ['ReactJS', 'FastAPI', 'PostgreSQL'],
        'url': '',
        'date_range': '2026',
    },
]

SAMPLE_EDUCATION = [
    {
        'institution': 'The University of Faisalabad',
        'degree': 'BS in Software Engineering',
        'date_range': 'November 2021 — July 2025',
        'cgpa': '3.30/4.0',
        'thesis_title': (
            'AI-driven diabetes and retinopathy screening application leveraging machine '
            'learning for non-invasive early detection.'
        ),
        'achievements': '',
    },
]

SAMPLE_LANGUAGES = [
    {'name': 'Urdu', 'proficiency': 'Native'},
    {'name': 'English', 'proficiency': 'Professional'},
]

SAMPLE_CERTIFICATIONS = []


def _placeholder_photo():
    """Neutral avatar for the two photo templates, as a data URI.

    Generated rather than shipped as a file so there is no asset to keep in sync,
    and WeasyPrint reads data URIs directly.
    """
    from PIL import Image, ImageDraw

    size = 320
    image = Image.new('RGB', (size, size), (79, 70, 229))
    draw = ImageDraw.Draw(image)
    # A simple head-and-shoulders glyph reads as a placeholder at thumbnail size
    # without needing a font metric we cannot guarantee.
    draw.ellipse((110, 70, 210, 170), fill=(224, 231, 255))
    draw.ellipse((70, 190, 250, 400), fill=(224, 231, 255))

    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    encoded = base64.b64encode(buffer.getvalue()).decode('ascii')
    return f'data:image/png;base64,{encoded}'


def sample_context(template=None):
    """Context for rendering `template` with the demo CV."""
    template = template or {}

    flat_skills = [item for group in SAMPLE_SKILLS_GROUPED for item in group['items']]

    return {
        'full_name': SAMPLE_NAME,
        'professional_title': SAMPLE_TITLE,
        'summary': SAMPLE_SUMMARY,
        'contact_lines': list(SAMPLE_CONTACT),
        'links': [dict(link) for link in SAMPLE_LINKS],
        'photo_url': _placeholder_photo() if template.get('photo') else '',
        'experiences': [dict(item) for item in SAMPLE_EXPERIENCES],
        'education': [dict(item) for item in SAMPLE_EDUCATION],
        'skills': flat_skills,
        'skills_grouped': [dict(group) for group in SAMPLE_SKILLS_GROUPED],
        'projects': [dict(item) for item in SAMPLE_PROJECTS],
        'certifications': list(SAMPLE_CERTIFICATIONS),
        'languages': [dict(item) for item in SAMPLE_LANGUAGES],
        'template': template,
        'is_sample': True,
    }
