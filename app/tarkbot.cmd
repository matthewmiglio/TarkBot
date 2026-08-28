@echo off
rem Source-tree shim so `tarkbot --mode craft` works without installing the MSI.
rem Put this file's folder (app/) on PATH, or copy it to a folder already on PATH.
python -m cli %*
