@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM ============================================================
REM  MONTE CARLO RUNNER — PROPHET BATTERY EXPERIMENTS
REM ============================================================

set NUM_RUNS=100
set CONFIG_FILE=default_settings.txt
set OUT_DIR=run_outputs
set REPORTS_DIR=reports

if not "%~1"=="" set NUM_RUNS=%~1
if not "%~2"=="" set CONFIG_FILE=%~2

cd /d "%~dp0"

if not exist "%CONFIG_FILE%" (
    echo ERROR: Config not found
    exit /b 1
)

if exist "%OUT_DIR%" rmdir /s /q "%OUT_DIR%"
mkdir "%OUT_DIR%"

echo ============================================
echo  PROPHET MONTE CARLO EXPERIMENT
echo ============================================
echo Runs : %NUM_RUNS%
echo ============================================

for /L %%R in (1,1,%NUM_RUNS%) do (

    echo.
    echo -------- RUN %%R / %NUM_RUNS% --------

    REM UNIQUE SEED PER RUN
    set /a SEED=10000 + %%R * 37

    REM CLEAN REPORTS
    if exist "%REPORTS_DIR%" del /q "%REPORTS_DIR%\*.txt" 2>nul

    REM CREATE TEMP CONFIG — strip existing seed line, inject new one
    (for /f "tokens=*" %%L in (%CONFIG_FILE%) do (
        set "line=%%L"
        echo !line! | findstr /i "MovementModel.rngSeed" >nul
        if !ERRORLEVEL! neq 0 echo !line!
    )) > temp_config.txt
    echo MovementModel.rngSeed = !SEED! >> temp_config.txt

    REM RUN SIMULATION
    cmd /c one.bat -b 1 temp_config.txt

    if !ERRORLEVEL! neq 0 (
        echo ERROR in run %%R
        exit /b !ERRORLEVEL!
    )

    REM SAVE OUTPUT
    set "RUN_FOLDER=%OUT_DIR%\run%%R"
    mkdir "!RUN_FOLDER!"

    for %%F in ("%REPORTS_DIR%\*.txt") do (
        copy "%%F" "!RUN_FOLDER!\%%~nxF" >nul
    )

    del temp_config.txt

    echo Saved run %%R ^(seed=!SEED!^)
)

echo.
echo ============================================
echo DONE — ALL MONTE CARLO RUNS COMPLETE
echo ============================================

endlocal