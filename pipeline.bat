@ECHO OFF
setlocal
echo %cd%
set PYTHONIOENCODING=UTF-8
set PYTHONPATH=%cd%
call venv\Scripts\activate.bat
python db\main.py --drop_results
python ref_area\main.py
python mastr\main.py
python images\preprocessing\main.py
python building\main.py
python images\prediction\main.py
python images\postprocessing\main.py
python mapping\main.py
endlocal
