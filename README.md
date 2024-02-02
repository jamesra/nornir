# nornir

Umbrella project for all nornir packages

## Dev setup

### Test data files

Get data files for tests from here:
http://storage1.connectomes.utah.edu/nornir-testdata.zip
And unzip in parent directory. Or run this script:

```sh
python download_test_files.py
```

### Setup Python environment

```sh
git clone https://github.com/jamesra/nornir.git
cd nornir
git switch dev
git submodule update --init --recursive
python -m venv env
source ./env/bin/activate
```
