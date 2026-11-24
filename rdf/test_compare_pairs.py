"""Exercise the offline export through its public command line."""

import csv
import gzip
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


DIRECTORY = Path(__file__).resolve().parent
WIKIDATA = 'http://www.wikidata.org/entity/'
FIXTURE = '''
@prefix ex: <https://example.org/> .
@prefix dct: <http://purl.org/dc/terms/> .
@prefix dwciri: <http://rs.tdwg.org/dwc/iri/> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix schema: <https://schema.org/> .
@prefix sosa: <http://www.w3.org/ns/sosa/> .
@prefix wd: <http://www.wikidata.org/entity/> .
@prefix wdt: <http://www.wikidata.org/prop/direct/> .
ex:alpha a sosa:Sample ; prov:wasDerivedFrom ex:plantA .
ex:beta a sosa:Sample ; prov:wasDerivedFrom ex:plantB .
[] dct:subject ex:plantA ; dwciri:toTaxon wd:Q1 .
[] dct:subject ex:plantB ; dwciri:toTaxon wd:Q2 .
[] prov:used ex:alpha ; dct:relation ex:fileA .
[] prov:used ex:beta ; dct:relation ex:fileB .
ex:featureA prov:wasDerivedFrom ex:fileA ; dct:identifier "1" .
ex:featureB prov:wasDerivedFrom ex:fileB ; dct:identifier "1" .
[] a sosa:Observation ; sosa:observedProperty wd:Q500256 ; sosa:hasFeatureOfInterest ex:featureA ;
   prov:used ex:software ; sosa:usedProcedure ex:methodA ; sosa:hasResult ex:resultA .
[] a sosa:Observation ; sosa:observedProperty wd:Q500256 ; sosa:hasFeatureOfInterest ex:featureB ;
   prov:used ex:software ; sosa:usedProcedure ex:methodB ; sosa:hasResult ex:resultB .
ex:resultA wdt:P235 "AAAAAAAAAAAAAA-BBBBBBBBBB-C" ;
    prov:wasDerivedFrom [ rdfs:seeAlso wd:Q10 ; wdt:P235 "AAAAAAAAAAAAAA-BBBBBBBBBB-C" ],
                        [ rdfs:seeAlso wd:Q11 ; wdt:P235 "AAAAAAAAAAAAAA-DDDDDDDDDD-C" ],
                        [ rdfs:seeAlso wd:Q12 ; wdt:P235 "EEEEEEEEEEEEEE-BBBBBBBBBB-C" ] .
ex:resultB schema:identifier [ schema:propertyID "InChIKey connectivity block" ; schema:value "AAAAAAAAAAAAAA" ] ;
    prov:wasDerivedFrom [ rdfs:seeAlso wd:Q10 ; wdt:P235 "AAAAAAAAAAAAAA-BBBBBBBBBB-C" ],
                        [ rdfs:seeAlso wd:Q13 ] .
'''


class PairEvidenceTest(unittest.TestCase):
    def test_associations_follow_each_raw_file_and_compare_only_the_linked_keys(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            for trial in ('first', 'second'):
                for pipeline in ('enpkg', 'flock'):
                    with gzip.open(directory / f'{pipeline}-{trial}.ttl.gz', 'wt', encoding='utf-8') as graph:
                        graph.write(FIXTURE if pipeline == 'enpkg' else FIXTURE.replace('wd:Q13', 'wd:Q14'))
            report = directory / 'report'
            subprocess.run([sys.executable, DIRECTORY / 'compare_pairs.py', '--input-dir', directory,
                            '--output-dir', report], check=True, timeout=30)
            with (report / 'pair-evidence.tsv').open(encoding='utf-8', newline='') as evidence:
                rows = list(csv.DictReader(evidence, delimiter='\t'))
            for trial in ('first', 'second'):
                for pipeline, exclusive in [('enpkg', 'Q13'), ('flock', 'Q14')]:
                    expected = [
                        ('Q1', 'Q10', 'methodA', 'full-key', 'both'),
                        ('Q1', 'Q11', 'methodA', 'connectivity-only', 'both'),
                        ('Q1', 'Q12', 'methodA', 'unverified', 'both'),
                        ('Q2', 'Q10', 'methodB', 'connectivity-only', 'both'),
                        ('Q2', exclusive, 'methodB', 'unverified', pipeline + '-only'),
                    ]
                    self.assertCountEqual([
                        (row['taxon'], row['chemical'], row['software'], row['procedure'], row['strength'], row['membership'])
                        for row in rows if row['trial'] == trial and row['pipeline'] == pipeline
                    ], [(WIKIDATA + taxon, WIKIDATA + chemical, 'https://example.org/software',
                         'https://example.org/' + method, strength, membership)
                        for taxon, chemical, method, strength, membership in expected])
