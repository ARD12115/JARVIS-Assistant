@echo off
REM Build JARVIS Tauri App with proper VC++ environment

call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvarsall.bat" x64

cd /d C:\Projects\JARVIS-Assistant\src-tauri
cargo build --bin jarvis-assistant