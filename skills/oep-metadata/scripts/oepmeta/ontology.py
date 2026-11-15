"""Offline frozen RDF/OWL index; never dereference ontology imports or IDs."""

import re
from pathlib import Path

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS

from .common import WorkflowError, file_hash, load_json, now, write_json

IAO_DEFINITION = URIRef("http://purl.obolibrary.org/obo/IAO_0000115")
SYNONYM_PREDICATES = [SKOS.altLabel, URIRef("http://www.geneontology.org/formats/oboInOwl#hasExactSynonym"),
                      URIRef("http://www.geneontology.org/formats/oboInOwl#hasRelatedSynonym"),
                      URIRef("http://purl.obolibrary.org/obo/IAO_0000118")]


def _texts(graph, subject, predicate):
    values = [item for item in graph.objects(subject, predicate) if isinstance(item, Literal)]
    return sorted({str(item) for item in values if item.language in (None, "en")}) or sorted({str(item) for item in values})


def build_index(source, output, version):
    """Index a local, caller-frozen RDF file. Imports remain offline references.

    JSON-LD is deliberately excluded because remote contexts can dereference
    network resources. Other RDF parsers are used with a local source only.
    """
    source = Path(source).resolve(strict=True)
    if not source.is_file() or not isinstance(version, str) or not version.strip():
        raise WorkflowError("Provide a local RDF source and explicit ontology release/version")
    formats = {".ttl": "turtle", ".owl": "xml", ".rdf": "xml", ".xml": "xml", ".nt": "nt", ".n3": "n3"}
    if source.suffix.lower() not in formats:
        raise WorkflowError("Supported frozen ontology formats: .ttl, .owl, .rdf, .xml, .nt, .n3")
    raw = source.read_bytes()
    if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise WorkflowError("RDF with XML DTD/entities is not accepted")
    graph = Graph()
    graph.parse(data=raw, format=formats[source.suffix.lower()], publicID=source.as_uri())
    subjects = set(graph.subjects(RDF.type, OWL.Class)) | set(graph.subjects(RDF.type, RDFS.Class)) | set(graph.subjects(RDFS.label, None))
    terms = {}
    for subject in sorted(subjects, key=str):
        if not isinstance(subject, URIRef):
            continue
        labels = _texts(graph, subject, RDFS.label)
        if not labels:
            labels = _texts(graph, subject, SKOS.prefLabel)
        if not labels:
            continue
        deprecated = any(str(value).lower() in ("true", "1") for value in graph.objects(subject, OWL.deprecated))
        definitions = _texts(graph, subject, IAO_DEFINITION) + _texts(graph, subject, SKOS.definition)
        terms[str(subject)] = {"id": str(subject), "labels": labels, "definitions": sorted(set(definitions)),
                               "synonyms": sorted({text for predicate in SYNONYM_PREDICATES for text in _texts(graph, subject, predicate)}),
                               "deprecated": deprecated,
                               "parents": sorted(str(value) for value in graph.objects(subject, RDFS.subClassOf) if isinstance(value, URIRef)),
                               "replaced_by": sorted(str(value) for value in graph.objects(subject, URIRef("http://purl.obolibrary.org/obo/IAO_0100001")))}
    aliases = {}
    for uri in terms:
        match = re.search(r"[/#](OEO_\d{8})$", uri)
        if match:
            aliases.setdefault(match.group(1), []).append(uri)
    # A compact ID is usable only when it identifies a unique indexed URI.
    aliases = {alias: uris[0] for alias, uris in aliases.items() if len(uris) == 1}
    index = {"version": version, "source": source.name, "source_sha256": file_hash(source), "built_at": now(),
             "term_count": len(terms), "imports_followed": False, "imports": sorted(str(value) for value in graph.objects(None, OWL.imports)),
             "limitations": ["Only the supplied RDF file is indexed; imported module terms require a merged release or separately frozen input."],
             "aliases": aliases, "terms": terms}
    write_json(output, index)
    return index


def _load(index):
    value = load_json(index) if isinstance(index, (str, Path)) else index
    if not isinstance(value, dict) or not isinstance(value.get("terms"), dict):
        raise WorkflowError("Expected a frozen ontology index with terms")
    return value


def lookup(index, identifier):
    value = _load(index)
    # Full URIs require exact membership. Only compact IDs may resolve through
    # aliases derived from actual source terms, never fabricated URI suffixes.
    identifier = str(identifier)
    if identifier in value["terms"]:
        return value["terms"][identifier]
    if re.fullmatch(r"OEO[_:]\d{8}", identifier):
        uri = value.get("aliases", {}).get(identifier.replace(":", "_"))
        return value["terms"].get(uri)
    return None


def search(index, query, limit=10):
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise WorkflowError("Ontology search limit must be 1..100")
    query = str(query).strip().casefold()
    if not query:
        raise WorkflowError("Ontology search query cannot be blank")
    value = _load(index)
    tokens = set(re.findall(r"\w+", query))
    results = []
    for record in value["terms"].values():
        label_texts = [text.casefold() for text in record.get("labels", []) + record.get("synonyms", [])]
        definition_text = " ".join(record.get("definitions", [])).casefold()
        score = max([100 if query == text else 50 if query in text else len(tokens & set(re.findall(r"\w+", text))) * 5 for text in label_texts] or [0])
        if query in record["id"].casefold():
            score = max(score, 100)
        score += len(tokens & set(re.findall(r"\w+", definition_text)))
        if score:
            results.append({**record, "score": score, "ontology_version": value["version"], "source_sha256": value["source_sha256"]})
    results.sort(key=lambda record: (record.get("deprecated", False), -record["score"], record["id"]))
    return results[:limit]
