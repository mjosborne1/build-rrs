"""
   fhir lighter library for building the fhir artefacts from the TSV input file 
"""

import json
import numpy as np
import pandas as pd
from fhirclient.models import valueset,conceptmap,codesystem
from fhirclient import client
from helpers import path_exists 
from fetcher import read_focus_procedures
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
   

def build_valueset(col,template,infile,outfile,smart,version):
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
    vs.version = version or meta.get('version')
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

def build_bodysite_valuesets(infile, outdir, version):
    """
    Build BodySite ValueSets based on the input file for each modality, template file and output to outdir.
    """
    df = pd.read_csv(infile, sep='\t', dtype={'Service': str, 'Procedure': str, 'Site': str, 'Laterality': str, 'Contrast': str})
    template = os.path.join('.','templates','ValueSet-radiology-body-structure-template.json')
    # Get list of focus procedures:  which are code, display pairs
    focus_procedures=read_focus_procedures()  
    # Get unique Procedures
    unique_procedures = df['Procedure'].unique()
    
    # Read the FHIR ValueSet JSON template file into a Python dictionary
    with open(template) as f:
        meta = json.load(f)
    
    for procedure in unique_procedures:
        # Filter the dataframe for the current procedure
        procedure_df = df[df['Procedure'] == procedure]
        
        # Get unique Sites for the current procedure
        unique_sites = procedure_df['Site'].astype(str).unique()
        
        # Build a friendly nametag for the ValueSet
        for code,desc in focus_procedures:          
            if code == procedure:
                proc_name=desc
                proc_name_vs=desc.replace(" ","-")
                break
        # Create a FHIR ValueSet resource object
        vs = valueset.ValueSet()
        vs.status = meta.get('status')
        vs.name = f"{meta.get('name')}-{proc_name_vs}"
        vs.title = f"{meta.get('title')} for Procedure {proc_name}"
        vs.description = f"{meta.get('description')} for Procedure {proc_name}"
        vs.publisher = meta.get('publisher')
        vs.version = version or meta.get('version')
        vs.url = f"{meta.get('url')}-{proc_name_vs}"
        vs.copyright = meta.get('copyright')
        vs.experimental = meta.get('experimental')
        
        # Add the concepts to the ValueSet
        vs.compose = valueset.ValueSetCompose()
        vs.compose.include = [valueset.ValueSetComposeInclude()]
        vs.compose.include[0].system = "http://snomed.info/sct"
        vs.compose.include[0].concept = []
        
        for site in unique_sites:
            if site.isdigit():
                include_concept = valueset.ValueSetComposeIncludeConcept()
                include_concept.code = str(site)
                vs.compose.include[0].concept.append(include_concept)
        
        # Export the ValueSet to file for manual review
        outfile = os.path.join(outdir, f"ValueSet-{proc_name_vs}.json")
        with open(outfile, "w") as f:
            json.dump(vs.as_json(), f, indent=2)


def build_concept_map(rrsfile,outdir,smart,version):
    """
    Build a concept map of procedures and other qualifiers in a property/dependsOn style 
    to a radiology service code (fully defined)
    """
    print(f'...Building ConceptMap')
    mapfile = os.path.join(outdir,"ConceptMap_RadiologyServices.json")
    df=pd.read_csv(rrsfile,sep='\t',dtype={'Service':str,'Procedure':str,'Site':str,'Laterality':str,'Contrast':str})
    # Read the FHIR ConceptMap JSON file into a Python dictionary
    template =  os.path.join('.','templates','ConceptMap-radiology-services-template.json')
    print("Processing ConceptMap template...{0}".format(template))
    prop_modality =  "FocalProcedure"
    prop_site = "BodySite"
    prop_laterality = "Laterality"
    prop_contrast = "Contrast"
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
    cm.version = version or meta.get('version')
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
            dep.property =  prop_site
            dep.system = "http://snomed.info/sct"
            ## Body structure
            dep.value = row['Site']
            if not isinstance(element.target[0].dependsOn, list):
                element.target[0].dependsOn = []
            element.target[0].dependsOn.append(dep)
        else:
            dep = conceptmap.ConceptMapGroupElementTargetDependsOn()
            dep.property = prop_site
            dep.system = "http://terminology.hl7.org/CodeSystem/data-absent-reason"
            dep.value = "unknown" 
            if not isinstance(element.target[0].dependsOn, list):
               element.target[0].dependsOn = []
            element.target[0].dependsOn.append(dep)
        if is_numeric(row['Laterality']):
            dep = conceptmap.ConceptMapGroupElementTargetDependsOn()
            dep.property = prop_laterality
            dep.system = "http://snomed.info/sct"
            dep.value = row['Laterality']
            if not isinstance(element.target[0].dependsOn, list):
                element.target[0].dependsOn = []
            element.target[0].dependsOn.append(dep)
        else:
            dep = conceptmap.ConceptMapGroupElementTargetDependsOn()
            dep.property = prop_laterality
            dep.system = "http://terminology.hl7.org/CodeSystem/data-absent-reason"
            dep.value = "unknown" 
            if not isinstance(element.target[0].dependsOn, list):
               element.target[0].dependsOn = []
            element.target[0].dependsOn.append(dep)    
        if is_numeric(row['Contrast']):
            dep = conceptmap.ConceptMapGroupElementTargetDependsOn()
            dep.property = prop_contrast
            dep.system = "http://snomed.info/sct"
            dep.value = row['Contrast']
            if not isinstance(element.target[0].dependsOn, list):
                element.target[0].dependsOn = []
            element.target[0].dependsOn.append(dep)
        else:
            dep = conceptmap.ConceptMapGroupElementTargetDependsOn()
            dep.property = prop_contrast 
            dep.system = "http://terminology.hl7.org/CodeSystem/data-absent-reason"
            dep.value = "unknown" 
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



def build_codesystem_supplement(rrsfile,outdir,smart,version):
    """
    Build a SNOMED CT codesystem supplement of procedures, bodysite, laterality and 
    contrast for each single radiology service code 
    """
    print(f'...Building CodeSystem Supplement')
    cs_sup_file = os.path.join(outdir,"CodeSystemSupplementRadiology.json")
    df=pd.read_csv(rrsfile,sep='\t',dtype={'Service':str,'Procedure':str,'Site':str,'Laterality':str,'Contrast':str})
    
    # Read the FHIR ConceptMap JSON file into a Python dictionary
    template =  os.path.join('.','templates','CodeSystemSupplement-template.json')
    print("Processing CodeSystem Supplement template...{0}".format(template))
    
    ## Drop any duplicate rows
    df.drop_duplicates(subset=['Service', 'Procedure'], inplace=True)

    def make_property(source):
        prop = codesystem.CodeSystemProperty()
        prop.code = source["code"]
        prop.description = source["description"]
        prop.type = source["type"]
        return prop

    with open(template) as f:
        meta = json.load(f)
        cs = codesystem.CodeSystem()
        cs.status = meta.get('status')
        cs.name = meta.get('name')
        cs.title = meta.get('title')
        cs.description = meta.get('description')
        cs.publisher = meta.get('publisher')
        cs.version = version or meta.get('version')
        cs.url = meta.get('url')
        cs.copyright = meta.get('copyright')
        cs.experimental = meta.get('experimental')
        cs.content = meta.get('content')
        cs.supplements = meta.get('supplements')
        cs.property = [ make_property(x) for x in meta["property"] ]
        cs.concept = []        
       
        for index, row in df.iterrows():
            if not is_numeric(row['Service']):
                continue
            concept = codesystem.CodeSystemConcept()
            concept.code = row['Service']        
            concept.property = [] 
            if is_numeric(row['Procedure']):
                prop = codesystem.CodeSystemConceptProperty()
                prop.code = "Procedure"
                prop.valueCode = row['Procedure']
                concept.property.append(prop)
            if is_numeric(row['Site']): 
                prop = codesystem.CodeSystemConceptProperty()
                prop.code = "BodySite"
                prop.valueCode = row['Site']
                concept.property.append(prop)
            if is_numeric(row['Laterality']): 
                prop = codesystem.CodeSystemConceptProperty()
                prop.code = "BodySiteLaterality"
                prop.valueCode = row['Laterality']
                concept.property.append(prop)
            if is_numeric(row['Contrast']): 
                prop = codesystem.CodeSystemConceptProperty()
                prop.code = "Contrast"
                prop.valueCode = row['Contrast']
                concept.property.append(prop)
            cs.concept.append(concept)
        # Dump the ConceptMap to file for manual review
        with open(cs_sup_file, "w") as f:
            json.dump(cs.as_json(), f, indent=2)
    
        if smart != None:
            response = cs.create(smart.server)
            if response:
                return 201
            else:
                return 500
        else:
            return 200

## Mainline
## Output the Valuesets and Conceptmap built from the RRS file    
def run_main(rrsfile,outdir,endpoint,version):
    smart=None
    if (endpoint != ""):
         smart = create_client(endpoint)
    # Note, the template file order must match the valueset file order
    vs_files=create_vs_filepath(outdir)
    templates=get_template_files()

    for col in range(0,5):
        print("{0} Processing template...{1}".format( col, templates[col]))
        vs = build_valueset(col,templates[col],rrsfile,vs_files[col],smart,version)        
    cm = build_concept_map(rrsfile,outdir,smart,version)
    csupp = build_codesystem_supplement(rrsfile,outdir,smart,version)    
    # Create custom per modality ValueSets
    bsvs =  build_bodysite_valuesets(rrsfile,outdir,version) 