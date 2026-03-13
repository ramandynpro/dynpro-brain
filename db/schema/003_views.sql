CREATE OR REPLACE VIEW v_person_capability_snapshot AS
SELECT
    p.person_id,
    p.full_name,
    p.current_role,
    p.home_location,
    p.timezone,
    p.profile_last_updated_at,
    p.profile_confidence,
    COUNT(DISTINCT se.evidence_id) AS skill_evidence_count,
    COUNT(DISTINCT ap.project_id) AS project_count,
    MAX(se.updated_at) AS last_skill_update,
    MAX(ap.updated_at) AS last_project_update
FROM person p
LEFT JOIN skill_evidence se ON se.person_id = p.person_id
LEFT JOIN assignment_project ap ON ap.person_id = p.person_id
GROUP BY
    p.person_id,
    p.full_name,
    p.current_role,
    p.home_location,
    p.timezone,
    p.profile_last_updated_at,
    p.profile_confidence;
