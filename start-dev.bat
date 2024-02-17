@echo off

:: Start Flask application in the background
start cmd /k "python app.py"

:: Start the Tailwind CSS development server
npx tailwindcss build -o static/dist/output.css --watch