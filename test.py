import json
import unittest
import fetcher
import lighter
import helpers
import os
from fhirclient.models import valueset as vs
from fhirpathpy import evaluate

class TestFetcher(unittest.TestCase):
    def test_get_valueset(self):
        """
        Test that get valueset returns json and a left sided concept is in the Valueset
        """
        data = fetcher.get_body_structures("left")
        # Check that we get an object
        self.assertIsInstance(data,object)
        # Look for Structure of left zygomatic bone
        self.assertIn("787058006",data)
        # Check that an observation/finding concept is not in the data
        self.assertNotIn("225403000",data)      


class TestLighter(unittest.TestCase):  
        
    def test_build_valueset(self):
        """
        Test that build_valueset creates a json file with a consistent concept
        """
        # Set up fhir client to test the ValueSet against a server

        infile = os.path.join('.','test_data','rrs.txt')
        outfile = os.path.join('.','test_data','vs','service.json')
        template = os.path.join('.','templates','ValueSet-radiology-services-template.json')
        lighter.build_valueset(0,template,infile,outfile)
        with open(outfile) as fh:
            data =  json.load(fh)
        
        # Check that we get a ValueSet object
        self.assertEqual(data["resourceType"],"ValueSet")

        # Test for a specific concept we know is in the ValueSet
        concepts = evaluate(data,"compose.include.concept")
        self.assertIn({"code":"961000087109"},concepts)

        # Test that the ValueSet resource is Valid        
        validation_status= helpers.validate_resource(data,"ValueSet")
        self.assertEqual(validation_status,200)


    def test_build_conceptmap(self):
        """
        Test that the concept map file builds correctly
        """
        infile = os.path.join('.','test_data','rrs.txt')
        outdir=os.path.join('.','test_data','cm')
        lighter.build_concept_map(infile,outdir)
        outfile = os.path.join('.','test_data','cm','conceptmap.json')
        with open(outfile) as fh:
            data =  json.load(fh)
        # Test that concept map data is a resource of type ConceptMap
        self.assertEqual(data["resourceType"],"ConceptMap")
         # Test that the ConceptMap resource is Valid        
        validation_status= helpers.validate_resource(data,"ConceptMap")
        self.assertEqual(validation_status,200)

if __name__ == '__main__':
    unittest.main()