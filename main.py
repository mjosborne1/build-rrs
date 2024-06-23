import argparse
import os
import fetcher
import lighter

homedir=os.environ['HOME']
parser = argparse.ArgumentParser()
infiledefault=os.path.join(homedir,"data","rrs","in","RRSReleaseCandidates062024.tsv")
parser.add_argument("-i", "--infile", help="S2S map file RRS to SCT", default=infiledefault)
parser.add_argument("-o", "--outdir", help="output dir for artefacts", default=os.path.join(homedir,"data","rrs","out"))
parser.add_argument("-p", "--publish", help="publish to this fhir endpoint", default="")
args = parser.parse_args()
print("Started")
rrsfile=fetcher.run_main(args.infile,args.outdir)
lighter.run_main(rrsfile,args.outdir,args.publish)
print("Finished")