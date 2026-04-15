@echo off
REM Build the Nornir umbrella Sphinx monodoc using the sphinxdocs venv.
REM Can be run from any directory:
REM   docs\make.cmd          <- normal build
REM   docs\make.cmd -W       <- treat warnings as errors
REM   docs\make.cmd clean    <- wipe _build then build

setlocal

set "REPO_ROOT=%~dp0.."
set "VENV=%REPO_ROOT%\venv\sphinxdocs"
set "SPHINX=%VENV%\Scripts\sphinx-build.exe"

if not exist "%SPHINX%" (
    echo ERROR: sphinx-build not found at %SPHINX%
    echo        Create the venv and run: pip install -r docs\requirements.txt
    exit /b 1
)

pushd "%REPO_ROOT%"

if /i "%1"=="clean" (
    echo Removing docs\_build ...
    rmdir /s /q "docs\_build" 2>nul
    shift
)

"%SPHINX%" -b html docs docs/_build/html %*

if %ERRORLEVEL% == 0 (
    echo.
    echo Done.  Open docs\_build\html\index.html
) else (
    echo.
    echo sphinx-build failed with exit code %ERRORLEVEL%
    popd
    endlocal
    exit /b %ERRORLEVEL%
)

popd
endlocal
