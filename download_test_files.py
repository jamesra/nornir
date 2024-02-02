import urllib.request
import zipfile
import os

# URL of the zip file
url = "http://storage1.connectomes.utah.edu/nornir-testdata.zip"

# Path to the parent directory where the zip file will be extracted
parent_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
zip_file_path = os.path.join(parent_directory, "nornir-testdata.zip")

# URL of the zip file
url = "http://storage1.connectomes.utah.edu/nornir-testdata.zip"

# Download the zip file
urllib.request.urlretrieve(url, zip_file_path)

# Extract the zip file
with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
    zip_ref.extractall(parent_directory)

# Remove the zip file
os.remove(zip_file_path)
