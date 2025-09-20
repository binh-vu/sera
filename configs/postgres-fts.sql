-- Setup configuration that seems works for full text search

CREATE EXTENSION IF NOT EXISTS unaccent;

CREATE TEXT SEARCH CONFIGURATION public.sevi ( COPY = pg_catalog.english );

CREATE TEXT SEARCH DICTIONARY sera_lowercase_rm_stopwords (
    TEMPLATE = pg_catalog.simple,
    STOPWORDS = english
);

CREATE TEXT SEARCH DICTIONARY english_stem (
    TEMPLATE = snowball,
    Language = english,
    StopWords = english
);

ALTER TEXT SEARCH CONFIGURATION public.sevi
   ALTER MAPPING
      FOR word, numword, hword, numhword, hword_part, hword_numpart
      WITH unaccent, english_stem;

-- Setup for Trigram search
-- unaccent need to be patched to mark it as immutable to be used in index
-- https://stackoverflow.com/questions/11005036/does-postgresql-support-accent-insensitive-collations/11007216#11007216

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE OR REPLACE FUNCTION public.immutable_unaccent(regdictionary, text)
  RETURNS text
  LANGUAGE c IMMUTABLE PARALLEL SAFE STRICT AS
'$libdir/unaccent', 'unaccent_dict';

CREATE OR REPLACE FUNCTION public.f_unaccent(text)
  RETURNS text
  LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
RETURN public.immutable_unaccent(regdictionary 'public.unaccent', $1);