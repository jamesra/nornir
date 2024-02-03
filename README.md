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
And unzip somewhere. Or run this script:

```sh
python download_test_files.py
```

#### Environment variables

Tests expect two environment variables:

TESTINPUTPATH=<Path to Test Data>
TESTOUTPUTPATH=<Path to write test results>

If running nornir-buildmanager tests, can set these by creating a `.env` file. See the `.env.example` file.

#### Run a test file

```sh
cd nornir-buildmanager/test
python -m pipeline.test_idoc
```

Confirm the test generates files here:
`test-output/IDocSingleSectionImportTest/TEM/0017/TEM`

#### Debug test with vscode

```sh
python -m debugpy --wait-for-client --listen 0.0.0.0:5678 -m pipeline.test_idoc
```

And add this config to launch.json
```json
{
  "name": "Python Debugger: Attach",
  "type": "debugpy",
  "request": "attach",
  "connect": {
    "host": "localhost",
    "port": 5678
  }
}
```