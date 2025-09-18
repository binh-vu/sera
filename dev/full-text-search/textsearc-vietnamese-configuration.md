Unaccent is a very important function to strip diacritics (accents) from characters. This is especially useful in Vietnamese, where many characters have diacritics that can affect search results.

```sql
CREATE EXTENSION IF NOT EXISTS unaccent;

SELECT unaccent('Hôtel');
SELECT unaccent('Nhiều địa phương cấm người ra đường khi bão Noru đổ bộ');
```

You need to understand how dictionary work in PostgreSQL. This is essential for configuring full-text search for Vietnamese as some dictionaries can only placed at the end such as english stem (with Snowball algorithm) as it recognizes everything. Some dictionaries that act as filters such as unaccent can be placed at the beginning because it can modify the token without recognizing/consuming it.

One thing I do not know is the lowercase processing. It seems that this does lowercase processing automatically. But I do not understand what dictionary or process does it exactly.

```sql
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
```
