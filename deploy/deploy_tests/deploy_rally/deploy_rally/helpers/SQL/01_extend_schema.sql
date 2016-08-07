-- Table: cluster_config

-- DROP TABLE cluster_config;

CREATE TABLE cluster_config
(
  id serial NOT NULL,
  uuid character(36) NOT NULL,
  env smallint,
  attributes jsonb NOT NULL DEFAULT '{}'::jsonb,
  network jsonb NOT NULL DEFAULT '{}'::jsonb,
  nodes jsonb NOT NULL DEFAULT '{}'::jsonb,
  fuel jsonb DEFAULT '{}'::jsonb,
  created timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT cluster_config_pkey PRIMARY KEY (uuid)
);
ALTER TABLE cluster_config OWNER TO rally;

-- Materialized View: clusters

-- DROP MATERIALIZED VIEW clusters;

CREATE MATERIALIZED VIEW clusters AS 
 SELECT cluster_config.uuid,
    cluster_config.created,
    cluster_config.env,
    cluster_config.fuel #>> '{fuel_version}'::text[] AS fuelversion,
    "substring"(cluster_config.fuel #>> '{name}'::text[], '[0-9]+$'::text) AS fuelbuild,
    cluster_config.fuel #>> '{mode}'::text[] AS hamode,
    jsonb_array_length(cluster_config.nodes) AS nodecount,
    cluster_config.attributes #>> '{editable,storage,ephemeral_ceph,value}'::text[] AS ephemeralceph,
    cluster_config.attributes #>> '{editable,storage,images_ceph,value}'::text[] AS imagesceph,
    cluster_config.attributes #>> '{editable,storage,objects_ceph,value}'::text[] AS objectsceph,
    cluster_config.attributes #>> '{editable,storage,volumes_ceph,value}'::text[] AS volumesceph,
    cluster_config.attributes #>> '{editable,storage,volumes_lvm,value}'::text[] AS volumeslvm,
    cluster_config.attributes #>> '{editable,provision,method,value}'::text[] AS provisionmethod,
    cluster_config.attributes #>> '{editable,common,debug,value}'::text[] AS enabledebug,
    cluster_config.attributes #>> '{editable,common,nova_quota,value}'::text[] AS usenovaquota,
    cluster_config.attributes #>> '{editable,additional_components,ceilometer,value}'::text[] AS ceilometer,
    cluster_config.attributes #>> '{editable,additional_components,heat,value}'::text[] AS heat,
    cluster_config.attributes #>> '{editable,additional_components,murano,value}'::text[] AS murano,
    cluster_config.attributes #>> '{editable,additional_components,sahara,value}'::text[] AS sahara,
    cluster_config.fuel #>> '{net_provider}'::text[] AS networking,
    cluster_config.attributes #>> '{editable,vlan_splinters,vswitch,value}'::text[] AS vlan,
    cluster_config.network #>> '{networking_parameters,net_l23_provider}'::text[] AS l23,
    cluster_config.network #>> '{networking_parameters,segmentation_type}'::text[] AS networksegmentation
   FROM cluster_config
;

ALTER TABLE clusters OWNER TO rally;

-- Function: update_clusters()

-- DROP FUNCTION update_clusters();

CREATE OR REPLACE FUNCTION update_clusters()
  RETURNS trigger AS
$BODY$
BEGIN
  REFRESH MATERIALIZED VIEW clusters;
  RETURN null;
END
$BODY$
  LANGUAGE plpgsql;
ALTER FUNCTION update_clusters() OWNER TO rally;
COMMENT ON FUNCTION update_clusters() IS 'Updates materialized view "clusters"';

-- Trigger: update_clusters on cluster_config

-- DROP TRIGGER update_clusters ON cluster_config;

CREATE TRIGGER update_clusters
  AFTER INSERT OR DELETE OR TRUNCATE
  ON cluster_config
  FOR EACH STATEMENT
  EXECUTE PROCEDURE update_clusters();
