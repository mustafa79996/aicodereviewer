' VBScript to launch AI Code Reviewer server completely silently in the background
Set fso = CreateObject("Scripting.FileSystemObject")
ScriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

PythonExe = ScriptDir & "\venv\Scripts\python.exe"
If Not fso.FileExists(PythonExe) Then
    PythonExe = "python.exe"
End If

ServerScript = ScriptDir & "\run_server.py"

Cmd = """" & PythonExe & """ """ & ServerScript & """ --host 0.0.0.0 --port 8000"

Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = ScriptDir
WshShell.Environment("PROCESS")("PYTHONPATH") = ScriptDir
WshShell.Environment("PROCESS")("PYTHONUTF8") = "1"

' 0 = Hide window completely, False = Do not wait for script to finish
WshShell.Run Cmd, 0, False
