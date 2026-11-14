"""Initial schema: every domain table, plus triggers that keep the audit log append-only.

Generated with `alembic revision --autogenerate` against an empty database, then
hand-checked. Datetime columns are plain DATETIME holding naive UTC (the app's
UtcDateTime type converts aware values before writing). Enum columns are VARCHAR(32)
validated in Python.

Revision ID: 0001
Revises:
Create Date: 2026-11-15 02:13:47.427948
"""
from alembic import op
import sqlalchemy as sa


revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

AUDIT_NO_UPDATE_TRIGGER = """
CREATE TRIGGER audit_entries_no_update
BEFORE UPDATE ON audit_entries
BEGIN
    SELECT RAISE(ABORT, 'audit entries are append-only');
END
"""

AUDIT_NO_DELETE_TRIGGER = """
CREATE TRIGGER audit_entries_no_delete
BEFORE DELETE ON audit_entries
BEGIN
    SELECT RAISE(ABORT, 'audit entries are append-only');
END
"""


def upgrade() -> None:
    op.create_table('ai_drafts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.String(length=40), nullable=False),
    sa.Column('subject_kind', sa.String(length=32), nullable=False),
    sa.Column('subject_id', sa.Integer(), nullable=False),
    sa.Column('language', sa.String(length=16), nullable=False),
    sa.Column('prompt_version', sa.String(length=32), nullable=False),
    sa.Column('model', sa.String(length=64), nullable=False),
    sa.Column('deployment', sa.String(length=64), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('sure_json', sa.JSON(), nullable=False),
    sa.Column('unsure_json', sa.JSON(), nullable=False),
    sa.Column('would_change_json', sa.JSON(), nullable=False),
    sa.Column('confidence', sa.Double(), nullable=False),
    sa.Column('reasoning_json', sa.JSON(), nullable=False),
    sa.Column('status', sa.Enum('draft', 'confirmed', 'unavailable', name='aidraftstatus', native_enum=False, length=32), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_ai_drafts'))
    )
    with op.batch_alter_table('ai_drafts', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_ai_drafts_kind_subject_kind_subject_id_prompt_version_language'), ['kind', 'subject_kind', 'subject_id', 'prompt_version', 'language'], unique=False)

    op.create_table('ai_images',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.String(length=40), nullable=False),
    sa.Column('subject_id', sa.Integer(), nullable=False),
    sa.Column('path', sa.String(length=255), nullable=False),
    sa.Column('model', sa.String(length=64), nullable=False),
    sa.Column('prompt', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_ai_images'))
    )
    with op.batch_alter_table('ai_images', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_ai_images_subject_id'), ['subject_id'], unique=False)

    op.create_table('competencies',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(length=40), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_competencies')),
    sa.UniqueConstraint('code', name=op.f('uq_competencies_code'))
    )
    op.create_table('employers',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('kind', sa.Enum('in_house', 'contractor', name='employerkind', native_enum=False, length=32), nullable=False),
    sa.Column('logo_key', sa.String(length=64), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_employers')),
    sa.UniqueConstraint('name', name=op.f('uq_employers_name'))
    )
    op.create_table('feeds',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(length=40), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('signal_class', sa.Enum('clinical', 'workplace', 'environmental', 'community', 'worker_reported', name='signalclass', native_enum=False, length=32), nullable=False),
    sa.Column('cadence_minutes', sa.Integer(), nullable=False),
    sa.Column('allowed_delay_minutes', sa.Integer(), nullable=False),
    sa.Column('location_level', sa.String(length=32), nullable=False),
    sa.Column('enabled', sa.Boolean(), nullable=False),
    sa.Column('source', sa.Enum('seeded', 'live', 'uploaded', name='feedsource', native_enum=False, length=32), nullable=False),
    sa.CheckConstraint('allowed_delay_minutes >= 0', name=op.f('ck_feeds_allowed_delay_not_negative')),
    sa.CheckConstraint('cadence_minutes > 0', name=op.f('ck_feeds_cadence_positive')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_feeds')),
    sa.UniqueConstraint('code', name=op.f('uq_feeds_code'))
    )
    op.create_table('hazards',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(length=40), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_hazards')),
    sa.UniqueConstraint('code', name=op.f('uq_hazards_code'))
    )
    op.create_table('settings',
    sa.Column('key', sa.String(length=64), nullable=False),
    sa.Column('value', sa.JSON(), nullable=False),
    sa.PrimaryKeyConstraint('key', name=op.f('pk_settings'))
    )
    op.create_table('shifts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('kind', sa.Enum('day', 'night', name='shiftkind', native_enum=False, length=32), nullable=False),
    sa.Column('start_at', sa.DateTime(), nullable=False),
    sa.Column('end_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_shifts')),
    sa.UniqueConstraint('date', 'kind', name=op.f('uq_shifts_date_kind'))
    )
    op.create_table('site_clocks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('now', sa.DateTime(), nullable=False),
    sa.CheckConstraint('id = 1', name=op.f('ck_site_clocks_single_row')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_site_clocks'))
    )
    op.create_table('zones',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('kind', sa.Enum('berth', 'yard_block', 'camp_block', 'district', name='zonekind', native_enum=False, length=32), nullable=False),
    sa.Column('parent_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['parent_id'], ['zones.id'], name=op.f('fk_zones_parent_id_zones')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_zones')),
    sa.UniqueConstraint('name', name=op.f('uq_zones_name'))
    )
    with op.batch_alter_table('zones', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_zones_parent_id'), ['parent_id'], unique=False)

    op.create_table('activities',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(length=40), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('grade', sa.Integer(), nullable=False),
    sa.Column('exposure_hours_week', sa.Double(), nullable=False),
    sa.Column('severity', sa.Integer(), nullable=False),
    sa.Column('competency_id', sa.Integer(), nullable=True),
    sa.Column('lower_hazard_alternative_id', sa.Integer(), nullable=True),
    sa.CheckConstraint('exposure_hours_week >= 0', name=op.f('ck_activities_exposure_not_negative')),
    sa.CheckConstraint('grade BETWEEN 1 AND 5', name=op.f('ck_activities_grade_range')),
    sa.CheckConstraint('severity BETWEEN 1 AND 5', name=op.f('ck_activities_severity_range')),
    sa.ForeignKeyConstraint(['competency_id'], ['competencies.id'], name=op.f('fk_activities_competency_id_competencies')),
    sa.ForeignKeyConstraint(['lower_hazard_alternative_id'], ['activities.id'], name=op.f('fk_activities_lower_hazard_alternative_id_activities')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_activities')),
    sa.UniqueConstraint('code', name=op.f('uq_activities_code'))
    )
    with op.batch_alter_table('activities', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_activities_competency_id'), ['competency_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_activities_lower_hazard_alternative_id'), ['lower_hazard_alternative_id'], unique=False)

    op.create_table('camp_tickets',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('zone_id', sa.Integer(), nullable=False),
    sa.Column('opened_at', sa.DateTime(), nullable=False),
    sa.Column('closed_at', sa.DateTime(), nullable=True),
    sa.Column('kind', sa.String(length=40), nullable=False),
    sa.Column('units_affected', sa.Integer(), nullable=False),
    sa.Column('units_total', sa.Integer(), nullable=False),
    sa.CheckConstraint('units_affected >= 0 AND units_affected <= units_total', name=op.f('ck_camp_tickets_units_in_range')),
    sa.ForeignKeyConstraint(['zone_id'], ['zones.id'], name=op.f('fk_camp_tickets_zone_id_zones')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_camp_tickets'))
    )
    with op.batch_alter_table('camp_tickets', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_camp_tickets_zone_id'), ['zone_id'], unique=False)

    op.create_table('clinics',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('zone_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['zone_id'], ['zones.id'], name=op.f('fk_clinics_zone_id_zones')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_clinics')),
    sa.UniqueConstraint('name', name=op.f('uq_clinics_name'))
    )
    with op.batch_alter_table('clinics', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_clinics_zone_id'), ['zone_id'], unique=False)

    op.create_table('feed_readings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('feed_id', sa.Integer(), nullable=False),
    sa.Column('zone_id', sa.Integer(), nullable=True),
    sa.Column('at', sa.DateTime(), nullable=False),
    sa.Column('metric', sa.String(length=40), nullable=False),
    sa.Column('value', sa.Double(), nullable=False),
    sa.Column('source', sa.Enum('seeded', 'live', 'uploaded', name='feedsource', native_enum=False, length=32), nullable=False),
    sa.ForeignKeyConstraint(['feed_id'], ['feeds.id'], name=op.f('fk_feed_readings_feed_id_feeds')),
    sa.ForeignKeyConstraint(['zone_id'], ['zones.id'], name=op.f('fk_feed_readings_zone_id_zones')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_feed_readings'))
    )
    with op.batch_alter_table('feed_readings', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_feed_readings_feed_id_zone_id_at'), ['feed_id', 'zone_id', 'at'], unique=False)
        batch_op.create_index(batch_op.f('ix_feed_readings_zone_id'), ['zone_id'], unique=False)

    op.create_table('inspections',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('source_kind', sa.String(length=32), nullable=False),
    sa.Column('source_id', sa.Integer(), nullable=False),
    sa.Column('zone_id', sa.Integer(), nullable=False),
    sa.Column('due_at', sa.DateTime(), nullable=False),
    sa.Column('status', sa.Enum('scheduled', 'done', 'cancelled', name='inspectionstatus', native_enum=False, length=32), nullable=False),
    sa.ForeignKeyConstraint(['zone_id'], ['zones.id'], name=op.f('fk_inspections_zone_id_zones')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_inspections'))
    )
    with op.batch_alter_table('inspections', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_inspections_source_kind_source_id'), ['source_kind', 'source_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_inspections_zone_id'), ['zone_id'], unique=False)

    op.create_table('learning_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.Enum('card', 'toolbox_talk', 'swp_change', name='learningkind', native_enum=False, length=32), nullable=False),
    sa.Column('source_kind', sa.String(length=32), nullable=False),
    sa.Column('source_id', sa.Integer(), nullable=False),
    sa.Column('draft_id', sa.Integer(), nullable=True),
    sa.Column('status', sa.Enum('draft', 'published', 'retired', name='learningstatus', native_enum=False, length=32), nullable=False),
    sa.ForeignKeyConstraint(['draft_id'], ['ai_drafts.id'], name=op.f('fk_learning_items_draft_id_ai_drafts')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_learning_items'))
    )
    with op.batch_alter_table('learning_items', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_learning_items_draft_id'), ['draft_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_learning_items_source_kind_source_id'), ['source_kind', 'source_id'], unique=False)

    op.create_table('people',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('employer_id', sa.Integer(), nullable=False),
    sa.Column('first_name', sa.String(length=80), nullable=False),
    sa.Column('last_name', sa.String(length=80), nullable=False),
    sa.Column('email', sa.String(length=254), nullable=False),
    sa.Column('role', sa.Enum('worker', 'foreman', 'planner', 'shift_manager', 'permit_issuer', 'hse_head', 'clinician', 'authority', 'admin', name='role', native_enum=False, length=32), nullable=False),
    sa.Column('job_title', sa.String(length=120), nullable=False),
    sa.Column('hire_date', sa.Date(), nullable=False),
    sa.Column('site_arrival_date', sa.Date(), nullable=False),
    sa.Column('induction', sa.Enum('site', 'contractor', name='inductionpathway', native_enum=False, length=32), nullable=False),
    sa.Column('camp_zone_id', sa.Integer(), nullable=True),
    sa.Column('display_language', sa.String(length=16), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['camp_zone_id'], ['zones.id'], name=op.f('fk_people_camp_zone_id_zones')),
    sa.ForeignKeyConstraint(['employer_id'], ['employers.id'], name=op.f('fk_people_employer_id_employers')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_people')),
    sa.UniqueConstraint('email', name=op.f('uq_people_email'))
    )
    with op.batch_alter_table('people', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_people_camp_zone_id'), ['camp_zone_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_people_employer_id'), ['employer_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_people_role'), ['role'], unique=False)

    op.create_table('warning_records',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('opened_at', sa.DateTime(), nullable=False),
    sa.Column('zone_id', sa.Integer(), nullable=False),
    sa.Column('level', sa.Enum('watch', 'warning', 'alert', name='warninglevel', native_enum=False, length=32), nullable=False),
    sa.Column('status', sa.Enum('open', 'closed', name='warningstatus', native_enum=False, length=32), nullable=False),
    sa.Column('outcome', sa.Enum('right', 'early', 'false_alarm', 'missed', name='warningoutcome', native_enum=False, length=32), nullable=True),
    sa.Column('closed_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['zone_id'], ['zones.id'], name=op.f('fk_warning_records_zone_id_zones')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_warning_records'))
    )
    with op.batch_alter_table('warning_records', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_warning_records_opened_at'), ['opened_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_warning_records_zone_id'), ['zone_id'], unique=False)

    op.create_table('absences',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('person_id', sa.Integer(), nullable=False),
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('kind', sa.String(length=32), nullable=False),
    sa.ForeignKeyConstraint(['person_id'], ['people.id'], name=op.f('fk_absences_person_id_people')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_absences'))
    )
    with op.batch_alter_table('absences', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_absences_person_id'), ['person_id'], unique=False)

    op.create_table('actions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('source_kind', sa.String(length=32), nullable=False),
    sa.Column('source_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('control_level', sa.Enum('eliminate', 'substitute', 'engineer', 'administrative', 'ppe', name='controllevel', native_enum=False, length=32), nullable=False),
    sa.Column('owner_id', sa.Integer(), nullable=False),
    sa.Column('due_on', sa.Date(), nullable=False),
    sa.Column('status', sa.Enum('open', 'in_progress', 'done', 'cancelled', name='actionstatus', native_enum=False, length=32), nullable=False),
    sa.Column('effectiveness_check_on', sa.Date(), nullable=True),
    sa.Column('effective', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['owner_id'], ['people.id'], name=op.f('fk_actions_owner_id_people')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_actions'))
    )
    with op.batch_alter_table('actions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_actions_owner_id'), ['owner_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_actions_source_kind_source_id'), ['source_kind', 'source_id'], unique=False)

    op.create_table('activity_hazards',
    sa.Column('activity_id', sa.Integer(), nullable=False),
    sa.Column('hazard_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['activity_id'], ['activities.id'], name=op.f('fk_activity_hazards_activity_id_activities')),
    sa.ForeignKeyConstraint(['hazard_id'], ['hazards.id'], name=op.f('fk_activity_hazards_hazard_id_hazards')),
    sa.PrimaryKeyConstraint('activity_id', 'hazard_id', name=op.f('pk_activity_hazards'))
    )
    with op.batch_alter_table('activity_hazards', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_activity_hazards_hazard_id'), ['hazard_id'], unique=False)

    op.create_table('audit_entries',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('at', sa.DateTime(), nullable=False),
    sa.Column('actor_id', sa.Integer(), nullable=True),
    sa.Column('actor_role', sa.Enum('worker', 'foreman', 'planner', 'shift_manager', 'permit_issuer', 'hse_head', 'clinician', 'authority', 'admin', name='role', native_enum=False, length=32), nullable=True),
    sa.Column('action', sa.String(length=64), nullable=False),
    sa.Column('subject_kind', sa.String(length=32), nullable=False),
    sa.Column('subject_ref', sa.String(length=128), nullable=False),
    sa.Column('evidence_json', sa.JSON(), nullable=True),
    sa.Column('model_version', sa.String(length=64), nullable=True),
    sa.ForeignKeyConstraint(['actor_id'], ['people.id'], name=op.f('fk_audit_entries_actor_id_people')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_entries'))
    )
    with op.batch_alter_table('audit_entries', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_audit_entries_actor_id'), ['actor_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_audit_entries_at'), ['at'], unique=False)

    op.create_table('check_ins',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('person_id', sa.Integer(), nullable=False),
    sa.Column('shift_id', sa.Integer(), nullable=False),
    sa.Column('at', sa.DateTime(), nullable=False),
    sa.Column('sleep_hours_band', sa.String(length=16), nullable=False),
    sa.Column('feeling', sa.Enum('good', 'tired', 'unwell', name='feeling', native_enum=False, length=32), nullable=False),
    sa.Column('hydration_ok', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['person_id'], ['people.id'], name=op.f('fk_check_ins_person_id_people')),
    sa.ForeignKeyConstraint(['shift_id'], ['shifts.id'], name=op.f('fk_check_ins_shift_id_shifts')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_check_ins')),
    sa.UniqueConstraint('person_id', 'shift_id', name=op.f('uq_check_ins_person_id_shift_id'))
    )
    with op.batch_alter_table('check_ins', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_check_ins_shift_id'), ['shift_id'], unique=False)

    op.create_table('clinic_visits',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('clinic_id', sa.Integer(), nullable=False),
    sa.Column('person_id', sa.Integer(), nullable=False),
    sa.Column('zone_id', sa.Integer(), nullable=False),
    sa.Column('at', sa.DateTime(), nullable=False),
    sa.Column('syndrome', sa.String(length=40), nullable=False),
    sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], name=op.f('fk_clinic_visits_clinic_id_clinics')),
    sa.ForeignKeyConstraint(['person_id'], ['people.id'], name=op.f('fk_clinic_visits_person_id_people')),
    sa.ForeignKeyConstraint(['zone_id'], ['zones.id'], name=op.f('fk_clinic_visits_zone_id_zones')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_clinic_visits'))
    )
    with op.batch_alter_table('clinic_visits', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_clinic_visits_at'), ['at'], unique=False)
        batch_op.create_index(batch_op.f('ix_clinic_visits_clinic_id'), ['clinic_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_clinic_visits_person_id'), ['person_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_clinic_visits_zone_id_at'), ['zone_id', 'at'], unique=False)

    op.create_table('fitness_outcomes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('person_id', sa.Integer(), nullable=False),
    sa.Column('decided_by', sa.Integer(), nullable=False),
    sa.Column('at', sa.DateTime(), nullable=False),
    sa.Column('outcome', sa.Enum('fit', 'fit_with_restrictions', 'not_today', name='fitnessdecision', native_enum=False, length=32), nullable=False),
    sa.Column('restriction_text', sa.Text(), nullable=True),
    sa.Column('share_with_employer', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['decided_by'], ['people.id'], name=op.f('fk_fitness_outcomes_decided_by_people')),
    sa.ForeignKeyConstraint(['person_id'], ['people.id'], name=op.f('fk_fitness_outcomes_person_id_people')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_fitness_outcomes'))
    )
    with op.batch_alter_table('fitness_outcomes', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_fitness_outcomes_decided_by'), ['decided_by'], unique=False)
        batch_op.create_index(batch_op.f('ix_fitness_outcomes_person_id'), ['person_id'], unique=False)

    op.create_table('gangs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.Column('foreman_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['foreman_id'], ['people.id'], name=op.f('fk_gangs_foreman_id_people')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_gangs')),
    sa.UniqueConstraint('name', name=op.f('uq_gangs_name'))
    )
    with op.batch_alter_table('gangs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_gangs_foreman_id'), ['foreman_id'], unique=False)

    op.create_table('hazard_reports',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('activity_id', sa.Integer(), nullable=True),
    sa.Column('zone_id', sa.Integer(), nullable=False),
    sa.Column('reported_by', sa.Integer(), nullable=True),
    sa.Column('at', sa.DateTime(), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('status', sa.Enum('open', 'in_review', 'closed', name='recordstatus', native_enum=False, length=32), nullable=False),
    sa.ForeignKeyConstraint(['activity_id'], ['activities.id'], name=op.f('fk_hazard_reports_activity_id_activities')),
    sa.ForeignKeyConstraint(['reported_by'], ['people.id'], name=op.f('fk_hazard_reports_reported_by_people')),
    sa.ForeignKeyConstraint(['zone_id'], ['zones.id'], name=op.f('fk_hazard_reports_zone_id_zones')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_hazard_reports'))
    )
    with op.batch_alter_table('hazard_reports', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_hazard_reports_activity_id'), ['activity_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_hazard_reports_at'), ['at'], unique=False)
        batch_op.create_index(batch_op.f('ix_hazard_reports_reported_by'), ['reported_by'], unique=False)
        batch_op.create_index(batch_op.f('ix_hazard_reports_zone_id'), ['zone_id'], unique=False)

    op.create_table('incidents',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('activity_id', sa.Integer(), nullable=False),
    sa.Column('zone_id', sa.Integer(), nullable=False),
    sa.Column('reported_by', sa.Integer(), nullable=False),
    sa.Column('at', sa.DateTime(), nullable=False),
    sa.Column('shift_kind', sa.Enum('day', 'night', name='shiftkind', native_enum=False, length=32), nullable=False),
    sa.Column('kind', sa.Enum('injury', 'illness', 'property', 'environment', name='incidentkind', native_enum=False, length=32), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('photo_key', sa.String(length=255), nullable=True),
    sa.Column('potential_severity', sa.Integer(), nullable=False),
    sa.Column('actual_severity', sa.Integer(), nullable=True),
    sa.Column('lost_time', sa.Boolean(), nullable=False),
    sa.Column('status', sa.Enum('open', 'in_review', 'closed', name='recordstatus', native_enum=False, length=32), nullable=False),
    sa.Column('closed_at', sa.DateTime(), nullable=True),
    sa.CheckConstraint('actual_severity BETWEEN 1 AND 5', name=op.f('ck_incidents_actual_severity_range')),
    sa.CheckConstraint('potential_severity BETWEEN 1 AND 5', name=op.f('ck_incidents_potential_severity_range')),
    sa.ForeignKeyConstraint(['activity_id'], ['activities.id'], name=op.f('fk_incidents_activity_id_activities')),
    sa.ForeignKeyConstraint(['reported_by'], ['people.id'], name=op.f('fk_incidents_reported_by_people')),
    sa.ForeignKeyConstraint(['zone_id'], ['zones.id'], name=op.f('fk_incidents_zone_id_zones')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_incidents'))
    )
    with op.batch_alter_table('incidents', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_incidents_activity_id'), ['activity_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_incidents_at'), ['at'], unique=False)
        batch_op.create_index(batch_op.f('ix_incidents_reported_by'), ['reported_by'], unique=False)
        batch_op.create_index(batch_op.f('ix_incidents_zone_id'), ['zone_id'], unique=False)

    op.create_table('inspection_checks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('inspection_id', sa.Integer(), nullable=False),
    sa.Column('driver', sa.String(length=64), nullable=False),
    sa.Column('question', sa.Text(), nullable=False),
    sa.Column('result', sa.Enum('confirmed', 'not_found', name='checkresult', native_enum=False, length=32), nullable=True),
    sa.Column('note', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['inspection_id'], ['inspections.id'], name=op.f('fk_inspection_checks_inspection_id_inspections')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_inspection_checks'))
    )
    with op.batch_alter_table('inspection_checks', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_inspection_checks_inspection_id'), ['inspection_id'], unique=False)

    op.create_table('lab_panels',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('person_id', sa.Integer(), nullable=False),
    sa.Column('at', sa.DateTime(), nullable=False),
    sa.Column('panel', sa.String(length=40), nullable=False),
    sa.Column('value', sa.Double(), nullable=False),
    sa.Column('flag', sa.String(length=16), nullable=True),
    sa.ForeignKeyConstraint(['person_id'], ['people.id'], name=op.f('fk_lab_panels_person_id_people')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_lab_panels'))
    )
    with op.batch_alter_table('lab_panels', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_lab_panels_person_id'), ['person_id'], unique=False)

    op.create_table('learning_reads',
    sa.Column('item_id', sa.Integer(), nullable=False),
    sa.Column('person_id', sa.Integer(), nullable=False),
    sa.Column('at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['item_id'], ['learning_items.id'], name=op.f('fk_learning_reads_item_id_learning_items')),
    sa.ForeignKeyConstraint(['person_id'], ['people.id'], name=op.f('fk_learning_reads_person_id_people')),
    sa.PrimaryKeyConstraint('item_id', 'person_id', name=op.f('pk_learning_reads'))
    )
    with op.batch_alter_table('learning_reads', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_learning_reads_person_id'), ['person_id'], unique=False)

    op.create_table('near_misses',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('activity_id', sa.Integer(), nullable=False),
    sa.Column('zone_id', sa.Integer(), nullable=False),
    sa.Column('reported_by', sa.Integer(), nullable=True),
    sa.Column('at', sa.DateTime(), nullable=False),
    sa.Column('shift_kind', sa.Enum('day', 'night', name='shiftkind', native_enum=False, length=32), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('potential_severity', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('open', 'in_review', 'closed', name='recordstatus', native_enum=False, length=32), nullable=False),
    sa.CheckConstraint('potential_severity BETWEEN 1 AND 5', name=op.f('ck_near_misses_potential_severity_range')),
    sa.ForeignKeyConstraint(['activity_id'], ['activities.id'], name=op.f('fk_near_misses_activity_id_activities')),
    sa.ForeignKeyConstraint(['reported_by'], ['people.id'], name=op.f('fk_near_misses_reported_by_people')),
    sa.ForeignKeyConstraint(['zone_id'], ['zones.id'], name=op.f('fk_near_misses_zone_id_zones')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_near_misses'))
    )
    with op.batch_alter_table('near_misses', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_near_misses_activity_id'), ['activity_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_near_misses_at'), ['at'], unique=False)
        batch_op.create_index(batch_op.f('ix_near_misses_reported_by'), ['reported_by'], unique=False)
        batch_op.create_index(batch_op.f('ix_near_misses_zone_id'), ['zone_id'], unique=False)

    op.create_table('observations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('activity_id', sa.Integer(), nullable=False),
    sa.Column('zone_id', sa.Integer(), nullable=False),
    sa.Column('person_id', sa.Integer(), nullable=True),
    sa.Column('at', sa.DateTime(), nullable=False),
    sa.Column('kind', sa.Enum('unsafe_act', 'unsafe_behaviour', 'unsafe_condition', 'safe', name='observationkind', native_enum=False, length=32), nullable=False),
    sa.Column('shift_kind', sa.Enum('day', 'night', name='shiftkind', native_enum=False, length=32), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['activity_id'], ['activities.id'], name=op.f('fk_observations_activity_id_activities')),
    sa.ForeignKeyConstraint(['person_id'], ['people.id'], name=op.f('fk_observations_person_id_people')),
    sa.ForeignKeyConstraint(['zone_id'], ['zones.id'], name=op.f('fk_observations_zone_id_zones')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_observations'))
    )
    with op.batch_alter_table('observations', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_observations_activity_id_at'), ['activity_id', 'at'], unique=False)
        batch_op.create_index(batch_op.f('ix_observations_at'), ['at'], unique=False)
        batch_op.create_index(batch_op.f('ix_observations_person_id'), ['person_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_observations_zone_id'), ['zone_id'], unique=False)

    op.create_table('permits',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('number', sa.String(length=32), nullable=False),
    sa.Column('activity_id', sa.Integer(), nullable=False),
    sa.Column('zone_id', sa.Integer(), nullable=False),
    sa.Column('shift_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('requested', 'assessed', 'issued', 'live', 'suspended', 'closed', name='permitstatus', native_enum=False, length=32), nullable=False),
    sa.Column('issuer_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['activity_id'], ['activities.id'], name=op.f('fk_permits_activity_id_activities')),
    sa.ForeignKeyConstraint(['issuer_id'], ['people.id'], name=op.f('fk_permits_issuer_id_people')),
    sa.ForeignKeyConstraint(['shift_id'], ['shifts.id'], name=op.f('fk_permits_shift_id_shifts')),
    sa.ForeignKeyConstraint(['zone_id'], ['zones.id'], name=op.f('fk_permits_zone_id_zones')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_permits')),
    sa.UniqueConstraint('number', name=op.f('uq_permits_number'))
    )
    with op.batch_alter_table('permits', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_permits_activity_id'), ['activity_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_permits_issuer_id'), ['issuer_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_permits_shift_id'), ['shift_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_permits_status'), ['status'], unique=False)
        batch_op.create_index(batch_op.f('ix_permits_zone_id'), ['zone_id'], unique=False)

    op.create_table('person_competencies',
    sa.Column('person_id', sa.Integer(), nullable=False),
    sa.Column('competency_id', sa.Integer(), nullable=False),
    sa.Column('valid_until', sa.Date(), nullable=True),
    sa.ForeignKeyConstraint(['competency_id'], ['competencies.id'], name=op.f('fk_person_competencies_competency_id_competencies')),
    sa.ForeignKeyConstraint(['person_id'], ['people.id'], name=op.f('fk_person_competencies_person_id_people')),
    sa.PrimaryKeyConstraint('person_id', 'competency_id', name=op.f('pk_person_competencies'))
    )
    with op.batch_alter_table('person_competencies', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_person_competencies_competency_id'), ['competency_id'], unique=False)

    op.create_table('swp_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('activity_id', sa.Integer(), nullable=False),
    sa.Column('seq', sa.Integer(), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['activity_id'], ['activities.id'], name=op.f('fk_swp_items_activity_id_activities')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_swp_items'))
    )
    with op.batch_alter_table('swp_items', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_swp_items_activity_id'), ['activity_id'], unique=False)

    op.create_table('training_records',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('person_id', sa.Integer(), nullable=False),
    sa.Column('course_code', sa.String(length=40), nullable=False),
    sa.Column('completed_on', sa.Date(), nullable=False),
    sa.ForeignKeyConstraint(['person_id'], ['people.id'], name=op.f('fk_training_records_person_id_people')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_training_records'))
    )
    with op.batch_alter_table('training_records', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_training_records_person_id'), ['person_id'], unique=False)

    op.create_table('warning_steps',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('warning_id', sa.Integer(), nullable=False),
    sa.Column('step', sa.Integer(), nullable=False),
    sa.Column('draft_id', sa.Integer(), nullable=True),
    sa.Column('status', sa.Enum('pending', 'drafted', 'confirmed', name='warningstepstatus', native_enum=False, length=32), nullable=False),
    sa.Column('confirmed_by', sa.Integer(), nullable=True),
    sa.Column('confirmed_at', sa.DateTime(), nullable=True),
    sa.CheckConstraint('step BETWEEN 1 AND 10', name=op.f('ck_warning_steps_step_range')),
    sa.ForeignKeyConstraint(['confirmed_by'], ['people.id'], name=op.f('fk_warning_steps_confirmed_by_people')),
    sa.ForeignKeyConstraint(['draft_id'], ['ai_drafts.id'], name=op.f('fk_warning_steps_draft_id_ai_drafts')),
    sa.ForeignKeyConstraint(['warning_id'], ['warning_records.id'], name=op.f('fk_warning_steps_warning_id_warning_records')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_warning_steps')),
    sa.UniqueConstraint('warning_id', 'step', name=op.f('uq_warning_steps_warning_id_step'))
    )
    with op.batch_alter_table('warning_steps', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_warning_steps_confirmed_by'), ['confirmed_by'], unique=False)
        batch_op.create_index(batch_op.f('ix_warning_steps_draft_id'), ['draft_id'], unique=False)

    op.create_table('weights_versions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('version', sa.String(length=16), nullable=False),
    sa.Column('status', sa.Enum('active', 'proposed', 'retired', name='weightsstatus', native_enum=False, length=32), nullable=False),
    sa.Column('body_json', sa.JSON(), nullable=False),
    sa.Column('approved_by', sa.Integer(), nullable=True),
    sa.Column('approved_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['approved_by'], ['people.id'], name=op.f('fk_weights_versions_approved_by_people')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_weights_versions')),
    sa.UniqueConstraint('version', name=op.f('uq_weights_versions_version'))
    )
    with op.batch_alter_table('weights_versions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_weights_versions_approved_by'), ['approved_by'], unique=False)
        batch_op.create_index('uq_weights_versions_one_active', ['status'], unique=True, sqlite_where=sa.text("status = 'active'"))

    op.create_table('assignments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('shift_id', sa.Integer(), nullable=False),
    sa.Column('person_id', sa.Integer(), nullable=False),
    sa.Column('activity_id', sa.Integer(), nullable=False),
    sa.Column('gang_id', sa.Integer(), nullable=True),
    sa.Column('source', sa.Enum('roster', 'swap', name='assignmentsource', native_enum=False, length=32), nullable=False),
    sa.ForeignKeyConstraint(['activity_id'], ['activities.id'], name=op.f('fk_assignments_activity_id_activities')),
    sa.ForeignKeyConstraint(['gang_id'], ['gangs.id'], name=op.f('fk_assignments_gang_id_gangs')),
    sa.ForeignKeyConstraint(['person_id'], ['people.id'], name=op.f('fk_assignments_person_id_people')),
    sa.ForeignKeyConstraint(['shift_id'], ['shifts.id'], name=op.f('fk_assignments_shift_id_shifts')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_assignments')),
    sa.UniqueConstraint('shift_id', 'person_id', name=op.f('uq_assignments_shift_id_person_id'))
    )
    with op.batch_alter_table('assignments', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_assignments_activity_id'), ['activity_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_assignments_gang_id'), ['gang_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_assignments_person_id'), ['person_id'], unique=False)

    op.create_table('permit_conditions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('permit_id', sa.Integer(), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('origin', sa.Enum('issuer', 'warning', name='conditionorigin', native_enum=False, length=32), nullable=False),
    sa.Column('warning_id', sa.Integer(), nullable=True),
    sa.Column('status', sa.Enum('draft', 'accepted', 'edited', 'rejected', name='conditionstatus', native_enum=False, length=32), nullable=False),
    sa.ForeignKeyConstraint(['permit_id'], ['permits.id'], name=op.f('fk_permit_conditions_permit_id_permits')),
    sa.ForeignKeyConstraint(['warning_id'], ['warning_records.id'], name=op.f('fk_permit_conditions_warning_id_warning_records')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_permit_conditions'))
    )
    with op.batch_alter_table('permit_conditions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_permit_conditions_permit_id'), ['permit_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_permit_conditions_warning_id'), ['warning_id'], unique=False)

    op.create_table('permit_events',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('permit_id', sa.Integer(), nullable=False),
    sa.Column('at', sa.DateTime(), nullable=False),
    sa.Column('kind', sa.String(length=40), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('actor_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['actor_id'], ['people.id'], name=op.f('fk_permit_events_actor_id_people')),
    sa.ForeignKeyConstraint(['permit_id'], ['permits.id'], name=op.f('fk_permit_events_permit_id_permits')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_permit_events'))
    )
    with op.batch_alter_table('permit_events', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_permit_events_actor_id'), ['actor_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_permit_events_permit_id'), ['permit_id'], unique=False)

    op.create_table('score_runs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.Enum('evening', 'shift_start', 'manual', name='runkind', native_enum=False, length=32), nullable=False),
    sa.Column('shift_id', sa.Integer(), nullable=False),
    sa.Column('weights_version_id', sa.Integer(), nullable=False),
    sa.Column('ran_at', sa.DateTime(), nullable=False),
    sa.Column('conditions_source', sa.Enum('scenario', 'live', name='conditionssource', native_enum=False, length=32), nullable=False),
    sa.ForeignKeyConstraint(['shift_id'], ['shifts.id'], name=op.f('fk_score_runs_shift_id_shifts')),
    sa.ForeignKeyConstraint(['weights_version_id'], ['weights_versions.id'], name=op.f('fk_score_runs_weights_version_id_weights_versions')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_score_runs'))
    )
    with op.batch_alter_table('score_runs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_score_runs_shift_id'), ['shift_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_score_runs_weights_version_id'), ['weights_version_id'], unique=False)

    op.create_table('unwell_events',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('person_id', sa.Integer(), nullable=False),
    sa.Column('shift_id', sa.Integer(), nullable=False),
    sa.Column('at', sa.DateTime(), nullable=False),
    sa.Column('permit_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['permit_id'], ['permits.id'], name=op.f('fk_unwell_events_permit_id_permits')),
    sa.ForeignKeyConstraint(['person_id'], ['people.id'], name=op.f('fk_unwell_events_person_id_people')),
    sa.ForeignKeyConstraint(['shift_id'], ['shifts.id'], name=op.f('fk_unwell_events_shift_id_shifts')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_unwell_events'))
    )
    with op.batch_alter_table('unwell_events', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_unwell_events_permit_id'), ['permit_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_unwell_events_person_id'), ['person_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_unwell_events_shift_id'), ['shift_id'], unique=False)

    op.create_table('assignment_scores',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('run_id', sa.Integer(), nullable=False),
    sa.Column('assignment_id', sa.Integer(), nullable=False),
    sa.Column('intrinsic', sa.Double(), nullable=False),
    sa.Column('control', sa.Double(), nullable=False),
    sa.Column('condition', sa.Double(), nullable=False),
    sa.Column('profile', sa.Double(), nullable=False),
    sa.Column('r', sa.Double(), nullable=False),
    sa.Column('tier', sa.Enum('fit', 'fit_with_controls', 'reassign', 'refer', 'unknown', name='tier', native_enum=False, length=32), nullable=False),
    sa.Column('drivers_json', sa.JSON(), nullable=False),
    sa.Column('confidence', sa.Double(), nullable=False),
    sa.Column('group_step_limited', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['assignment_id'], ['assignments.id'], name=op.f('fk_assignment_scores_assignment_id_assignments')),
    sa.ForeignKeyConstraint(['run_id'], ['score_runs.id'], name=op.f('fk_assignment_scores_run_id_score_runs')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_assignment_scores')),
    sa.UniqueConstraint('run_id', 'assignment_id', name=op.f('uq_assignment_scores_run_id_assignment_id'))
    )
    with op.batch_alter_table('assignment_scores', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_assignment_scores_assignment_id'), ['assignment_id'], unique=False)

    op.create_table('swap_proposals',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('run_id', sa.Integer(), nullable=False),
    sa.Column('assignment_id', sa.Integer(), nullable=False),
    sa.Column('to_activity_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('proposed', 'accepted', 'declined', 'approved', 'rejected', name='swapstatus', native_enum=False, length=32), nullable=False),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('decided_by', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['assignment_id'], ['assignments.id'], name=op.f('fk_swap_proposals_assignment_id_assignments')),
    sa.ForeignKeyConstraint(['decided_by'], ['people.id'], name=op.f('fk_swap_proposals_decided_by_people')),
    sa.ForeignKeyConstraint(['run_id'], ['score_runs.id'], name=op.f('fk_swap_proposals_run_id_score_runs')),
    sa.ForeignKeyConstraint(['to_activity_id'], ['activities.id'], name=op.f('fk_swap_proposals_to_activity_id_activities')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_swap_proposals'))
    )
    with op.batch_alter_table('swap_proposals', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_swap_proposals_assignment_id'), ['assignment_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_swap_proposals_decided_by'), ['decided_by'], unique=False)
        batch_op.create_index(batch_op.f('ix_swap_proposals_run_id'), ['run_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_swap_proposals_to_activity_id'), ['to_activity_id'], unique=False)

    op.create_table('contests',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('assignment_score_id', sa.Integer(), nullable=False),
    sa.Column('person_id', sa.Integer(), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('status', sa.Enum('open', 'upheld', 'dismissed', name='conteststatus', native_enum=False, length=32), nullable=False),
    sa.ForeignKeyConstraint(['assignment_score_id'], ['assignment_scores.id'], name=op.f('fk_contests_assignment_score_id_assignment_scores')),
    sa.ForeignKeyConstraint(['person_id'], ['people.id'], name=op.f('fk_contests_person_id_people')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_contests'))
    )
    with op.batch_alter_table('contests', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_contests_assignment_score_id'), ['assignment_score_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_contests_person_id'), ['person_id'], unique=False)

    # The audit log is append-only: abort any UPDATE or DELETE, including raw SQL.
    op.execute(AUDIT_NO_UPDATE_TRIGGER)
    op.execute(AUDIT_NO_DELETE_TRIGGER)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_entries_no_delete")
    op.execute("DROP TRIGGER IF EXISTS audit_entries_no_update")
    with op.batch_alter_table('contests', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_contests_person_id'))
        batch_op.drop_index(batch_op.f('ix_contests_assignment_score_id'))

    op.drop_table('contests')
    with op.batch_alter_table('swap_proposals', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_swap_proposals_to_activity_id'))
        batch_op.drop_index(batch_op.f('ix_swap_proposals_run_id'))
        batch_op.drop_index(batch_op.f('ix_swap_proposals_decided_by'))
        batch_op.drop_index(batch_op.f('ix_swap_proposals_assignment_id'))

    op.drop_table('swap_proposals')
    with op.batch_alter_table('assignment_scores', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_assignment_scores_assignment_id'))

    op.drop_table('assignment_scores')
    with op.batch_alter_table('unwell_events', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_unwell_events_shift_id'))
        batch_op.drop_index(batch_op.f('ix_unwell_events_person_id'))
        batch_op.drop_index(batch_op.f('ix_unwell_events_permit_id'))

    op.drop_table('unwell_events')
    with op.batch_alter_table('score_runs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_score_runs_weights_version_id'))
        batch_op.drop_index(batch_op.f('ix_score_runs_shift_id'))

    op.drop_table('score_runs')
    with op.batch_alter_table('permit_events', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_permit_events_permit_id'))
        batch_op.drop_index(batch_op.f('ix_permit_events_actor_id'))

    op.drop_table('permit_events')
    with op.batch_alter_table('permit_conditions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_permit_conditions_warning_id'))
        batch_op.drop_index(batch_op.f('ix_permit_conditions_permit_id'))

    op.drop_table('permit_conditions')
    with op.batch_alter_table('assignments', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_assignments_person_id'))
        batch_op.drop_index(batch_op.f('ix_assignments_gang_id'))
        batch_op.drop_index(batch_op.f('ix_assignments_activity_id'))

    op.drop_table('assignments')
    with op.batch_alter_table('weights_versions', schema=None) as batch_op:
        batch_op.drop_index('uq_weights_versions_one_active', sqlite_where=sa.text("status = 'active'"))
        batch_op.drop_index(batch_op.f('ix_weights_versions_approved_by'))

    op.drop_table('weights_versions')
    with op.batch_alter_table('warning_steps', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_warning_steps_draft_id'))
        batch_op.drop_index(batch_op.f('ix_warning_steps_confirmed_by'))

    op.drop_table('warning_steps')
    with op.batch_alter_table('training_records', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_training_records_person_id'))

    op.drop_table('training_records')
    with op.batch_alter_table('swp_items', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_swp_items_activity_id'))

    op.drop_table('swp_items')
    with op.batch_alter_table('person_competencies', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_person_competencies_competency_id'))

    op.drop_table('person_competencies')
    with op.batch_alter_table('permits', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_permits_zone_id'))
        batch_op.drop_index(batch_op.f('ix_permits_status'))
        batch_op.drop_index(batch_op.f('ix_permits_shift_id'))
        batch_op.drop_index(batch_op.f('ix_permits_issuer_id'))
        batch_op.drop_index(batch_op.f('ix_permits_activity_id'))

    op.drop_table('permits')
    with op.batch_alter_table('observations', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_observations_zone_id'))
        batch_op.drop_index(batch_op.f('ix_observations_person_id'))
        batch_op.drop_index(batch_op.f('ix_observations_at'))
        batch_op.drop_index(batch_op.f('ix_observations_activity_id_at'))

    op.drop_table('observations')
    with op.batch_alter_table('near_misses', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_near_misses_zone_id'))
        batch_op.drop_index(batch_op.f('ix_near_misses_reported_by'))
        batch_op.drop_index(batch_op.f('ix_near_misses_at'))
        batch_op.drop_index(batch_op.f('ix_near_misses_activity_id'))

    op.drop_table('near_misses')
    with op.batch_alter_table('learning_reads', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_learning_reads_person_id'))

    op.drop_table('learning_reads')
    with op.batch_alter_table('lab_panels', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_lab_panels_person_id'))

    op.drop_table('lab_panels')
    with op.batch_alter_table('inspection_checks', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_inspection_checks_inspection_id'))

    op.drop_table('inspection_checks')
    with op.batch_alter_table('incidents', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_incidents_zone_id'))
        batch_op.drop_index(batch_op.f('ix_incidents_reported_by'))
        batch_op.drop_index(batch_op.f('ix_incidents_at'))
        batch_op.drop_index(batch_op.f('ix_incidents_activity_id'))

    op.drop_table('incidents')
    with op.batch_alter_table('hazard_reports', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_hazard_reports_zone_id'))
        batch_op.drop_index(batch_op.f('ix_hazard_reports_reported_by'))
        batch_op.drop_index(batch_op.f('ix_hazard_reports_at'))
        batch_op.drop_index(batch_op.f('ix_hazard_reports_activity_id'))

    op.drop_table('hazard_reports')
    with op.batch_alter_table('gangs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_gangs_foreman_id'))

    op.drop_table('gangs')
    with op.batch_alter_table('fitness_outcomes', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_fitness_outcomes_person_id'))
        batch_op.drop_index(batch_op.f('ix_fitness_outcomes_decided_by'))

    op.drop_table('fitness_outcomes')
    with op.batch_alter_table('clinic_visits', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_clinic_visits_zone_id_at'))
        batch_op.drop_index(batch_op.f('ix_clinic_visits_person_id'))
        batch_op.drop_index(batch_op.f('ix_clinic_visits_clinic_id'))
        batch_op.drop_index(batch_op.f('ix_clinic_visits_at'))

    op.drop_table('clinic_visits')
    with op.batch_alter_table('check_ins', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_check_ins_shift_id'))

    op.drop_table('check_ins')
    with op.batch_alter_table('audit_entries', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_audit_entries_at'))
        batch_op.drop_index(batch_op.f('ix_audit_entries_actor_id'))

    op.drop_table('audit_entries')
    with op.batch_alter_table('activity_hazards', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_activity_hazards_hazard_id'))

    op.drop_table('activity_hazards')
    with op.batch_alter_table('actions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_actions_source_kind_source_id'))
        batch_op.drop_index(batch_op.f('ix_actions_owner_id'))

    op.drop_table('actions')
    with op.batch_alter_table('absences', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_absences_person_id'))

    op.drop_table('absences')
    with op.batch_alter_table('warning_records', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_warning_records_zone_id'))
        batch_op.drop_index(batch_op.f('ix_warning_records_opened_at'))

    op.drop_table('warning_records')
    with op.batch_alter_table('people', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_people_role'))
        batch_op.drop_index(batch_op.f('ix_people_employer_id'))
        batch_op.drop_index(batch_op.f('ix_people_camp_zone_id'))

    op.drop_table('people')
    with op.batch_alter_table('learning_items', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_learning_items_source_kind_source_id'))
        batch_op.drop_index(batch_op.f('ix_learning_items_draft_id'))

    op.drop_table('learning_items')
    with op.batch_alter_table('inspections', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_inspections_zone_id'))
        batch_op.drop_index(batch_op.f('ix_inspections_source_kind_source_id'))

    op.drop_table('inspections')
    with op.batch_alter_table('feed_readings', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_feed_readings_zone_id'))
        batch_op.drop_index(batch_op.f('ix_feed_readings_feed_id_zone_id_at'))

    op.drop_table('feed_readings')
    with op.batch_alter_table('clinics', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_clinics_zone_id'))

    op.drop_table('clinics')
    with op.batch_alter_table('camp_tickets', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_camp_tickets_zone_id'))

    op.drop_table('camp_tickets')
    with op.batch_alter_table('activities', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_activities_lower_hazard_alternative_id'))
        batch_op.drop_index(batch_op.f('ix_activities_competency_id'))

    op.drop_table('activities')
    with op.batch_alter_table('zones', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_zones_parent_id'))

    op.drop_table('zones')
    op.drop_table('site_clocks')
    op.drop_table('shifts')
    op.drop_table('settings')
    op.drop_table('hazards')
    op.drop_table('feeds')
    op.drop_table('employers')
    op.drop_table('competencies')
    with op.batch_alter_table('ai_images', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_ai_images_subject_id'))

    op.drop_table('ai_images')
    with op.batch_alter_table('ai_drafts', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_ai_drafts_kind_subject_kind_subject_id_prompt_version_language'))

    op.drop_table('ai_drafts')
