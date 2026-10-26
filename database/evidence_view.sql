-- Read-only, scalar-column JDBC projection; no JSONB crosses the Spark JDBC boundary.
CREATE OR REPLACE VIEW disease_evidence AS
SELECT crop,disease_id,name_en,name_ko,scientific_name,ordinality::integer AS feature_no,
 feature->>'category' AS category,feature->>'description' AS description,
 feature->>'source_name' AS source_name,(feature->'url')::text AS source_urls,
 feature->>'location_in_source' AS source_location,
 feature->>'plant_part' AS plant_part,feature->>'growth_stage' AS growth_stage,
 source_conflicts::text AS source_conflicts
FROM (SELECT 'rice'::text AS crop,disease_id,name_en,name_ko,scientific_name,features,source_conflicts FROM rice
 UNION ALL SELECT 'maize',disease_id,name_en,name_ko,scientific_name,features,source_conflicts FROM maize) d,
 jsonb_array_elements(features) WITH ORDINALITY AS f(feature,ordinality);
