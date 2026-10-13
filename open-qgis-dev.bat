@echo off
setlocal
set "PROFILETOOL_DEV_ROOT=%~dp0"
rem Open an isolated QGIS profile with this checkout loaded directly.
call "C:\OSGeo4W\bin\qgis.bat" --nologo --profiles-path "%TEMP%\profiletool-qgis-dev" --profile profiletool-dev --code "%~dp0scripts\qgis_dev.py"
