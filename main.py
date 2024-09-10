import argparse
import os
import fetcher
import lighter
import logging
from datetime import datetime

def main():
    homedir=os.environ['HOME']
    parser = argparse.ArgumentParser()
    infiledefault=os.path.join(homedir,"data","rrs","in","RRS_Candidates_4.4.1.tsv")
    endpoint_default="https://r4.ontoserver.csiro.au/fhir"
    #endpoint_default="http://localhost:8080/fhir"
    templates_path="templates--smartdemo"
    logger = logging.getLogger(__name__)
    parser.add_argument("-i", "--infile", help="S2S map file RRS to SCT", default=infiledefault)
    parser.add_argument("-o", "--outdir", help="output dir for artefacts", default=os.path.join(homedir,"data","rrs","out"))
    parser.add_argument("-p", "--publish", help="publish to this fhir endpoint", default=endpoint_default)
    parser.add_argument("-t", "--templates", help="templates path relative to this source folder", default=templates_path)
    parser.add_argument("-s", "--skip", help="Skip generating the rrs.txt file", default="")

    args = parser.parse_args()
    now = datetime.now() # current date and time
    ts = now.strftime("%Y%m%d-%H%M%S")
    FORMAT='%(asctime)s %(lineno)d : %(message)s'
    logging.basicConfig(format=FORMAT, filename=f'build-rrs-{ts}.log',level=logging.INFO)
    logger.info('Started')
    if args.skip != "yes":
        rrsfile=fetcher.run_main(args.infile,args.outdir)
    else:
        rrsfile=os.path.join(args.outdir,'rrs.txt')
    lighter.run_main(rrsfile,args.outdir,args.publish,args.templates)
    logger.info("Finished")

if __name__ == '__main__':
    main()