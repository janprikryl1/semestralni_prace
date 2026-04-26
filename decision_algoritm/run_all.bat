@echo off
cd /d "%~dp0"
start "BTCUSDC"  cmd /k "python main.py --symbol BTCUSDC"
start "XRPUSDC"  cmd /k "python main.py --symbol XRPUSDC"
start "BCHUSDC"  cmd /k "python main.py --symbol BCHUSDC"
start "TRXUSDC"  cmd /k "python main.py --symbol TRXUSDC"
start "PEPEUSDC" cmd /k "python main.py --symbol PEPEUSDC"
start "SHIBUSDC" cmd /k "python main.py --symbol SHIBUSDC"
