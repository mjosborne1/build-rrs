### Installation Requirements
- Python and the ability to install modules using pip. This will be automatic through the requirements file.
- An input source which is the TSV file exported from Snap2SNOMED
- A file path for the output of the process , on Windows this might be C:\data\rrs\out 
  on Mac/Linux it will be /home/user/data/rrs/out or similar where `user` is your account name

### How to install this script
   * `virtualenv .venv`
   * `source env/bin/activate`
   * `pip install -r requirements.txt`


### How to run this script
   * `python main.py -i <S2S map file Catalogue to SCT> -o <output folder>`

### Unit testing
   run the unit tests in test.py to ensure everything is setup correcty
   I do this through the Test Explorer extension in VS Code, 
   select build-rrs and press the play button.

### Regenerating the requirements.txt file
If you change this code and want to regenerate the requirements use this:
   `pip freeze >| requirements.txt`
