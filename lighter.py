"""
   fhir lighter library for building the fhir artefacts from the TSV input file 
"""

""" from fhir.resources.valueset import ValueSet
from fhir.resources.conceptmap import ConceptMap """

import json
import numpy as np
import pandas as pd
from fhirclient.models import valueset,conceptmap
from helpers import path_exists 
import os


def create_filepath(outdir):
    if not path_exists(outdir):       
        return []    
    filepath = [              
        os.path.join(outdir,"service.json"),
        os.path.join(outdir,"procedure.json"),
        os.path.join(outdir,"bodysite.json"),
        os.path.join(outdir,"laterality.json")         
    ]    
    return filepath


def get_template_files():
    filepath = [              
        os.path.join('.','templates','ValueSet-radiology-services-template.json'),
        os.path.join('.','templates','ValueSet-radiology-procedure-template.json'),
        os.path.join('.','templates','ValueSet-radiology-body-structure-template.json'),
        os.path.join('.','templates','ValueSet-radiology-laterality-template.json')         
    ]    
    return filepath

## check_numeric
#    return true if the pandas frame is numeric and not a float else return false
def check_numeric(value):
    if pd.isna(value) or not pd.isnull(value):
        return False
    elif isinstance(value, np.float64):
        print("value is a float {0}".format(value))
        return False
    else:
        return True
    

def build_valueset(col,template,infile,outfile):
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
    vs.status = meta.get('status')
    vs.name = meta.get('name')
    vs.title = meta.get('title')
    vs.description = meta.get('description')
    vs.publisher = meta.get('publisher')
    vs.version = meta.get('version')
    vs.url = meta.get('url')    

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

    # Export the Valueset to file
    with open(outfile, "w") as f:
        json.dump(vs.as_json(), f, indent=2)
    
    # Cleanup
    df.drop(df.index, inplace=True) 


def build_concept_map(rrsfile,outdir):
    mapfile = os.path.join(outdir,"conceptmap.json")
    df=pd.read_csv(rrsfile,sep='\t',dtype={'Service':str,'Procedure':str,'Site':str,'Laterality':str,'Contrast':str})
    # Read the FHIR ConceptMap JSON file into a Python dictionary
    template =  os.path.join('.','templates','ConceptMap-radiology-services-template.json')
    print("Processing ConceptMap template...{0}".format(template))
    with open(template) as f:
       meta = json.load(f)
     # Create a FHIR ConceptMap resource object
    cm = conceptmap.ConceptMap()
    cm.status = meta.get('status')
    cm.name = meta.get('name')
    cm.title = meta.get('title')
    cm.description = meta.get('description')
    cm.publisher = meta.get('publisher')
    cm.version = meta.get('version')
    cm.url = meta.get('url')

    # Add the map group rows 
    cm.group = [ conceptmap.ConceptMapGroup() ]
    cm.group[0].source = "http://snomed.info/sct"
    cm.group[0].target = "http://snomed.info/sct"

    # add map elements
    #    0 : Service (Full code), 1: Procedure, 2: Site , 3: Laterality, 4: Contrast
    elements=[]
    for index, row in df.iterrows():
        if check_numeric(row['Service']):
            continue
        element = conceptmap.ConceptMapGroupElement()
        element.code = row['Procedure']
        element.target = [conceptmap.ConceptMapGroupElementTarget()]
        element.target[0].code = row['Service']
        element.target[0].equivalence = "equivalent"
        # Check if the subsequent fields contain digits
        idx = 0
        if check_numeric(row['Site']):
            element.target[0].dependsOn = [conceptmap.ConceptMapGroupElementTargetDependsOn()]
            element.target[0].dependsOn[idx].property = "123037004"  ## Body structure
            element.target[0].dependsOn[idx].system = "http://snomed.info/sct"
            element.target[0].dependsOn[idx].value = row['Site']
            idx += 1
        if check_numeric(row['Laterality']):
            element.target[0].dependsOn = [conceptmap.ConceptMapGroupElementTargetDependsOn()]
            element.target[0].dependsOn[idx].property = "272741003"  ## Body structure laterality
            element.target[0].dependsOn[idx].system = "http://snomed.info/sct"
            element.target[0].dependsOn[idx].value = row['Laterality']
            idx += 1
        if check_numeric(row['Contrast']):
            element.target[0].dependsOn = [conceptmap.ConceptMapGroupElementTargetDependsOn()]
            element.target[0].dependsOn[idx].property = "424361007"  ## Using substance - contrast
            element.target[0].dependsOn[idx].system = "http://snomed.info/sct"
            element.target[0].dependsOn[idx].value = row['Contrast']
        elements.append(element)
    cm.group[0].element = elements
  
    # Dump the ConceptMap to file
    with open(mapfile, "w") as f:
        json.dump(cm.as_json(), f, indent=2)

    # Cleanup
    df.drop(df.index, inplace=True)


## Mainline
## Output the Valuesets and Conceptmap built from the RRS file    
def run_main(rrsfile,outdir):
    files=create_filepath(outdir)
    #(pre_co,sep,procedure,sep,site,sep,lat,sep,contrast)
    templates=get_template_files()
    for col in range(0,4):
        print("{0} Processing template...{1}".format( col, templates[col]))
        build_valueset(col,templates[col],rrsfile,files[col])
    build_concept_map(rrsfile,outdir)
