Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\ximon\Kodprojekt\skriv"
WshShell.Run "C:\Python314\python.exe skriv.py", 1, False
