@echo off
rem GaelaniLIVE Engine - conversor de vídeo para la PS5. Arrastra uno o más archivos
rem o carpetas sobre este archivo.
rem   Cualquier formato (mkv, mov, avi, webm, mp4, 10-bit, HDR, 120 fps...) -> <nombre>_ps5.mp4
rem   junto al original: H.264 8-bit, máximo 60 fps, tamaño por píxeles (con barras negras):
rem     hasta 1080p -> 1920x1080 / hasta 1440p -> 2560x1440 (2K) / mayor -> 3840x2160 (4K).
rem   El sonido se conserva (AAC estéreo, sin cambiar loudness). Índice al inicio: arranque rápido.
rem Variables opcionales:
rem   FORCE=1   vuelve a convertir aunque el _ps5.mp4 ya exista
rem   CODEC=hevc  sale en HEVC en vez de H.264 (la PS5 también lo reproduce)
rem Necesita ffmpeg.exe en esta carpeta o en el PATH.
setlocal EnableExtensions
set FFMPEG=%~dp0ffmpeg.exe
if not exist "%FFMPEG%" set FFMPEG=ffmpeg
"%FFMPEG%" -version >nul 2>&1
if errorlevel 1 (
  echo No se encontro ffmpeg.exe. Deja en la misma carpeta que este archivo o en el PATH.
  pause
  exit /b 1
)
if "%~1"=="" (
  echo Arrastra uno o mas vídeos o carpetas sobre convert_for_ps5.bat.
  pause
  exit /b 1
)

set SW=if(gt(iw*ih,3686400),3840,if(gt(iw*ih,2073600),2560,1920))
set SH=if(gt(iw*ih,3686400),2160,if(gt(iw*ih,2073600),1440,1080))
set PW=if(gt(iw,2560)+gt(ih,1440),3840,if(gt(iw,1920)+gt(ih,1080),2560,1920))
set PH=if(gt(iw,2560)+gt(ih,1440),2160,if(gt(iw,1920)+gt(ih,1080),1440,1080))
set VCODEC=libx264
set PROFILE=-profile:v high
set XPARAMS=-x264-params "keyint=60:min-keyint=30:scenecut=0:open-gop=0:ref=4"
if /i "%CODEC%"=="hevc" (
  set VCODEC=libx265
  set PROFILE=
  set XPARAMS=-x265-params "keyint=60:min-keyint=30:scenecut=0:open-gop=0:ref=4"
)
set FAILED=0
set DONE=0

:loop
if "%~1"=="" goto done
if exist "%~1\" (
  for %%F in ("%~1\*.mp4" "%~1\*.mkv" "%~1\*.mov" "%~1\*.avi" "%~1\*.webm" "%~1\*.m4v" "%~1\*.ts" "%~1\*.flv" "%~1\*.wmv" "%~1\*.mpg" "%~1\*.mpeg" "%~1\*.3gp") do call :convert "%%~fF"
) else (
  call :convert "%~f1"
)
shift
goto loop

:convert
if "%~1"=="" goto :eof
if not exist "%~1" goto :eof
set OUT=%~dpn1_ps5.mp4
if exist "%OUT%" if not "%FORCE%"=="1" (
  echo Omitido (ya existe): %~nx1
  goto :eof
)
echo.
echo === %~nx1
"%FFMPEG%" -hide_banner -loglevel error -stats -y -i "%~1" ^
  -map 0:v:0 -map 0:a? ^
  -vf "scale=w='%SW%':h='%SH%':force_original_aspect_ratio=decrease:force_divisible_by=2:flags=lanczos,pad=w='%PW%':h='%PH%':x=(ow-iw)/2:y=(oh-ih)/2,format=yuv420p" ^
  -fpsmax 60 -c:v %VCODEC% %PROFILE% -preset slow -crf 17 -maxrate 40M -bufsize 60M ^
  %XPARAMS% ^
  -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv ^
  -c:a aac -b:a 192k -ar 48000 -ac 2 ^
  -movflags +faststart "%OUT%"
if errorlevel 1 (
  echo FALLIDO: %~nx1
  set FAILED=1
) else (
  echo OK: %~n1_ps5.mp4
  set /a DONE+=1
)
goto :eof

:done
echo.
echo Hecho: %DONE% vídeo(s) convertidos.
if "%FAILED%"=="1" echo ATENCION: alguno fallo (arriba se ve el error).
echo Copia los _ps5.mp4 a /data/GaelaniLIVE/video en la PS5, a una carpeta "gaelanilive"
echo de un USB, o subelos desde la pagina movil/PC o con tools\gaelanilive_manager.py.
echo Los 4K/2K valen como fondo principal; para "solo por juego" usa uno de 1080p.
pause
