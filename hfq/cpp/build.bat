@echo off
REM 构建 hfq C++ 引擎 CLI。使用 conda 环境 hfqcpp 中自带的 MinGW g++（无需 VS / Windows SDK）。
setlocal
set MINGW=C:\App\miniconda3\envs\hfqcpp\Library\mingw-w64\bin
set PATH=%MINGW%;%PATH%
echo Using g++:
"%MINGW%\g++.exe" --version | findstr /R "g++"
"%MINGW%\g++.exe" -std=c++14 -O2 -static -o hfq_cli.exe hfq_cli.cpp hfq_engine.cpp
if exist hfq_cli.exe (echo BUILD OK) else (echo BUILD FAILED & exit /b 1)
endlocal
