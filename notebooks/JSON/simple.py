import json
import zipfile
from rdflib import Graph, plugin
from rdflib.serializer import Serializer

# load a single extracted json file
json_filename = "Y:\\data\\JSON_LD\\00acb9f0-1640-4f8c-89ef-d857e1428be0.json"
json_file = open(json_filename)
my_object = json.load(json_file)

print(json_filename, "\n", my_object)

# load a single json file from a openLCA JSON_LD zip
json_zip_filename = "Y:\\data\\JSON_LD\\ecoinvent_36_lcia_methods.zip"
zip_file = zipfile.ZipFile(json_zip_filename, 'r')
name_list = zip_file.namelist()
json_filename = name_list[3]
my_file_contents = zip_file.read(json_filename)
my_object = json.loads(my_file_contents)

print(json_filename, "\n", my_object)

# load a collection of linked JSON files
testrdf = ''' 
@prefix dc: <http://purl.org/dc/terms/> .
<http://example.org/about>
    dc:title "Someone's Homepage"@en .
'''
g = Graph().parse(data=testrdf, format='n3')
print(g.serialize(format='json-ld', indent=4))
context = {"@vocab": "http://purl.org/dc/terms/", "@language": "en"}
print(g.serialize(format='json-ld', context=context, indent=4))

json_db = {}
for name in name_list:
    raw = zip_file.read(name)
    json_db[name] = json.loads(raw)

context = json_db['context.json']
context['@vocab']
