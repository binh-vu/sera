from __future__ import annotations


class MultiLingualString(str):
    lang: str
    lang2value: dict[str, str]

    def __new__(cls, lang2value: dict[str, str], lang):
        object = str.__new__(cls, lang2value[lang])
        object.lang = lang
        object.lang2value = lang2value
        return object

    def as_lang(self, lang: str) -> str:
        return self.lang2value[lang]

    def as_lang_default(self, lang: str, default: str) -> str:
        return self.lang2value.get(lang, default)

    def has_lang(self, lang: str) -> bool:
        return lang in self.lang2value

    def is_empty(self):
        return all(value == "" for value in self.lang2value.values())

    @staticmethod
    def en(label: str):
        return MultiLingualString(lang2value={"en": label}, lang="en")

    @staticmethod
    def from_dict(obj: dict):
        return MultiLingualString(obj["lang2value"], obj["lang"])

    def to_dict(self):
        return {"lang2value": self.lang2value, "lang": self.lang}

    def to_tuple(self):
        return self.lang2value, self.lang

    def __getnewargs__(self) -> tuple[dict[str, str], str]:  # type: ignore
        return self.lang2value, self.lang
