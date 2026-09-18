
HIREFLOW
CV Builder Module — Complete Implementation Guide

Step-by-Step Build Plan with Every Edge Case Handled
Muhammad Rizwan-ul-Hassan  •  Module 8 of HireFlow

Total Steps
10 steps from Django setup to frontend complete
Build Order
Backend first, then Celery tasks, then React frontend
R&D Basis
Complete edge case analysis from previous sessions
AI Integration
Claude API for CV parsing — added in Step 9
Testing
Pytest coverage targets defined per step
Deployment
Docker-ready from Step 1

Implementation Steps — Overview

Build in exactly this order. Do not start Step 2 until Step 1 is working and tested. Every step has acceptance criteria. When those are met, move forward.

Step
Title
What It Delivers
Step 1
Django App Setup & Database Models
Foundation — every table, every field, every relationship
Step 2
Resume Lifecycle & Ownership Layer
Creation, draft logic, completion scoring, permissions
Step 3
Contact Info & Summary API
Simplest section — sets the pattern for all others
Step 4
Work Experience & Bullets API
Core section — separate bullet table, metric extraction
Step 5
Education, Skills & Canonical Table
Skills normalisation, fixed categories, proficiency
Step 6
Projects, Certifications & Languages API
Optional sections, reorder endpoints
Step 7
File Upload & Text Extraction Pipeline
PDF + DOCX parsing, scanned PDF detection, Celery async
Step 8
AI Parse with Claude API
Prompt design, JSON validation, diff UI data, partial save
Step 9
PDF Export Pipeline
WeasyPrint, skip-regen logic, template contract
Step 10
React Frontend — CV Builder UI
RTK Query, autosave hook, step navigator, diff modal

STEP 1
Django App Setup & Database Models
Every table, every field, every constraint — built once, built right

1.1  Create the Django App
Inside backend/apps/ create a new app called cv_builder. This is a standalone Django app. It knows nothing about the applications module. Keep it isolated.
python manage.py startapp cv_builder
# Move it into backend/apps/cv_builder/
# Add 'apps.cv_builder' to INSTALLED_APPS in settings/base.py

1.2  Model File Structure
Do not put all models in one models.py file. Split them. Each model gets its own file inside a models/ folder. This keeps the code navigable as the module grows.
apps/cv_builder/
├── models/
│   ├── __init__.py          ← import all models here
│   ├── cv_profile.py        ← Table 1
│   ├── work_experience.py   ← Table 2 + 3
│   ├── education.py         ← Table 4
│   ├── skill.py             ← Table 5 + canonical
│   ├── project.py           ← Table 6
│   ├── certification.py     ← Table 7
│   ├── language.py          ← Table 8
│   └── upload_log.py        ← Table 9
├── serializers/
├── views/
├── services/
├── tasks.py
├── permissions.py
└── urls.py

1.3  All Database Tables
Table 1 — CVProfile (one per user)
Field
Type
Notes
id
UUIDField PK
Use UUID not integer — harder to enumerate
user
OneToOneField → User
OneToOne enforced at DB level
full_name
CharField(100)
Default empty string not null
professional_title
CharField(150)
e.g. Full Stack Web App Developer
email
EmailField
Pre-filled from auth user on creation
phone
CharField(30)
Include country code
city
CharField(100)

country
CharField(100)

linkedin_url
URLField blank=True
Validated as URL
github_url
URLField blank=True

portfolio_url
URLField blank=True

summary
TextField blank=True
Base summary — AI tailors per job in Module 10
template_id
CharField(50) null
null = no template chosen yet
is_complete
BooleanField False
Computed on every save — never set manually
completion_score
IntegerField 0
0-100 — shown as progress bar
content_updated_at
DateTimeField auto
Updated on ANY section save — used for PDF regen check
pdf_file
FileField null
Path to last generated PDF
pdf_generated_at
DateTimeField null
Compared to content_updated_at before regen
reminder_sent
BooleanField False
True after 23-day reminder email sent
created_at
DateTimeField auto

updated_at
DateTimeField auto


Table 2 — WorkExperience
Field
Type
Notes
id
UUIDField PK

cv
FK → CVProfile
on_delete=CASCADE
company_name
CharField(200)

role_title
CharField(200)

employment_type
CharField(50)
Choices: Full-time/Part-time/Internship/Contract/Freelance
location
CharField(200)
City, Country
location_type
CharField(20)
Choices: Onsite/Remote/Hybrid
start_month
IntegerField null
1-12, nullable for year-only dates
start_year
IntegerField
Required
end_month
IntegerField null
null if is_current=True
end_year
IntegerField null
null if is_current=True
is_current
BooleanField
If True end_month/end_year must be null — validated in serializer
order
IntegerField 0
For drag-to-reorder — lower = appears first on CV
created_at
DateTimeField auto


Table 3 — WorkBullet (separate table — critical decision)
Bullets are NOT stored as a text array on WorkExperience. Each bullet is its own row. Module 9 (AI match) and Module 10 (AI tailoring) need to read and rewrite individual bullets. A JSON array makes that impossible cleanly.
Field
Type
Notes
id
UUIDField PK

experience
FK → WorkExperience
on_delete=CASCADE
text
TextField
The actual bullet point text
impact_metric
CharField null
Extracted by regex on save: '180+ tests', '54% to 93%'
skills_demonstrated
JSONField []
Auto-detected tech keywords in bullet text
order
IntegerField 0
Position within this experience
created_at
DateTimeField auto


Table 4 — Education
Field
Type
Notes
id
UUIDField PK

cv
FK → CVProfile
on_delete=CASCADE
institution
CharField(300)

degree_type
CharField(50)
Choices: BS/MS/PhD/Diploma/Certificate/Other
field_of_study
CharField(200)
Software Engineering, Computer Science etc
cgpa
DecimalField(3,2) null
3.30 — stored with full precision
cgpa_scale
DecimalField(3,1) null
4.0 — the out-of value
start_year
IntegerField

end_year
IntegerField null
null if is_current=True
is_current
BooleanField False

thesis_title
TextField blank

achievements
TextField blank
Dean's list, scholarships etc
order
IntegerField 0


Table 5 — SkillCanonical (normalization table)
This table prevents 'ReactJS' vs 'React' vs 'React.js' from being treated as 3 different skills. Pre-populate this table with 200+ common tech skills before launch.
Field
Type
Notes
id
UUIDField PK

canonical_name
CharField(100)
The official spelling: 'PostgreSQL', 'FastAPI', 'React'
aliases
JSONField []
['Postgres','postgres','psql','PostgreSQL 16']
category
CharField(50)
Languages/Frameworks/Databases/Tools/Concepts/Soft Skills
logo_url
URLField null
Optional — for skill badge display
is_popular
BooleanField
True = show in autocomplete suggestions by default

Table 6 — CVSkill
Field
Type
Notes
id
UUIDField PK

cv
FK → CVProfile
on_delete=CASCADE
canonical
FK → SkillCanonical null
null if user typed a freetext skill
name
CharField(100)
Always stored — either canonical_name or freetext
category
CharField(50)
Copied from canonical or user-selected
proficiency
CharField(20)
Choices: Beginner/Intermediate/Advanced/Expert
years_of_exp
DecimalField null
Optional — 1.5 means 1 year 6 months
is_featured
BooleanField
Show prominently — used for CV top skills section
is_verified
BooleanField
True if matched to canonical, False if freetext
order
IntegerField 0


Tables 7, 8, 9 — Project, Certification, Language
Table
Key Fields
Notes
CVProject
name, subtitle, description, tech_stack (JSON), project_url, start/end year, is_ongoing, is_professional, order
is_professional=True means work project not personal
CVCertification
name, issuing_organization, issue_month/year, expiry_year, credential_url, order
expiry_year null = does not expire
CVLanguage
language_name, proficiency (Native/Fluent/Professional/Basic), order
Simple table — no FK to canonical needed

Table 10 — CVUploadLog
Field
Type
Notes
id
UUIDField PK

cv
FK → CVProfile
on_delete=CASCADE
original_filename
CharField(300)
Original name user uploaded
file_type
CharField(10)
pdf / docx
file_path
CharField(500)
media/cv_uploads/{user_id}/{ts}_{filename}
raw_extracted_text
TextField blank
What pdfplumber/docx extracted — stored for debugging
ai_parsed_json
JSONField null
Raw response from Claude API
parse_status
CharField(20)
pending/extracting/parsing/success/partial/failed/scanned
fields_extracted
IntegerField 0
How many form fields got populated
fields_total
IntegerField 0
Total fields in the schema
error_message
TextField blank
Human-readable error shown to user if failed
uploaded_at
DateTimeField auto

extracted_at
DateTimeField null
When text extraction finished
parsed_at
DateTimeField null
When AI parsing finished

⚠  Edge Cases — Database Setup
Migration order wrong
Always run makemigrations after ALL models are written. Never run it model-by-model or circular FK errors appear.
UUID vs Integer PK
Use UUIDField(default=uuid.uuid4) on every model. Prevents ID enumeration attacks on the API.
Cascade delete testing
In tests, delete a CVProfile and verify all child rows are gone. If any orphan remains, the on_delete is wrong.
skill canonical prepopulate
Write a management command: python manage.py seed_skills — loads 200 canonical skills from a JSON fixture file before any user touches the system.
Step 1 — Acceptance Criteria
    • python manage.py migrate runs with zero errors
    • All 10 tables visible in Django admin
    • Creating a CVProfile via Django shell and then deleting it cascades all child rows
    • python manage.py seed_skills loads canonical skills without errors
    • UUIDs are generated correctly on every model

STEP 2
Resume Lifecycle & Ownership Layer
Creation moment, draft limits, completion scoring, security permissions

2.1  The Creation Moment
When user clicks 'Create CV' on the dashboard, a POST request fires immediately. The backend creates a CVProfile shell with only the user FK set and everything else empty. The frontend then navigates to the builder with the returned UUID. This is server-first — never optimistic.
POST /api/cv/profile/
Response 201: { id: 'uuid', completion_score: 0, is_complete: false }
 
# Django view logic:
# 1. Check user does not already have a CVProfile
# 2. If exists → return existing profile (idempotent)
# 3. If not → create new shell
# 4. Pre-fill email from request.user.email
2.2  Draft Limit Enforcement
A user cannot create a new CV if they already have one (OneToOne relationship enforces this at DB level). Unlike a resume-builder app where users create many resumes, HireFlow stores one master profile per user. The AI generates tailored versions per job application on demand.
This is a key HireFlow design decision. One CV profile. AI tailoring happens at application time in Module 10. Not multiple stored CVs.
2.3  Completion Scoring Service
Every time any section is saved, the completion score is recalculated. This lives in apps/cv_builder/services/completeness.py — not in the model, not in the view.
Section
Points
Condition
Personal Info
25 pts
full_name + email + phone + city all filled (5pts each + 5 bonus)
Summary
10 pts
summary text is at least 80 characters
Work Experience
25 pts
At least 1 experience with at least 2 bullets
Education
15 pts
At least 1 education entry
Skills
15 pts
At least 5 skills added
Projects
10 pts
At least 1 project (optional — bonus points)
is_complete = True when score >= 75. This is the threshold that stops the 30-day deletion clock from running.
2.4  IsOwner Permission Class
Every view in this module uses this permission. Written once in permissions.py, imported everywhere.
# permissions.py
class IsCVOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        # Works for any model that has a .cv FK
        if hasattr(obj, 'cv'):
            return obj.cv.user == request.user
        # Works for CVProfile directly
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return False
 
# Every ViewSet's get_queryset must filter by user:
def get_queryset(self):
    return WorkExperience.objects.filter(
        cv__user=self.request.user
    ).order_by('order')
2.5  content_updated_at Signal
Every time any child section (WorkExperience, Education, Skill etc) is saved, the parent CVProfile's content_updated_at must be updated. Use a Django post_save signal in each model's file.
from django.db.models.signals import post_save
from django.utils import timezone
 
@receiver(post_save, sender=WorkExperience)
def update_cv_timestamp(sender, instance, **kwargs):
    CVProfile.objects.filter(id=instance.cv_id).update(
        content_updated_at=timezone.now()
    )
# Same signal on: WorkBullet, Education, CVSkill, CVProject, CVCertification, CVLanguage
⚠  Edge Cases — Lifecycle
User closes browser during creation POST
Server-first creation means nothing is created. User returns to dashboard, sees no broken CV. They click Create CV again — works normally.
Concurrent session — two tabs open
Second tab's POST returns the existing CVProfile (idempotent). Frontend receives the same UUID and shows the same builder state.
content_updated_at not updating
If signal is missing on any child model, pdf_generated_at check will skip regeneration even when content changed. Write a test: save a bullet, check content_updated_at changed.
completion_score drift
Never cache completion score. Recalculate it fresh on every section save. It is cheap — a few COUNT queries.
Step 2 — Acceptance Criteria
    • POST /api/cv/profile/ creates a CVProfile and returns UUID
    • Second POST for same user returns existing profile, not a new one
    • Deleting a WorkExperience updates content_updated_at on CVProfile
    • completion_score is 0 on fresh creation and increases correctly as sections are filled
    • IsCVOwner blocks user A from accessing user B's work experience

STEP 3
Contact Info & Summary API
The simplest section — establishes the pattern every other section follows

Contact info and summary are stored directly on CVProfile. No child table. This makes them the simplest section — perfect for establishing the API pattern that every other section will follow.
3.1  Serializer Design
Use two separate serializers — one for reading (GET) and one for writing (PUT/PATCH). The read serializer includes computed fields like completion_score and is_complete. The write serializer validates only the fields the user can change.
class CVProfileReadSerializer(serializers.ModelSerializer):
    completion_score = serializers.IntegerField(read_only=True)
    is_complete = serializers.BooleanField(read_only=True)
    section_completion = serializers.SerializerMethodField()
 
    def get_section_completion(self, obj):
        # Returns dict: {contact: True, experience: False, ...}
        return calculate_section_completion(obj)
 
class CVProfileWriteSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ['full_name','professional_title','email','phone',
                  'city','country','linkedin_url','github_url',
                  'portfolio_url','summary','template_id']
 
    def validate_linkedin_url(self, value):
        if value and 'linkedin.com' not in value:
            raise ValidationError('Must be a LinkedIn URL')
        return value
3.2  Endpoints
GET /api/cv/profile/
Returns full CVProfile including section_completion breakdown
PUT /api/cv/profile/
Update all personal info fields at once
PATCH /api/cv/profile/
Partial update — used by autosave (only changed fields sent)
GET /api/cv/profile/completion/
Returns just the completion breakdown — used for progress bar polling
⚠  Edge Cases — Contact & Summary
User clears their email field
email on CVProfile can be blank — it is display email not auth email. Validate: if blank, warn but do not block save.
LinkedIn URL without https://
Normalise on save: if value starts with 'linkedin.com' prepend 'https://'
Summary under 80 chars
Do not block save. Show warning: 'Short summary may reduce match accuracy in Module 9'. This is a soft warning not a hard error.
Phone number format
Store exactly what user types. Do not enforce format — international numbers have many valid formats.
Step 3 — Acceptance Criteria
    • GET /api/cv/profile/ returns all fields including section_completion dict
    • PATCH with only {summary: 'text'} updates only summary, leaves all other fields unchanged
    • completion_score increases after filling personal info fields
    • LinkedIn URL without https:// is normalised on save
    • User cannot read another user's CVProfile — 403 returned

STEP 4
Work Experience & Bullets API
The core section — nested bullets, metric extraction, reorder endpoint

4.1  Nested Structure
Work experience has two levels: the experience row and its bullet rows. The API handles both. When creating an experience, no bullets exist yet. Bullets are added separately via a nested endpoint.
4.2  Metric Extraction Service
Every time a bullet is saved (created or updated), the backend runs a regex extraction to find quantifiable achievements. This runs in services/metric_extractor.py — synchronously, no Celery needed, it is fast.
METRIC_PATTERNS = [
    r'\d+\+?\s*(?:tests?|cases?|tickets?)',   # 180+ test cases
    r'\d+%\s*to\s*\d+%',                    # 54% to 93%
    r'reduced?\s+\w+\s+by\s+\d+%',         # reduced latency by 40%
    r'\$[\d,]+(?:k|K|M)?',                    # $20,000 or $20k
    r'\d+x\s+(?:faster|improvement|reduction)', # 3x faster
    r'\d+\+?\s*(?:users?|clients?|companies)', # 50+ clients
    r'\d+\+?\s*(?:engineers?|developers?)',   # 10+ engineers
]
 
def extract_metric(text: str) -> str | None:
    for pattern in METRIC_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group()
    return None
4.3  Skills Detection in Bullets
When a bullet is saved, also scan the text for known tech keywords from the SkillCanonical table. Store found skills in skills_demonstrated JSONField. This data feeds Module 9's match scoring later.
def extract_skills_from_bullet(text: str) -> list[str]:
    # Load canonical names + aliases into memory (cache this)
    canonical_skills = get_all_skill_names()  # from cache/DB
    found = []
    text_lower = text.lower()
    for skill_name in canonical_skills:
        if skill_name.lower() in text_lower:
            found.append(skill_name)
    return found
4.4  Reorder Endpoint
User drags experiences to change their order on the CV. A single PATCH call sends the new order array. The backend updates all affected rows in one transaction.
PATCH /api/cv/work-experience/reorder/
Body: { ordered_ids: ['uuid-1', 'uuid-4', 'uuid-2'] }
 
# Backend logic:
with transaction.atomic():
    for index, exp_id in enumerate(ordered_ids):
        WorkExperience.objects.filter(
            id=exp_id,
            cv__user=request.user  # ownership check on every ID
        ).update(order=index)
4.5  All Endpoints
GET /api/cv/work-experience/
List all — ordered by 'order' field
POST /api/cv/work-experience/
Create new experience (no bullets yet)
PUT /api/cv/work-experience/{id}/
Update experience details
DELETE /api/cv/work-experience/{id}/
Delete experience + all its bullets (CASCADE)
PATCH /api/cv/work-experience/reorder/
Update order of all experiences
GET /api/cv/work-experience/{id}/bullets/
List bullets for one experience
POST /api/cv/work-experience/{id}/bullets/
Add a bullet — runs metric + skill extraction
PUT /api/cv/work-experience/{id}/bullets/{bid}/
Edit a bullet — re-runs extraction
DELETE /api/cv/work-experience/{id}/bullets/{bid}/
Delete one bullet
PATCH /api/cv/work-experience/{id}/bullets/reorder/
Reorder bullets within one experience
⚠  Edge Cases — Work Experience & Bullets
is_current=True but end_year provided
Serializer validation: if is_current is True, set end_month=None and end_year=None automatically. Do not raise an error — silently correct it.
Deleting experience with bullets
CASCADE on FK handles this at DB level. But also check: does deleting an experience update content_updated_at? Yes — the post_delete signal must fire too, not just post_save.
Reorder with invalid UUID
Filter each ID through cv__user=request.user. If any ID fails the ownership check, reject the entire reorder with 400. Never partial-reorder.
Empty bullet text
Minimum 10 characters. Blank bullets add nothing to the CV and confuse the AI parser in Module 9.
Bullet with no detectable metric
Fine — impact_metric stays null. Not every bullet has a number. Never fabricate a metric.
Skill extraction false positive
'Python' detected in 'Monty Python joke in my notes'
Step 4 — Acceptance Criteria
    • Creating an experience and then adding 3 bullets returns all 3 with order 0, 1, 2
    • Saving a bullet with '180+ automated tests' populates impact_metric correctly
    • Reorder endpoint updates order fields in one DB transaction
    • Deleting an experience with 5 bullets deletes all 6 rows (1 + 5)
    • is_current=True with end_year provided auto-clears end_year in the response
    • content_updated_at on CVProfile changes after every bullet save

STEP 5
Education, Skills & Canonical Table
Fixed categories, skill normalisation, proficiency, bulk add

5.1  Education API
Education follows the same pattern as Work Experience but without bullets. Simpler. The only special logic is CGPA validation.
def validate_cgpa(self, value):
    cgpa_scale = self.initial_data.get('cgpa_scale', 4.0)
    if value and float(value) > float(cgpa_scale):
        raise ValidationError('CGPA cannot exceed the scale value')
    return value
5.2  Skills — The Canonical Flow
When a user types a skill name, the frontend sends it to a search endpoint first. The backend searches SkillCanonical by canonical_name and aliases. If found, the frontend shows the canonical name as a suggestion. If user selects it, the POST includes the canonical_id. If user ignores suggestions and submits their own text, canonical_id is null and is_verified=False.
# Search endpoint — used by frontend autocomplete
GET /api/cv/skills/search/?q=postgres
Response: [
  { id: 'uuid', canonical_name: 'PostgreSQL', category: 'Databases', is_popular: true }
]
 
# Add skill with canonical match
POST /api/cv/skills/
Body: { canonical_id: 'uuid', proficiency: 'Advanced' }
# Backend fills name + category from canonical automatically
 
# Add freetext skill (no canonical match)
POST /api/cv/skills/
Body: { name: 'My Custom Tool', category: 'Tools', proficiency: 'Intermediate' }
# is_verified = False stored
5.3  Bulk Add Skills
After CV upload and parse, the system needs to add 15 skills at once. A bulk endpoint prevents 15 individual HTTP requests.
POST /api/cv/skills/bulk-add/
Body: { skills: [
  { name: 'Python', canonical_id: 'uuid', proficiency: 'Advanced' },
  { name: 'FastAPI', canonical_id: 'uuid', proficiency: 'Advanced' },
  ...
] }
 
# Backend: use get_or_create per skill to prevent duplicates
# If skill with same name already exists for this CV → skip it
# Return: { added: 12, skipped: 3 }
⚠  Edge Cases — Skills
Duplicate skill submission
User adds 'Python' twice. Use get_or_create with (cv, canonical) or (cv, name) as unique constraint. Second add returns the existing skill, not a 400 error.
User changes proficiency after bulk add
Standard PUT /api/cv/skills/{id}/ — no special logic needed.
Category mismatch — user puts 'Python' in 'Databases'
If canonical_id is provided, always use the canonical category. Ignore user-provided category for verified skills. For freetext skills, accept whatever category they provide.
Canonical table empty on first run
The seed_skills management command from Step 1 must run before any user can search skills. Add a health check that verifies SkillCanonical has rows before the app starts.
Step 5 — Acceptance Criteria
    • GET /api/cv/skills/search/?q=react returns PostgreSQL canonical with aliases
    • Adding a skill via canonical_id auto-fills name and category from canonical
    • Bulk add of 15 skills where 3 already exist returns {added: 12, skipped: 3}
    • CGPA of 3.5 with scale 4.0 saves correctly — CGPA of 5.0 with scale 4.0 returns 400
    • Duplicate skill submission returns existing skill not a new row

STEP 6
Projects, Certifications & Languages API
Optional sections with reorder, tech stack as JSON, retention cleanup tasks

These three sections follow identical patterns to what you built in Steps 4 and 5. The main new concept here is the Celery Beat cleanup tasks for draft retention.
6.1  Projects — Tech Stack as JSON
tech_stack is a JSONField containing a list of skill names. On save, validate that it is a list of strings. Maximum 10 items — more than that is noise on a CV.
def validate_tech_stack(self, value):
    if not isinstance(value, list):
        raise ValidationError('tech_stack must be a list')
    if len(value) > 10:
        raise ValidationError('Maximum 10 technologies per project')
    if not all(isinstance(v, str) for v in value):
        raise ValidationError('All tech_stack items must be strings')
    return value
6.2  Retention Cleanup Celery Tasks
Now that all sections exist, implement the three Celery Beat tasks that manage draft retention. These go in tasks.py.
Task
Schedule
Logic
send_draft_reminder()
Daily 9:00 AM
Find CVProfiles where is_complete=False AND content_updated_at is between 23 and 25 days ago AND reminder_sent=False. Send email. Set reminder_sent=True.
delete_stale_drafts()
Daily 2:00 AM
Find CVProfiles where is_complete=False AND content_updated_at > 30 days ago. Delete PDF file from disk first. Then delete the CVProfile row — CASCADE handles children.
delete_orphaned_files()
Sunday 3:00 AM
Scan media/cv_uploads/ folder. For each file, check if a CVUploadLog row exists. If no matching row → delete the file.
⚠  Edge Cases — Cleanup Tasks
delete_stale_drafts runs and file deletion fails
Wrap file deletion in try/except. If it fails, log the error but still delete the DB row. Orphaned files will be caught by delete_orphaned_files on Sunday.
User is actively editing when delete_stale_drafts runs
The task checks content_updated_at > 30 days. If user is editing right now, content_updated_at just updated to now. The task will skip this CV. Safe.
Celery Beat not running
Add a monitoring check: if delete_stale_drafts has not run in 48 hours, send an alert email to admin. Use django-health-check or a simple last_run tracking field.
Step 6 — Acceptance Criteria
    • All three optional sections have working CRUD and reorder endpoints
    • tech_stack with 11 items returns 400 validation error
    • send_draft_reminder task can be triggered manually and sends an email
    • delete_stale_drafts task deletes the PDF file before the DB row
    • delete_orphaned_files cleans up a manually orphaned test file

STEP 7
File Upload & Text Extraction Pipeline
PDF and DOCX parsing, scanned PDF detection, async Celery flow, status polling

7.1  Upload Endpoint
The upload endpoint does three things synchronously: validate the file, save it to disk, create the CVUploadLog row, then immediately trigger the Celery task and return. The HTTP response comes back in under 200ms regardless of how long parsing takes.
POST /api/cv/upload/
Content-Type: multipart/form-data
Body: { file: <binary> }
 
Sync steps (in the HTTP request):
  1. Validate file type (PDF or DOCX only)
  2. Validate file size (max 5MB)
  3. Validate file is not empty (size > 0)
  4. Save file to media/cv_uploads/{user_id}/{timestamp}_{safe_filename}
  5. Verify saved file size matches Content-Length header
  6. Create CVUploadLog with parse_status='pending'
  7. Fire Celery task: extract_and_parse_cv.delay(log_id)
  8. Return 202: { log_id: 'uuid', status: 'pending' }
7.2  File Safety
ALLOWED_MIME_TYPES = {
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
}
MAX_SIZE = 5 * 1024 * 1024  # 5MB
 
# Sanitise filename — prevent path traversal
from django.utils.text import get_valid_filename
safe_name = get_valid_filename(file.name)[:100]
file_path = f'cv_uploads/{user.id}/{timestamp}_{safe_name}'
7.3  Celery Task — Two Stages
The Celery task is split into two chained sub-tasks so each stage can fail independently and the parse_status reflects exactly where the failure happened.
# Stage 1: Text extraction
@shared_task
def extract_text_from_cv(log_id):
    log = CVUploadLog.objects.get(id=log_id)
    log.parse_status = 'extracting'
    log.save()
 
    if log.file_type == 'pdf':
        text = extract_pdf(log.file_path)
    elif log.file_type == 'docx':
        text = extract_docx(log.file_path)
 
    # Scanned PDF detection
    if len(text.strip()) < 100:
        log.parse_status = 'scanned'
        log.error_message = 'Scanned image PDF detected. Please upload a text-based PDF or fill manually.'
        log.save()
        return  # Stop here — do not call Claude API with empty text
 
    log.raw_extracted_text = text
    log.extracted_at = timezone.now()
    log.save()
    send_to_ai_parser.delay(log_id)  # chain to stage 2
7.4  PDF Extraction (pdfplumber)
import pdfplumber
 
def extract_pdf(file_path: str) -> str:
    full_text = []
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text.append(text)
    except Exception as e:
        raise ExtractionError(f'PDF extraction failed: {e}')
    return '\n'.join(full_text).strip()
7.5  DOCX Extraction (python-docx with table support)
from docx import Document
 
def extract_docx(file_path: str) -> str:
    blocks = []
    try:
        doc = Document(file_path)
        # Paragraphs
        for para in doc.paragraphs:
            if para.text.strip():
                blocks.append(para.text.strip())
        # Table cells (critical for column-layout CVs)
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        blocks.append(cell.text.strip())
    except Exception as e:
        raise ExtractionError(f'DOCX extraction failed: {e}')
    return '\n'.join(blocks).strip()
7.6  Status Polling Endpoint
GET /api/cv/upload/{log_id}/status/
Response: {
    status: 'pending|extracting|parsing|success|partial|failed|scanned',
    fields_extracted: 14,
    fields_total: 20,
    error_message: null
}
 
# Frontend polls this every 2 seconds until status is terminal
# Terminal statuses: success, partial, failed, scanned
⚠  Edge Cases — Upload Pipeline
Upload interrupted at 60%
After saving, verify file size matches Content-Length. If mismatch: delete partial file, return 400 'Upload incomplete — please try again'.
Corrupted PDF
pdfplumber raises an exception. Catch it, set parse_status='failed', error_message='File appears corrupted. Try re-exporting your CV as PDF.'
DOCX with only images
Table and paragraph extraction returns empty string. Triggers scanned detection (len < 100). Same user message as scanned PDF.
Celery worker crashes mid-task
parse_status stays at 'extracting'. Frontend polls forever. Add a timeout: if status is 'extracting' for more than 5 minutes, a separate Celery Beat task sets it to 'failed'.
User uploads second file before first finishes
Allow it. Create a second CVUploadLog. The most recent successful parse wins. Previous logs are kept for audit.
File path traversal attempt
get_valid_filename() strips all path separators. File always saved under cv_uploads/{user_id}/. User cannot escape their directory.
Step 7 — Acceptance Criteria
    • Uploading a valid PDF returns 202 with log_id within 200ms
    • Polling /status/ shows progression through extracting → parsing → success
    • Uploading a scanned image PDF returns status='scanned' with the correct error message
    • Uploading a DOCX with two-column table layout extracts text from both columns
    • Uploading a 6MB file returns 400 file too large
    • A corrupted PDF returns status='failed' with a helpful error message

STEP 8
AI Parse with Claude API
Prompt design, JSON validation, diff UI data, partial save, overwrite protection

8.1  The Claude API Call
The second Celery stage calls the Claude API with the extracted text. The prompt is the most important piece of this entire module. A bad prompt means bad structured data means a broken form.
@shared_task
def send_to_ai_parser(log_id):
    log = CVUploadLog.objects.get(id=log_id)
    log.parse_status = 'parsing'
    log.save()
 
    prompt = build_parse_prompt(log.raw_extracted_text)
 
    try:
        response = call_claude_api(prompt)
        raw_json = clean_json_response(response)
        parsed = validate_with_pydantic(raw_json)
    except json.JSONDecodeError:
        log.parse_status = 'failed'
        log.error_message = 'AI could not parse your CV. Please fill manually.'
        log.save()
        return
    except PydanticValidationError as e:
        # Save whatever partial data validated correctly
        parsed = extract_partial_valid_data(raw_json)
        log.parse_status = 'partial'
 
    log.ai_parsed_json = parsed.dict()
    log.parsed_at = timezone.now()
    count_extracted = count_non_null_fields(parsed)
    log.fields_extracted = count_extracted
    log.fields_total = TOTAL_CV_FIELDS  # constant = 22
    log.save()
8.2  JSON Cleaning
def clean_json_response(text: str) -> dict:
    # Strip markdown code fences Claude sometimes adds
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()
    return json.loads(text)
8.3  The Prompt
The prompt must be extremely explicit about the output format. Every field must be defined. Claude must be told what to do when data is absent — return null, never guess or fabricate.
def build_parse_prompt(cv_text: str) -> str:
    return f'''
Extract structured data from this CV text.
Return ONLY valid JSON. No markdown. No explanation. No preamble.
If a field is not found, use null — never guess or fabricate.
For arrays (experience, education, skills), return [] if none found.
 
CV TEXT:
{cv_text}
 
Return this exact JSON structure:
{{
  "personal": {{"full_name":null,"professional_title":null,
    "email":null,"phone":null,"city":null,"country":null,
    "linkedin_url":null,"github_url":null,"summary":null}},
  "work_experience": [{{"company_name":null,"role_title":null,
    "employment_type":"Full-time","location":null,
    "start_month":null,"start_year":null,"end_month":null,
    "end_year":null,"is_current":false,
    "bullets":["bullet text 1","bullet text 2"]}}],
  "education": [...],
  "skills": [{{"name":null,"category":"Languages"}}],
  "projects": [...],
  "languages": [{{"language_name":null,"proficiency":"Native"}}],
  "certifications": [...]
}}
'''
8.4  Overwrite Protection — The Diff Flow
If a user has existing CV data and uploads a file, never silently overwrite. The backend detects existing data and returns a diff payload instead of immediately saving. The frontend shows the diff UI. User makes choices. A second API call applies the choices.
# After parsing, check if CV already has data:
def should_show_diff(cv, parsed_data):
    has_experience = cv.work_experiences.exists()
    has_education = cv.educations.exists()
    has_skills = cv.skills.exists()
    return has_experience or has_education or has_skills
 
# If diff needed, return parsed data WITHOUT saving to DB
# Status endpoint returns:
# { status: 'needs_diff_review', parsed_data: {...}, existing_data: {...} }
 
# Second API call after user reviews diff:
POST /api/cv/upload/{log_id}/apply/
Body: {
  personal: 'replace',       # replace | keep
  work_experience: 'merge',  # replace | keep | merge
  education: 'replace',
  skills: 'merge',
  projects: 'keep',
}
⚠  Edge Cases — AI Parsing
Claude returns malformed JSON
clean_json_response fails at json.loads(). Set status='failed'. Never let this crash the Celery worker — always catch exceptions.
Claude hallucinates extra fields
Pydantic model ignores extra fields by default (extra='ignore'). Safe — unknown keys are silently dropped.
Claude returns CGPA as string '3.3/4.0'
Pydantic validator on cgpa field: extract float from string using regex before validation.
Bullet points returned as one long string
The prompt explicitly asks for a list. But if Claude returns a string, split on newlines or common bullet characters ('-', '•', '*') as fallback.
User chooses 'merge' for skills but has duplicates
Use the same get_or_create logic from bulk-add. Duplicates are skipped, not errored.
Claude API is down
Catch the HTTP error. Set parse_status='failed', error_message='AI service temporarily unavailable. Your file is saved — try parsing again later.' Add a retry button on frontend.
Step 8 — Acceptance Criteria
    • Uploading your own CV (Muhammad Rizwan's PDF) successfully extracts name, email, company, role, bullets
    • A response with markdown fences is cleaned and parsed correctly
    • Uploading when skills already exist returns status='needs_diff_review' with diff payload
    • Applying diff with merge for skills does not create duplicate entries
    • Claude API timeout sets status='failed' with a retry-friendly error message

STEP 9
PDF Export Pipeline
WeasyPrint rendering, skip-regen logic, template contract, Celery async export

9.1  The Export Flow
POST /api/cv/export/pdf/
 
Step 1: Check if re-render needed:
  if pdf_generated_at >= content_updated_at → return existing PDF URL
  else → trigger Celery task: generate_cv_pdf.delay(cv_id)
  Return 202: { task_id: 'uuid', status: 'generating' }
 
GET /api/cv/export/status/
  Response: { status: 'generating|ready|failed', pdf_url: null|'url' }
 
GET /api/cv/export/download/
  Returns the PDF file as a download response
  Header: Content-Disposition: attachment; filename='cv_rizwan.pdf'
9.2  Template Contract
Each template defines what it can and cannot display. This is checked before rendering to warn users about content that will not appear.
Template
Max Experiences
Max Skills
Photo Slot
ATS Safe
Minimal
4
12
No
Yes
Modern
6
20
Yes
No
Classic
5
15
No
Yes
Technical
8
30
No
Yes
9.3  WeasyPrint Rendering
@shared_task
def generate_cv_pdf(cv_id):
    cv = CVProfile.objects.select_related('user').prefetch_related(
        'work_experiences__bullets', 'educations',
        'skills', 'projects', 'certifications', 'languages'
    ).get(id=cv_id)
 
    # Load correct template
    template_name = f'cv_templates/{cv.template_id or "minimal"}.html'
    context = build_cv_context(cv)
 
    html_string = render_to_string(template_name, context)
    pdf_bytes = weasyprint.HTML(string=html_string).write_pdf()
 
    # Save to disk
    filename = f'cv_exports/{cv.user.id}/cv_{timestamp}.pdf'
    save_file(filename, pdf_bytes)
 
    # Update CVProfile
    CVProfile.objects.filter(id=cv_id).update(
        pdf_file=filename,
        pdf_generated_at=timezone.now()
    )
⚠  Edge Cases — PDF Export
Template not set
Default to 'minimal' template. Never raise an error for missing template.
cv.work_experiences has 8 entries but template max is 4
Slice to template max in build_cv_context(). Warn user in the frontend before they trigger export: '4 of your 8 experiences will appear on this template.'
WeasyPrint crashes on unusual characters
Wrap write_pdf() in try/except. Set export status to 'failed'. Log the error with the cv_id for debugging.
User downloads PDF immediately after triggering export
Status is still 'generating'. Return 202 with message 'Your PDF is being prepared. Check back in a few seconds.'
Two export requests fired simultaneously
Check if a Celery task is already running for this cv_id before creating a new one. Use a Redis lock or check pdf task_id field on CVProfile.
Step 9 — Acceptance Criteria
    • POST /api/cv/export/pdf/ returns 202 and triggers Celery task
    • Second export request with no content changes returns existing PDF URL immediately
    • Saving a bullet after export triggers content_updated_at update — next export re-renders
    • A CV with 8 experiences on the Minimal template (max 4) exports with only 4 experiences
    • WeasyPrint crash sets export status to 'failed' with a logged error

STEP 10
React Frontend — CV Builder UI
RTK Query setup, autosave hook, step navigator, diff modal, upload status polling

10.1  Frontend Folder Structure
src/features/cvBuilder/
├── api/
│   └── cvApi.ts              ← All RTK Query endpoints for this module
├── components/
│   ├── steps/
│   │   ├── ContactInfoStep.tsx
│   │   ├── ExperienceStep.tsx
│   │   ├── EducationStep.tsx
│   │   ├── SkillsStep.tsx
│   │   ├── ProjectsStep.tsx
│   │   └── SummaryStep.tsx
│   ├── StepNavigator.tsx     ← Sidebar with section list + completion dots
│   ├── CompletionBar.tsx     ← 0-100 progress bar
│   ├── UploadModal.tsx       ← File upload + status polling
│   ├── DiffModal.tsx         ← Show existing vs uploaded data for each section
│   └── ExportButton.tsx      ← Trigger PDF + poll status
├── hooks/
│   ├── useAutosave.ts        ← Core autosave logic
│   └── useUploadStatus.ts    ← Polling hook for upload status
└── slice/
    └── cvBuilderSlice.ts     ← Local UI state: currentStep, dirtyFields, uploadLogId
10.2  The Autosave Hook — Most Important Piece
This hook is what makes the entire autosave system work. It handles the dirty flag, debouncing, event listeners, and session storage backup.
// useAutosave.ts
export function useAutosave(sectionName, formData, patchFn) {
  const [isDirty, setIsDirty] = useState(false)
  const inFlightRef = useRef(false)
  const abortRef = useRef(null)
 
  const save = useCallback(async () => {
    if (!isDirty || inFlightRef.current) return
    inFlightRef.current = true
    abortRef.current = new AbortController()
    try {
      await patchFn(formData, { signal: abortRef.current.signal })
      setIsDirty(false)
      sessionStorage.removeItem(`cv_backup_${sectionName}`)
    } catch (err) {
      if (err.name !== 'AbortError') {
        // Save to sessionStorage as emergency backup
        sessionStorage.setItem(`cv_backup_${sectionName}`, JSON.stringify(formData))
        // Show subtle banner: 'Changes not saved — retrying...'
      }
    } finally {
      inFlightRef.current = false
    }
  }, [isDirty, formData, patchFn, sectionName])
 
  // Trigger: tab loses focus
  useEffect(() => {
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) save()
    })
    return () => document.removeEventListener('visibilitychange', save)
  }, [save])
 
  // Trigger: 30-second idle timer
  useEffect(() => {
    const timer = setInterval(() => { if (isDirty) save() }, 30000)
    return () => clearInterval(timer)
  }, [isDirty, save])
 
  return { isDirty, setIsDirty, save }
}
10.3  Autosave Triggers — When save() Is Called
Trigger
How
Notes
User clicks Next button
onClick calls save() then navigates
Most common path
User clicks sidebar section
onClick calls save() then changes step
User jumping between sections
Tab goes to background
visibilitychange event listener
Prevents data loss on tab switch
30-second idle timer
setInterval — only fires if isDirty=true
Safety net
Browser close/refresh
beforeunload event — shows browser warning
Cannot PATCH on unload reliably — session storage backup
10.4  Upload Status Polling Hook
// useUploadStatus.ts
export function useUploadStatus(logId) {
  const [status, setStatus] = useState('pending')
  const TERMINAL = ['success','partial','failed','scanned','needs_diff_review']
 
  useEffect(() => {
    if (!logId) return
    const poll = setInterval(async () => {
      const res = await fetch(`/api/cv/upload/${logId}/status/`)
      const data = await res.json()
      setStatus(data.status)
      if (TERMINAL.includes(data.status)) {
        clearInterval(poll)
      }
    }, 2000)  // poll every 2 seconds
    return () => clearInterval(poll)
  }, [logId])
 
  return status
}
10.5  Diff Modal
When upload status becomes 'needs_diff_review', the DiffModal opens. It shows a side-by-side comparison per section and lets the user choose keep/replace/merge. A second API call applies the choices.
Section
Options
Default
Personal Info
Keep existing / Replace with uploaded
Keep
Work Experience
Keep existing / Replace all / Merge (add new)
Merge
Education
Keep existing / Replace all / Merge
Merge
Skills
Keep existing / Replace all / Merge (add new)
Merge
Projects
Keep existing / Replace all / Merge
Keep
⚠  Edge Cases — Frontend
User refreshes mid-upload
useUploadStatus restores polling from logId stored in Redux slice. If logId is in Redux state on mount, immediately start polling.
Session storage backup on network failure
On remount, check sessionStorage for backup keys. If found, populate the form and show banner: 'We recovered unsaved changes from your last session.'
Step navigation with unsaved changes
If isDirty=true and user tries to navigate away via browser back button, show a confirmation dialog. React Router v6 useBlocker handles this.
Skill autocomplete debouncing
The search endpoint is called on every keystroke. Debounce 300ms before firing. Show a spinner in the input while waiting.
PDF export button spam
Disable the button after first click. Show spinner + 'Generating your PDF...' Re-enable only when status returns 'ready' or 'failed'.
Step 10 — Acceptance Criteria
    • Editing a field and switching sections without clicking Next triggers autosave via visibilitychange
    • Network failure during autosave shows 'Changes not saved' banner and saves to sessionStorage
    • Refreshing page during upload and returning to builder resumes status polling automatically
    • DiffModal appears when upload completes and existing CV data is present
    • Applying merge for skills does not duplicate existing skills
    • PDF export button is disabled while generating and re-enables when complete
    • useBlocker shows confirmation dialog when user tries to navigate away with isDirty=true

Build Checklist — All Steps

Print this page. Check each item off as you build. Do not move to the next step until every item is checked.

Step
Acceptance Check
Done?
1 — Models
migrate runs clean, all 10 tables exist, cascade delete works, seed_skills loads
☐
1 — Models
UUID PKs generated, CVProfile OneToOne enforced at DB level
☐
2 — Lifecycle
Server-first creation, idempotent POST, completion scoring works
☐
2 — Lifecycle
IsOwner blocks cross-user access, content_updated_at updates on child save
☐
3 — Contact
PATCH partial update works, LinkedIn URL normalised, 403 on other user's profile
☐
4 — Experience
Bullets stored in separate table, metric extraction from text works
☐
4 — Experience
Reorder atomic transaction, delete cascades bullets, is_current clears end date
☐
5 — Skills
Canonical search works, bulk add skips duplicates, CGPA validation works
☐
6 — Optional
Projects/certs/languages CRUD works, cleanup tasks can be triggered manually
☐
7 — Upload
202 returned in <200ms, scanned PDF detected, DOCX tables extracted
☐
7 — Upload
Corrupted file returns failed status, 6MB file rejected, filename sanitised
☐
8 — AI Parse
Your own CV parsed correctly, markdown fences cleaned, diff flow triggers
☐
8 — AI Parse
Merge skips duplicates, Claude timeout returns retry-friendly error
☐
9 — PDF Export
Skip regen when content unchanged, template max truncates correctly
☐
10 — Frontend
Autosave fires on tab blur and 30s idle, session storage backup on failure
☐
10 — Frontend
Diff modal appears, polling resumes after refresh, export button disables
☐


HireFlow — CV Builder Module — Complete Implementation Guide
Muhammad Rizwan-ul-Hassan