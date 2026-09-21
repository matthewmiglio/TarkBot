@echo off
rem The laptop side of scripts/run_on_laptop.sh: run one live test and log the result.
rem
rem Launched by a scheduled task, never by SSH. An SSH process on Windows gets no desktop, so
rem every screen grab in it fails with "screen grab failed" and every click goes nowhere. A task
rem created /RU <user> /IT runs in that user's interactive session, which has one.
rem
rem The test path and its arguments come out of run_test.txt and run_args.txt rather than off this
rem line, because the scheduled task is what supplies the line and quoting them through
rem ssh -> cmd.exe -> schtasks /tr is a thicket. The driver script writes both files.
cd /d "%~dp0"

rem Hide this console before anything reads the screen. The task opens it over the game, and the
rem game runs borderless at the full screen size, so a console left on top is a black hole in the
rem middle of every match: the first run found the hideout tab at 0.526 with the window covering
rem the left half of the menu. SW_HIDE (0) rather than minimise, so it cannot flicker back. The
rem log is a file, so nothing is lost by having no console to print to.
python -c "import ctypes;ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(),0)"

set TEST=
set ARGS=
if exist run_test.txt set /p TEST=<run_test.txt
if exist run_args.txt set /p ARGS=<run_args.txt
if "%TEST%"=="" (
    echo no run_test.txt: nothing to run> live.log
    exit /b 1
)
python "%TEST%" %ARGS% > live.log 2>&1
echo EXIT=%ERRORLEVEL%>> live.log
