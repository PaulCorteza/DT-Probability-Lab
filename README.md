# Dice Throne Probability Calculator

A beginner-friendly Python project that calculates exact probabilities for five six-sided dice.

## 1. Install the tools

Install:
- Python 3.11 or newer: https://www.python.org/downloads/
- Visual Studio Code: https://code.visualstudio.com/

During Python installation on Windows, select **Add Python to PATH**.

## 2. Open the project

Extract this ZIP file. In VS Code, choose **File → Open Folder** and select `dice_throne_calculator`.

Open **Terminal → New Terminal**.

## 3. Create a virtual environment

In the VS Code terminal, run:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run this once in that terminal:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

## 4. Install Streamlit

```powershell
py -m pip install -r requirements.txt
```

## 5. Run the app

```powershell
py -m streamlit run app.py
```

The app should open in your browser. If it does not, open the local URL printed in the terminal (usually http://localhost:8501).

## 6. Run the tests

In a second terminal (or after stopping the app with Ctrl+C):

```powershell
py -m unittest -v
```

## Project files

- `app.py` — the Streamlit user interface
- `dice_engine.py` — the probability calculations and strategy optimizer
- `test_dice_engine.py` — basic automated tests
- `requirements.txt` — external Python packages

## Important first-version assumptions

This prototype uses five standard six-sided dice. It includes generic combinations (three/four/five of a kind, four sixes, and two straights). Dice Throne character boards can have different symbols and ability-specific rules, which we can model in a later version.
# DTStratLab
# DT-Probability-Lab
