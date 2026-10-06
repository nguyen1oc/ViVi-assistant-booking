@echo off
REM Cross-platform Python launcher for AI log hooks (Windows cmd.exe).
REM Test every PATH match so a broken Microsoft Store alias is skipped.

for /f "delims=" %%P in ('where py.exe 2^>nul') do (
  "%%P" -3 -c "import sys" >nul 2>nul
  if not errorlevel 1 (
    "%%P" -3 %*
    exit /b %ERRORLEVEL%
  )
)

for %%N in (python.exe python3.exe) do (
  for /f "delims=" %%P in ('where %%N 2^>nul') do (
    "%%P" -c "import sys" >nul 2>nul
    if not errorlevel 1 (
      "%%P" %*
      exit /b %ERRORLEVEL%
    )
  )
)

exit /b 0
