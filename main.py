import argparse
import os
import fetcher
import lighter

homedir=os.environ['HOME']
parser = argparse.ArgumentParser()
infiledefault=os.path.join(homedir,"data","rrs","in","RRS_to_SNOMED_2024-02-01.tsv")
parser.add_argument("-i", "--infile", help="S2S map file RRS to SCT", default=infiledefault)
parser.add_argument("-o", "--outdir", help="ouput dir for artefacts", default=os.path.join(homedir,"data","rrs","out"))
args = parser.parse_args()

rrsfile=fetcher.run_main(args.infile,args.outdir)
lighter.run_main(rrsfile,args.outdir)
