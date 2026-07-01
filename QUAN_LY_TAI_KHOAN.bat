@echo off
chcp 65001 >nul
echo.
echo ================================================
echo   QUAN LY TAI KHOAN - INSAKO Tax Agent
echo ================================================
echo.
echo Chon chuc nang:
echo   1. Xem danh sach tai khoan
echo   2. Them tai khoan moi
echo   3. Doi mat khau
echo   4. Thoat
echo.
set /p choice="Nhap lua chon (1-4): "

if "%choice%"=="1" goto :list
if "%choice%"=="2" goto :add
if "%choice%"=="3" goto :change
if "%choice%"=="4" goto :end

:list
python -c "
import json
with open('auth.json', encoding='utf-8') as f:
    data = json.load(f)
print()
print('DANH SACH TAI KHOAN:')
print('-' * 40)
for username, info in data.items():
    if not username.startswith('_'):
        print(f'  Username : {username}')
        print(f'  Ten hien thi: {info[\"name\"]}')
        print(f'  Role     : {info[\"role\"]}')
        print()
"
pause
goto :end

:add
echo.
set /p newuser="Ten dang nhap moi: "
set /p newname="Ten hien thi: "
set /p newpw="Mat khau: "
set /p newrole="Role (admin/accountant/viewer): "
python -c "
import json, hashlib
with open('auth.json', encoding='utf-8') as f:
    data = json.load(f)
username = '%newuser%'.lower().strip()
pw_hash = hashlib.sha256('%newpw%'.encode()).hexdigest()
data[username] = {'name': '%newname%', 'password_hash': pw_hash, 'role': '%newrole%'}
with open('auth.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f'Da them tai khoan: {username}')
"
pause
goto :end

:change
echo.
set /p chuser="Ten dang nhap can doi mat khau: "
set /p newpw2="Mat khau moi: "
python -c "
import json, hashlib
with open('auth.json', encoding='utf-8') as f:
    data = json.load(f)
username = '%chuser%'.lower().strip()
if username in data:
    data[username]['password_hash'] = hashlib.sha256('%newpw2%'.encode()).hexdigest()
    with open('auth.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'Da doi mat khau cho: {username}')
else:
    print(f'Khong tim thay tai khoan: {username}')
"
pause

:end
echo.
