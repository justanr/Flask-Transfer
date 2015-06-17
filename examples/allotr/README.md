
#Allotr

Flask allows rejecting incoming files if they're too big. However, what if you wanted to reject files if they caused a directory to grow too large? This example application uses a really bad implementation of `du -s` to determine the current size of a directory and then checks if the uploaded file causes the directory to exceed it's allotment (by default 20kb).

##Dependencies

* Flask
* Flask-Bootstrap
* Flask-WTF
* Flask-Transfer

## Running
Navigate here after install dependencies and run `python run.py`
