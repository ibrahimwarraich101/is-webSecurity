$pythonPath = 'C:\Users\ibrah\AppData\Local\Programs\Python\Python314\python.exe'
if (Test-Path $pythonPath) { & $pythonPath "$PSScriptRoot\app.py" @args }
else { python "$PSScriptRoot\app.py" @args }
