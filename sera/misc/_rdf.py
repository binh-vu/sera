from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from typing import Iterable

from rdflib import OWL, RDF, RDFS, SKOS, XSD, Graph, URIRef
from rdflib.namespace import NamespaceManager
from sm.typing import IRI, InternalID, RelIRI


@dataclass
class SingleNS:
    alias: str
    namespace: str

    def __post_init__(self):
        assert self.namespace.endswith("/") or self.namespace.endswith(
            "#"
        ), f"Namespace {self.namespace} should end with / or #"

    def term(self, name: str) -> Term:
        return Term(self, name)

    def id(self, uri: IRI | URIRef) -> str:
        assert uri.startswith(self.namespace), (uri, self.namespace)
        return uri[len(self.namespace) :]

    def uri(self, name: InternalID) -> URIRef:
        return URIRef(self.namespace + name)

    def uristr(self, name: InternalID) -> IRI:
        return self.namespace + name

    def __getattr__(self, name: InternalID):
        return self.alias + ":" + name

    def __getitem__(self, name: InternalID):
        return self.alias + ":" + name

    def __contains__(self, uri: IRI | URIRef) -> bool:
        return uri.startswith(self.namespace)

    def rel2abs(self, reluri: RelIRI) -> URIRef:
        return URIRef(self.namespace + reluri.split(":")[1])

    def abs2rel(self, uri: IRI | URIRef) -> RelIRI:
        return self.alias + ":" + self.id(uri)


@dataclass
class Term:
    ns: SingleNS
    name: str
    reluri: str = field(init=False)
    uri: URIRef = field(init=False)

    def __post_init__(self):
        self.reluri = self.ns[self.name]
        self.uri = self.ns.uri(self.name)
