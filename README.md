# nornir

Umbrella project for all nornir packages

## Dev setup


### Setup Python environment

```sh
git clone https://github.com/jamesra/nornir.git
cd nornir
git switch dev
git submodule update --init --recursive
python -m venv env
source ./env/bin/activate
python install_dev.py
```

### Automated Tests

#### Data files

Get data files for tests from here:
http://storage1.connectomes.utah.edu/nornir-testdata.zip
And unzip in parent directory. Or run this script:

```sh
python download_test_files.py
```


#### Run test file example

Tests expect two environment variables:

TESTINPUTPATH=<Path to Test Data>
TESTOUTPUTPATH=<Path to write test results>

```sh
cd nornir-buildmanager/test
python -m pipeline.test_idoc
```
