#JPEGr

This was actually partially the reason why I developed Flask-Transfer. To create a displayable representation of a PDF, specifically for resumes (yes, yes, a text representation of a resume is a better choice, but let's ignore that).

This highlight's Flask-Transfer's strengths: hiding the complexity of manipulating uploads behind a few lines of code. Inside `jpegr/transfer.py` are five functions that handle: converting a PDF to a JPG, changing the filename from a pdf extension to a jpg extension, ensuring there are no name collisions, and flashing the success to the user. There's also an example use of the metadata attribute for the pre and postprocessors.

Rather than cramming all of that into the routing function, it's tucked away into its own module, registered on a Transfer instance and invoked with `PDFTransfer.save`. 

##Dependecies
There are dependencies outside of Flask and Flask-Transfer:

* flask-bootstrap
* flask-wtf
* wand
* ImageMagick (wand system level dependency)

##Running
Navigate to this folder and run `python run.py`

