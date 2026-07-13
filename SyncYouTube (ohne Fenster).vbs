' Startet SyncYouTube voellig OHNE jedes Fenster (nicht mal ein
' kurzes Aufblitzen wie bei der .bat). Doppelklick genuegt. Die App laeuft im
' Tray weiter (Symbol unten rechts). Zum Beenden: Tray-Symbol -> Beenden.
Dim sh, fso, base
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
base = fso.GetParentFolderName(WScript.ScriptFullName)
sh.Run """" & base & "\..\SyncDashboard\System\venv\Scripts\pythonw.exe"" """ & base & "\System\youtube_app.py""", 0, False
