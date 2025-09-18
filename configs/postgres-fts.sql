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
