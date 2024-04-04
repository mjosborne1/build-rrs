import json
import unittest
import fetcher
import lighter
import helpers
import os
from fhirclient.models import valueset as vs
from fhirpathpy import evaluate

endpoint = 'https://r4.ontoserver.csiro.au/fhir'

##infiledefault=os.path.join(homedir,"data","rrs","in","xray-test.tsv")

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
    def test_get_bilateral_procedures(self):
        """
        Check the bilateral procedure function
        """
        # Check the bilateral procedure function
        bilateral_procs = fetcher.get_bilateral_procedures()
        # Look for X-ray of both ankles (procedure)
        self.assertIn("425703002",bilateral_procs)
        # Check that X-ray of left ankle (procedure) is not in the bilateral procs data
        self.assertNotIn("426420006",bilateral_procs)
    def test_get_procedures_without_contrast(self):
        """
        Check procedures without contrast function
        """
        procs = fetcher.get_procedures_without_contrast()
        # Look for CT Abdo without contrast
        self.assertIn("1187246003",procs)
        # Check that CT Abdo is not in this list
        self.assertNotIn("169070004",procs)


class TestLighter(unittest.TestCase):  
        
    def test_build_valueset(self):
        """
        Test that build_valueset creates a json file with a consistent concept
        """
        # Set up fhir client to test the ValueSet against a server
        smart=None
        if (endpoint != ""):
            smart = lighter.create_client(endpoint)
        infile = os.path.join('.','test_data','rrs.txt')
        outfile = os.path.join('.','test_data','vs','service.json')
        template = os.path.join('.','templates','ValueSet-radiology-services-template.json')
        status = lighter.build_valueset(0,template,infile,outfile,smart)
        # Check that the ValueSet was created on the server
        self.assertEqual(status,201)
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
        smart=None
        if (endpoint != ""):
            smart = lighter.create_client(endpoint)
        infile = os.path.join('.','test_data','rrs.txt')
        outdir=os.path.join('.','test_data','cm')
        status = lighter.build_concept_map(infile,outdir,smart)
         # Check that the ValueSet was created on the server
        self.assertEqual(status,201)
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