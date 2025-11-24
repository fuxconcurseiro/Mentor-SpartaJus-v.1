@echo off
:: O comando abaixo força o terminal a olhar para a pasta onde este arquivo está salvo
cd /d "%~dp0"

echo Verificando e ATUALIZANDO bibliotecas necessarias...
:: O comando --upgrade garante que voce tenha a versao mais recente que suporta o Gemini Flash
pip install --upgrade streamlit pandas google-generativeai matplotlib

echo.
echo Iniciando o Mentor SpartaJus...
echo Certifique-se de que o arquivo "study_app.py" esta nesta mesma pasta.
echo.

streamlit run study_app.py

if %errorlevel% neq 0 (
    echo.
    echo Ocorreu um erro. Verifique se o arquivo study_app.py esta na mesma pasta que este arquivo.
    pause
)