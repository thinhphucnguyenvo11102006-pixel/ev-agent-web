Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

projectDir = fso.GetParentFolderName(WScript.ScriptFullName)
pythonExe = projectDir & "\.venv\Scripts\python.exe"
wakeScript = projectDir & "\wake_word_listener.py"

WshShell.CurrentDirectory = projectDir
WshShell.Run """" & pythonExe & """ """ & wakeScript & """", 0, False
