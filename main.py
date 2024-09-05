import argparse
import os
import fetcher
import lighter

homedir=os.environ['HOME']
parser = argparse.ArgumentParser()
infiledefault=os.path.join(homedir,"data","rrs","in","RRS_Candidates_3.1.tsv")
parser.add_argument("-i", "--infile", help="S2S map file RRS to SCT", default=infiledefault)
parser.add_argument("-o", "--outdir", help="output dir for artefacts", default=os.path.join(homedir,"data","rrs","out"))
parser.add_argument("-v", "--version", help="business version of the ValueSets and ConceptMaps", default="1.1.0")
parser.add_argument("-p", "--publish", help="publish to this fhir endpoint", default="")
args = parser.parse_args()
print("Started")
rrsfile=fetcher.run_main(args.infile,args.outdir)
lighter.run_main(rrsfile,args.outdir,args.publish,args.version)
print("Finished")