@echo off
chcp 65001 >nul
echo Компиляция проекта в единый файл compiled_app.html...
powershell -NoProfile -Command ^
  "$html = Get-Content 'index.html' -Raw -Encoding UTF8; " ^
  "$css  = Get-Content 'styles.css' -Raw -Encoding UTF8; " ^
  "$db   = Get-Content 'database.js' -Raw -Encoding UTF8; " ^
  "$app  = Get-Content 'app.js' -Raw -Encoding UTF8; " ^
  "$html = $html.Replace('<link rel=\"stylesheet\" href=\"styles.css\" />', '<style>' + $css + '</style>'); " ^
  "$html = $html.Replace('<script src=\"database.js\"></script>', '<script>' + $db + '</script>'); " ^
  "$html = $html.Replace('<script src=\"app.js\"></script>', '<script>' + $app + '</script>'); " ^
  "Set-Content 'compiled_app.html' -Value $html -Encoding UTF8"
echo Готово! Запускаю справочник...
start "" "compiled_app.html"