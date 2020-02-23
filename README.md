# mmbot_api
API middleware to bridge mm2 / cex autotrading

# Linux Setup
Clone repo
```
sudo apt update 
sudo apt-get install python3-venv libcurl4-gnutls-dev
cd
git clone https://github.com/smk762/mmbot_qt
cd mmbot_qt
```



Create a virtual environment in the current directory:

`python3 -m venv venv`

Activate the virtual environment:

`source venv/bin/activate`

Install dependancies

`sudo apt-get install libpython3.6`

`pip3 install -r requirements.txt`

Build with `pyinstaller --onefile mmbot_api.py`

If you face issues with pydantic module / maximum recursion error while creating binary, use the version below -

`SKIP_CYTHON=1 pip install git+https://github.com/samuelcolvin/pydantic.git@v0.32`

Credit: https://github.com/pyinstaller/pyinstaller/issues/4346#issuecomment-520293391
