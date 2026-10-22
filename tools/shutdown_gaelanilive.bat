@echo off
rem Shut GaelaniLIVE down on the PS5: the payload stops (port 9049), the video wallpaper turns off,
rem the window (port 9050) closes. Usage: shutdown_gaelanilive.bat [console ip]
setlocal
set HOST=%~1
if "%HOST%"=="" set HOST=192.168.100.15
echo Shutting down GaelaniLIVE on %HOST%...
powershell -NoProfile -Command "$c = New-Object Net.Sockets.TcpClient; try { $c.Connect('%HOST%', 9049); $r = New-Object IO.StreamReader($c.GetStream()); Write-Host ('GaelaniLIVE: ' + $r.ReadLine()); $c.Close() } catch { Write-Host 'GaelaniLIVE is not running (port 9049 closed).' }"
rem Clear the crash guard so the next start can play the video.
curl -s -Q "DELE /system_tmp/gaelanilive/video_trying" ftp://%HOST%:2121/ >nul 2>&1
echo Done.
pause
