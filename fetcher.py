import subprocess
import urllib 
import numpy as np
import pandas as pd
from fhirpathpy import evaluate
import os
import json
from helpers import init,path_exists

baseurl="https://tx.ontoserver.csiro.au/fhir"
system="http://snomed.info/sct"

## Not Used
## attribute_mapper : map qualifier to least specific category for service/modality for the Concept map and RRS
## e.g. Plain x-ray imaging action (qualifier) maps to Plain x-ray (Procedure)
## Except for site specific procedures (Mammo)
## Last field is a description of the map
def attribute_mapper(modality,site):
  target = modality
  # Important: Keep site co-ordinated map rows to the top so they evaluate before the generic case
  map = [('312254007','','168537006','Plain X-Ray'),
         ('278110001','','168537006','Radiographic imaging to X-Ray'),
         ('312251004','','77477000','CT'),
         ('702569007','','717193008','Cone Beam CT'),
         ('312250003','','113091000','MRI'),
         ('278292003','','16310003','Ultrasound imaging'),
         ('312275004','','44491008','Fluoroscopy')
        
## Site specific from here
         ('278110001','76752008','71651007','Mammography'),
         ('360037004','41801008','77343006','Angiography')
         ]
  for map_src,map_site,map_trg,desc in map:
    if modality == map_src and (map_site == site or map_site == ""):
      target = map_trg            
  
  return target  


## Check for the existance of the file paths and return those in an array
def create_filepath(s2sfile,outdir):
    if (not path_exists(s2sfile)) or (not path_exists(outdir)):       
        return {}    
    filepath = {
        "s2sfile": s2sfile,
        "rrsfile": os.path.join(outdir,"rrs.txt")       
    }    
    return filepath


# match_property_name
# SNOMED Relationship qualifiers for radiology procedures
# return values:
#    0 == Procedure/modality/service
#    1 == Site 
#    2 == Laterality    
#    3 == Using Contrast
# return -1 if no match
def match_property_name(sct_code):
  index=-1
  property_list = [("260686004",0),("405813007",1),("272741003",2),("424361007",3)]
  for concept, field in property_list:
      if concept == sct_code:
        index=field
        break
  return index  


## get_valueset
## Generic Valueset getter, pass in a URL expression
## return a json response from the curl call
def get_valueset(expr):
  vsexp=baseurl+'/ValueSet/$expand?url='
  query=vsexp+urllib.parse.quote(expr,safe='')
  command = ['curl', '-H "Accept: application/fhir+json" ' , '--location', query]  
  result = subprocess.run(command, capture_output=True)
  data =  json.loads(result.stdout)
  return data


## get_concept_all_props
## Perform a CodeSystem lookup and get all properties 
## return a json resposne from the curl call
def get_concept_all_props(code):
  cslookup='/CodeSystem/$lookup'  
  query=baseurl+cslookup+'?system='+urllib.parse.quote(system,safe='')+"&code="+code+"&property=*"

  command = ['curl', '-H "Accept: application/fhir+json" ' , '--location', query]
  result = subprocess.run(command, capture_output=True)
  data =  json.loads(result.stdout)
  return data


## procedure mapper 
## given a procedure code (proc), lookup the ancestors to see what the base procedure is
## Get the ancestors and check to see if the match our list of common services/procedures/modalities
def procedure_mapper(proc):
  target = proc
  ecl='http://snomed.info/sct?fhir_vs=ecl/>'+ proc
  data = get_valueset(ecl)
  concepts = evaluate(data,"expansion.contains.code")
  ### Need to put this in a lookup table
  map = [('82918005','Pet'),
         ('168537006','Plain X-Ray'),
         ('77477000','CT'),
         ('717193008','Cone Beam CT'),
         ('113091000','MRI'),
         ('16310003','Ultrasound imaging'),
         ('44491008','Fluoroscopy'),
         ('71651007','Mammography'),
         ('77343006','Angiography'),
         ('27483000','X-ray with contrast')
         ]
  
  for src,desc in map:          
    if src in concepts:
      target=src
      break
    
  return target


##  get_body_structures
##  Get SNOMED Body Structure array, passing in a laterality
##   return an array of SNOMED concept ids for lateralised Body Structures
def get_body_structures(laterality_name):
  bodystruct_id="123037004"
  laterality_qualifier_id="272741003"
  # default to left
  laterality_id="7771000"
  if laterality_name not in ['left','right']:
    print("Error: Laterality name must be left or right")
    return {}
  else:
    if laterality_name == "right":
      laterality_id="24028007"
  ecl='http://snomed.info/sct?fhir_vs=ecl/<'+bodystruct_id+':'+laterality_qualifier_id+'='+laterality_id
  data = get_valueset(ecl)
  body_structures = evaluate(data,"expansion.contains.code")    
  return body_structures

## get_snomed_props
## Expand the defining relationships (properties) of the SNOMED CT Concept
##   return a pandas data frame with the expanded properties 
def get_snomed_props(code):
  # Expand the properties for the SNOMED CT concept (code)
  data=get_concept_all_props(code)
  # Evaluate a fhirpath expression to get the Concept subproperties
  expr="Parameters.parameter.where(name=\'property\').part.where(name=\'subproperty\').part"
  parts = evaluate(data,expr)

  # Iterate through the subproperty parts to find the attribute values pairs (defining relationships)
  temp_list = []
  for elem in parts:    
    if elem["name"]=="code":
      qualifier = elem["valueCode"]
      # identify what type of qualifier property e.g. method / site / Using contrast this is returning type_id (int) 0..3
      type_id = match_property_name(qualifier)
    if elem["name"] == "value":
      target_value=elem["valueCode"]
      row = [code, type_id, qualifier, target_value]
      temp_list.append(row)
  df = pd.DataFrame(temp_list,columns=["Concept","TypeId","Qualifier","TargetValue"])
  return df


## split_site
##   return the de-lateralised concept (find the proximal primitive parent)
def split_site(code):
  ecl='http://snomed.info/sct?fhir_vs=ecl/>! '+code+' {{ C definitionStatus = primitive }}'
  data = get_valueset(ecl)
  body_structure = evaluate(data,"expansion.contains.code")    
  return body_structure


## Separate lateralised body site into a body site column and a flag for left, right, both
##  left_list and right_list are arrays of concepts that have the laterality listed in the name of that variable.
def expand_body_site(df,left_list,right_list,fh):
  sep="\t"
  pre_co=""
  procedure=""
  lat=""
  contrast=""
  site=""
  sorted_props = df.sort_values(by=['TypeId'])
  for index, row in sorted_props.iterrows():
    # Procedure / Modality
    if row["TypeId"] == 0:
      if pre_co == "":
        pre_co = row["Concept"]       
    # Body Site    
    if row["TypeId"] == 1:    
      concept = row["TargetValue"]
      # Extract the laterality, rule is it's bilateral if in both left and right sets.    
      if (concept in left_list) and (concept in right_list):
        lat="51440002"
      elif (concept in left_list):
        lat="7771000"
      elif (concept in right_list):
        lat="24028007"
      # If laterality exists, find the proximal primitive parent    
      site=row["TargetValue"]  
      if lat != "":  
         site_array=split_site(concept)
         if site_array:
            site=site_array[0]  
    # Contrast  
    if row["TypeId"] == 3:
      contrast="263543005"
  procedure = procedure_mapper(pre_co)
  if procedure==pre_co:
    print("ERROR: Unable to determine base radiological procedure for code: "+pre_co)
  else:
   fh.write("%s%s%s%s%s%s%s%s%s\n" % (pre_co,sep,procedure,sep,site,sep,lat,sep,contrast))

"""
Mainline
"""

def run_main(s2sfile,outdir):
  sep="\t"
  files=create_filepath(s2sfile,outdir)
  left_list=get_body_structures("left")
  right_list=get_body_structures("right")  
  data=pd.read_csv(files["s2sfile"],sep='\t',dtype={'Target code': str})
  fhRRS=init(files["rrsfile"])
  fhRRS.write("%s%s%s%s%s%s%s%s%s\n" % ("Service",sep,"Procedure",sep,"Site",sep,"Laterality",sep,"Contrast"))
  # find the concepts marked as equivalent and extract the relationships / properties
  for index, row in data.iterrows():
    if row["Relationship type code"] == "TARGET_EQUIVALENT":
        if row["Target code"] != "":
          order_code = str(row["Target code"])
          rrs_df = get_snomed_props(order_code)  
          # Take the initial dataframes and further expand the body structure to add laterality
          expand_body_site(rrs_df,left_list,right_list,fhRRS)
  fhRRS.close()
  return files["rrsfile"]

         
