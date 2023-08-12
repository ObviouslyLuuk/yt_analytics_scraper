@REM Delete directory D:\\Users\\Luuk\\Documents\\Programming\\stuff\\yt_realtime_data\\User Data
@REM Delete directory D:\\Users\\Luuk\\Documents\\Programming\\stuff\\yt_realtime_data\\backup\\User Data(backup)

@echo off
setlocal EnableDelayedExpansion

set "target=D:\\Users\\Luuk\\Documents\\Programming\\stuff\\yt_realtime_data\\User Data"
set "backup=D:\\Users\\Luuk\\Documents\\Programming\\stuff\\yt_realtime_data\\backup\\User Data(backup)"

rmdir /S /Q "%target%"
rmdir /S /Q "%backup%"

@REM Copy directory C:\\Users\\321lu\\AppData\\Local\\Google\\Chrome\\User Data to D:\\Users\\Luuk\\Documents\\Programming\\stuff\\yt_realtime_data\\User Data 
@REM Copy directory C:\\Users\\321lu\\AppData\\Local\\Google\\Chrome\\User Data to D:\\Users\\Luuk\\Documents\\Programming\\stuff\\yt_realtime_data\\backup\\User Data(backup)

set "source=C:\\Users\\321lu\\AppData\\Local\\Google\\Chrome Beta\\User Data"

xcopy /E /I /Y "%source%" "%target%"
xcopy /E /I /Y "%source%" "%backup%"
```