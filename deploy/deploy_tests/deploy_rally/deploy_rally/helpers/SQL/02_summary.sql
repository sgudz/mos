-- Materialized View: tests

-- DROP MATERIALIZED VIEW tests;

CREATE MATERIALIZED VIEW tests AS 
 SELECT DISTINCT d.name AS cluster_uuid,
    t.uuid AS task_uuid,
    t.status,
    "substring"(r.key ->> 'name'::text, '^[A-Z][a-z]+'::text) AS component,
    r.key ->> 'name'::text AS jobname,
    length(t.verification_log) > 0 AS bad_task,
    r.key #>> '{kw,runner,times}'::text[] AS times,
    r.key #>> '{kw,runner,concurrency}'::text[] AS concurrency,
    e.count AS errors
   FROM tasks t
     LEFT JOIN ( SELECT task_results.task_uuid,
            task_results.key::json AS key,
            json_array_elements(task_results.data::json -> 'raw'::text) AS data
           FROM task_results) r ON t.uuid::text = r.task_uuid::text
     LEFT JOIN ( SELECT r_1.task_uuid AS uuid,
            count(1) AS count,
            json_array_length(r_1.data -> 'error'::text) > 0 AS errors
           FROM ( SELECT task_results.task_uuid,
                    json_array_elements(task_results.data::json -> 'raw'::text) AS data
                   FROM task_results) r_1
          GROUP BY r_1.task_uuid, json_array_length(r_1.data -> 'error'::text) > 0) e ON r.task_uuid::text = e.uuid::text AND e.errors = true
     LEFT JOIN deployments d ON d.uuid = t.deployment_uuid::bpchar
;

ALTER TABLE tests OWNER TO rally;

-- Materialized View: test_timings

-- DROP MATERIALIZED VIEW test_timings;

CREATE MATERIALIZED VIEW test_timings AS 
 SELECT r.task_uuid::character(36) AS task_uuid,
    min((r.data ->> 'duration')::numeric) AS min,
    avg((r.data ->> 'duration')::numeric) AS avg,
    max((r.data ->> 'duration')::numeric) AS max
   FROM ( SELECT task_results.task_uuid,
            json_array_elements(task_results.data::json -> 'raw') AS data
           FROM task_results) r
  WHERE json_array_length(r.data -> 'error') = 0
  GROUP BY r.task_uuid
;

ALTER TABLE test_timings OWNER TO rally;

-- Function: update_test_results()

-- DROP FUNCTION update_test_results();

CREATE OR REPLACE FUNCTION update_test_results()
  RETURNS trigger AS
$BODY$
BEGIN
REFRESH MATERIALIZED VIEW tests;
REFRESH MATERIALIZED VIEW test_timings;
RETURN null;
END
$BODY$
  LANGUAGE plpgsql;
ALTER FUNCTION update_test_results() OWNER TO rally;

-- Trigger: update_test_results on task_results

-- DROP TRIGGER update_test_results ON task_results;

CREATE TRIGGER update_test_results
  AFTER INSERT OR DELETE OR TRUNCATE
  ON task_results
  FOR EACH STATEMENT
  EXECUTE PROCEDURE update_test_results();
