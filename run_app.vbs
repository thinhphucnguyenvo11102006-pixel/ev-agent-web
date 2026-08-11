Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

projectDir = fso.GetParentFolderName(WScript.ScriptFullName)
pythonExe = projectDir & "\.venv\Scripts\python.exe"
mainScript = projectDir & "\main_desktop.py"

WshShell.CurrentDirectory = projectDir
WshShell.Run """" & pythonExe & """ """ & mainScript & """", 0, False
