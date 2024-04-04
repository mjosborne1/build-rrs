"""
   fhir lighter library for building the fhir artefacts from the TSV input file 
"""

import json
import numpy as np
import pandas as pd
from fhirclient.models import valueset,conceptmap
from fhirclient import client
from helpers import path_exists 
import os

## create_vs_filepath
#     Create and return an array of valueset file names
def create_vs_filepath(outdir):
    if not path_exists(outdir):       
        return []    
    vs_filepath = [              
        os.path.join(outdir,"ValueSet-Service.json"),
        os.path.join(outdir,"ValueSet-Procedure.json"),
        os.path.join(outdir,"ValueSet-Bodysite.json"),
        os.path.join(outdir,"ValueSet-Laterality.json"),         
        os.path.join(outdir,"ValueSet-Contrast.json")         
    ]    
    return vs_filepath

## get_template_files
#     Create and return an array of ValueSet template files
def get_template_files():
    template_filepath = [              
        os.path.join('.','templates','ValueSet-radiology-services-template.json'),
        os.path.join('.','templates','ValueSet-radiology-procedure-template.json'),
        os.path.join('.','templates','ValueSet-radiology-body-structure-template.json'),
        os.path.join('.','templates','ValueSet-radiology-laterality-template.json'),     
        os.path.join('.','templates','ValueSet-radiology-contrast-template.json')         
    ]    
    return template_filepath

## check_numeric
#    return true if the pandas frame is numeric and not a float else return false
def is_numeric(value):
    if pd.isna(value):
        return False
    elif isinstance(value, np.float64):
        print("value is a float {0}".format(value))
        return False
    else:
        return True
    

def create_client(endpoint):
    settings = {
        'app_id': 'build-rrs',
        'api_base': endpoint
    }
    smart = client.FHIRClient(settings=settings)
    return smart
   

def build_valueset(col,template,infile,outfile,smart):
    """
    Build a FHIR ValueSet based on the input file, template file and output to outfile
    col is an integer that describes which column 0..3 in the input file to work from
    """
    df=pd.read_csv(infile,sep='\t',dtype={'Service':str,'Procedure':str,'Site':str,'Laterality':str,'Contrast':str})
   
    # Get values from the required column
    concepts=df.iloc[:,col].astype(str).unique()
    # Get the ValueSet template as a ValueSet object
    # Read the FHIR ValueSet JSON file into a Python dictionary
    with open(template) as f:
       meta = json.load(f)

    # Create a FHIR ValueSet resource object
    vs = valueset.ValueSet()
    # vs.id = meta.get('id')
    vs.status = meta.get('status')
    vs.name = meta.get('name')
    vs.title = meta.get('title')
    vs.description = meta.get('description')
    vs.publisher = meta.get('publisher')
    vs.version = meta.get('version')
    vs.url = meta.get('url')
#    vs.contact = meta.get('contact')
    vs.copyright = meta.get('copyright')
    vs.experimental = meta.get('experimental')

    # Add the concepts to the ValueSet
    vs.compose = valueset.ValueSetCompose()
    vs.compose.include = [valueset.ValueSetComposeInclude()]
    vs.compose.include[0].system = "http://snomed.info/sct"
    vs.compose.include[0].concept = []   

    for concept in concepts:
        if concept.isdigit(): 
            include_concept = valueset.ValueSetComposeIncludeConcept()
            include_concept.code = str(concept)      
            vs.compose.include[0].concept.append(include_concept)

    # Export the Valueset to file for manual review
    with open(outfile, "w") as f:
        json.dump(vs.as_json(), f, indent=2)
    # Cleanup
    df.drop(df.index, inplace=True)
    if smart != None:
        response = vs.create(smart.server)
        if response:
            return 201
        else:
            return 500
    else:
        return 200



def build_concept_map(rrsfile,outdir,smart):
    """
    Build a concept map of procedures and other qualifiers in a property/dependsOn style 
    to a radiology service code (fully defined)
    """
    mapfile = os.path.join(outdir,"ConceptMap_RadiologyServices.json")
    df=pd.read_csv(rrsfile,sep='\t',dtype={'Service':str,'Procedure':str,'Site':str,'Laterality':str,'Contrast':str})
    # Read the FHIR ConceptMap JSON file into a Python dictionary
    template =  os.path.join('.','templates','ConceptMap-radiology-services-template.json')
    print("Processing ConceptMap template...{0}".format(template))
    with open(template) as f:
       meta = json.load(f)
     # Create a FHIR ConceptMap resource object
    cm = conceptmap.ConceptMap()
    #cm.id = meta.get('id')
    cm.status = meta.get('status')
    cm.name = meta.get('name')
    cm.title = meta.get('title')
    cm.description = meta.get('description')
    cm.publisher = meta.get('publisher')
    cm.version = meta.get('version')
    cm.url = meta.get('url')
#    cm.contact = meta.get('contact')
    cm.copyright = meta.get('copyright')
    cm.experimental = meta.get('experimental')

    # Add the map group rows 
    cm.group = [ conceptmap.ConceptMapGroup() ]
    cm.group[0].source = "http://snomed.info/sct"
    cm.group[0].target = "http://snomed.info/sct"

    # add map elements
    #    0 : Service (Full code), 1: Procedure, 2: Site , 3: Laterality, 4: Contrast (yes/no)
    elements=[]
    for index, row in df.iterrows():
        if not is_numeric(row['Service']):
            continue
        element = conceptmap.ConceptMapGroupElement()
        element.code = row['Procedure']
        element.target = [conceptmap.ConceptMapGroupElementTarget()]
        element.target[0].code = row['Service']
        element.target[0].equivalence = "equivalent"
        # Check if the subsequent fields contain digits
        idx = 0
        if is_numeric(row['Site']):
            dep = conceptmap.ConceptMapGroupElementTargetDependsOn()
            dep.property = "405813007"  ## Procedure site - direct
            dep.system = "http://snomed.info/sct"
            ## Body structure
            dep.value = row['Site']
            if not isinstance(element.target[0].dependsOn, list):
                element.target[0].dependsOn = []
            element.target[0].dependsOn.append(dep)
        if is_numeric(row['Laterality']):
            dep = conceptmap.ConceptMapGroupElementTargetDependsOn()
            dep.property = "272741003"  ## Body structure laterality
            dep.system = "http://snomed.info/sct"
            dep.value = row['Laterality']
            if not isinstance(element.target[0].dependsOn, list):
                element.target[0].dependsOn = []
            element.target[0].dependsOn.append(dep)
        if is_numeric(row['Contrast']):
            dep = conceptmap.ConceptMapGroupElementTargetDependsOn()
            dep.property = "424361007"  ## yes or no value
            dep.system = "http://snomed.info/sct"
            dep.value = row['Contrast']
            if not isinstance(element.target[0].dependsOn, list):
                element.target[0].dependsOn = []
            element.target[0].dependsOn.append(dep)
        elements.append(element)
    cm.group[0].element = elements
    # Dump the ConceptMap to file for manual review
    with open(mapfile, "w") as f:
        json.dump(cm.as_json(), f, indent=2)
    # Cleanup
    df.drop(df.index, inplace=True)
    if smart != None:
        response = cm.create(smart.server)
        if response:
            return 201
        else:
            return 500
    else:
        return 200

## Mainline
## Output the Valuesets and Conceptmap built from the RRS file    
def run_main(rrsfile,outdir,endpoint):
    smart=None
    if (endpoint != ""):
         smart = create_client(endpoint)
    # Note, the template file order must match the valueset file order
    vs_files=create_vs_filepath(outdir)
    templates=get_template_files()
    for col in range(0,5):
        print("{0} Processing template...{1}".format( col, templates[col]))
        vs = build_valueset(col,templates[col],rrsfile,vs_files[col],smart)        
    cm = build_concept_map(rrsfile,outdir,smart)
   