from pyld import jsonld
import json

doc = {
    "http://schema.org/name": "Manu Sporny",
    "http://schema.org/url": {"@id": "http://manu.sporny.org/"},
    "http://schema.org/image": {"@id": "http://manu.sporny.org/images/manu.png"}
}

context = {
    "name": "http://schema.org/name",
    "homepage": {"@id": "http://schema.org/url", "@type": "@id"},
    "image": {"@id": "http://schema.org/image", "@type": "@id"}
}

# compact a document according to a particular context
# see: https://json-ld.org/spec/latest/json-ld/#compacted-document-form
compacted = jsonld.compact(doc, context)

print(json.dumps(compacted, indent=2))
# Output:
# {
#   "@context": {...},
#   "image": "http://manu.sporny.org/images/manu.png",
#   "homepage": "http://manu.sporny.org/",
#   "name": "Manu Sporny"
# }

# compact using URLs
jsonld.compact('http://example.org/doc', 'http://example.org/context')

# expand a document, removing its context
# see: https://json-ld.org/spec/latest/json-ld/#expanded-document-form
expanded = jsonld.expand(compacted)

print(json.dumps(expanded, indent=2))
# Output:
# [{
#   "http://schema.org/image": [{"@id": "http://manu.sporny.org/images/manu.png"}],
#   "http://schema.org/name": [{"@value": "Manu Sporny"}],
#   "http://schema.org/url": [{"@id": "http://manu.sporny.org/"}]
# }]

# expand using URLs
jsonld.expand('http://example.org/doc')

# flatten a document
# see: https://json-ld.org/spec/latest/json-ld/#flattened-document-form
flattened = jsonld.flatten(doc)
# all deep-level trees flattened to the top-level

# frame a document
# see: https://json-ld.org/spec/latest/json-ld-framing/#introduction
framed = jsonld.frame(doc, frame)
# document transformed into a particular tree structure per the given frame

# normalize a document using the RDF Dataset Normalization Algorithm
# (URDNA2015), see: https://json-ld.github.io/normalization/spec/
normalized = jsonld.normalize(
    doc, {'algorithm': 'URDNA2015', 'format': 'application/n-quads'})
# normalized is a string that is a canonical representation of the document
# that can be used for hashing, comparison, etc.

