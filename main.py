from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Response, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
import pandas as pd
import io
from typing import Optional

app = FastAPI(title="Компаниудын нэгдсэн дата цуглуулах систем")

# 6 Компанийн мэдээлэл
USER_DATABASE = {
    "buyant@tumen.mn": {"password": "pass123", "rd": "5046244", "company": "Буянт тэнгис ХХК"},
    "tera@tumen.mn": {"password": "pass123", "rd": "5324112", "company": "Тера стийл ХХК"},
    "grand@tumen.mn": {"password": "pass123", "rd": "5118742", "company": "Гранд рояал стийл ХХК"},
    "tumurt@tumen.mn": {"password": "pass123", "rd": "2664531", "company": "Түмэн төмөрт групп ХХК"},
    "tengis@tumen.mn": {"password": "pass123", "rd": "4125883", "company": "Түмэн тэнгис ХХК"},
    "tseel@tumen.mn": {"password": "pass123", "rd": "6032147", "company": "Цээл мөрөн ХХК"}
}

# Системийн төв өгөгдлийн сан (Бүх компанийн дата энд РД-аар ялгарч хадгалагдана)
CENTRAL_DATABASE = []

# 1. НЭВТРЭХ ХУУДАС
@app.get("/login", response_class=HTMLResponse)
def login_page(error: Optional[str] = None):
    error_html = f'<div style="color: #ef4444; font-size: 14px; margin-bottom: 20px; text-align: center; background: #fee2e2; padding: 12px; border-radius: 12px; font-weight: 500;">{error}</div>' if error else ''
    html_content = """
    <!DOCTYPE html>
    <html lang="mn">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Нэвтрэх - Нэгдсэн систем</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 0; background-color: #f3f4f6; display: flex; justify-content: center; align-items: center; height: 100vh; }
            .login-card { background: #ffffff; padding: 40px; border-radius: 24px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1); width: 100%; max-width: 380px; border: 1px solid #e5e7eb; box-sizing: border-box; }
            .logo-area { text-align: center; font-size: 40px; margin-bottom: 10px; }
            .login-card h2 { text-align: center; margin: 0 0 8px 0; color: #111827; font-size: 24px; font-weight: 800; }
            .login-card p { text-align: center; margin: 0 0 25px 0; color: #6b7280; font-size: 14px; }
            .input-group { margin-bottom: 20px; }
            .input-group label { display: block; font-size: 14px; font-weight: 600; margin-bottom: 8px; color: #374151; }
            .input-group input { width: 100%; padding: 14px; border: 1px solid #d1d5db; border-radius: 12px; box-sizing: border-box; font-size: 15px; background-color: #f9fafb; }
            .btn-login { width: 100%; background: #2563eb; color: white; border: none; padding: 14px; border-radius: 12px; font-size: 16px; font-weight: bold; cursor: pointer; }
        </style>
    </head>
    <body>
        <div class="login-card">
            <div class="logo-area">🏢</div>
            <h2>Системд нэвтрэх</h2>
            <p>Компаниудын нэгдсэн дата оруулах сан</p>
            """ + error_html + """
            <form action="/login" method="post">
                <div class="input-group">
                    <label>Цахим шуудан (Email):</label>
                    <input type="email" name="email" required placeholder="name@company.mn">
                </div>
                <div class="input-group">
                    <label>Нууц үг:</label>
                    <input type="password" name="password" required placeholder="••••••••">
                </div>
                <button type="submit" class="btn-login">Нэвтрэх</button>
            </form>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/login")
def do_login(email: str = Form(...), password: str = Form(...)):
    user = USER_DATABASE.get(email)
    if not user or user["password"] != password:
        return RedirectResponse(url="/login?error=Мэйл+эсвэл+нууц+үг+буруу+байна", status_code=303)
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(key="session_user", value=email, httponly=True)
    return response

@app.get("/logout")
def do_logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key="session_user")
    return response

# 2. ҮНДСЭН АЖЛЫН ХУУДАС (Зөвхөн өөрийн компанидаа дата оруулах ганц карттай)
@app.get("/", response_class=HTMLResponse)
def get_ui(session_user: Optional[str] = Cookie(None), message: Optional[str] = None):
    if not session_user or session_user not in USER_DATABASE:
        return RedirectResponse(url="/login", status_code=303)
        
    user_info = USER_DATABASE[session_user]
    company_name = user_info["company"]
    company_rd = user_info["rd"]
    
    msg_html = f'<div style="background:#d1fae5; color:#065f46; padding:15px; border-radius:14px; text-align:center; font-weight:600; margin-bottom:20px;">{message}</div>' if message else ''
    
    html_content = """
    <!DOCTYPE html>
    <html lang="mn">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Дата оруулах цонх</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 0; background-color: #f3f4f6; color: #1f2937; }
            .navbar { background-color: #ffffff; border-bottom: 1px solid #e5e7eb; padding: 15px 30px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
            .brand { font-size: 18px; font-weight: bold; color: #111827; }
            .logout-btn { color: #ef4444; text-decoration: none; font-size: 14px; font-weight: 600; background: #fee2e2; padding: 8px 14px; border-radius: 10px; }
            .container { max-width: 600px; margin: 40px auto; padding: 0 20px; }
            .header-section { text-align: center; margin-bottom: 35px; }
            .header-section h1 { font-size: 26px; font-weight: 800; color: #111827; }
            .company-info-box { background: #eff6ff; padding: 20px; border-radius: 18px; border: 1px solid #bfdbfe; margin-bottom: 30px; text-align: center; font-weight: 700; color: #1e40af; font-size: 16px; }
            .card { background: #ffffff; padding: 30px; border-radius: 20px; border: 1px solid #e5e7eb; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); border-top: 5px solid #2563eb; }
            .card-title { font-size: 18px; font-weight: 700; margin-bottom: 8px; color: #111827; }
            .card-desc { font-size: 13px; color: #6b7280; margin-bottom: 20px; }
            .file-input { width: 100%; font-size: 14px; color: #4b5563; padding: 15px; background: #f9fafb; border: 1px dashed #d1d5db; border-radius: 12px; cursor: pointer; box-sizing: border-box; }
            .btn-submit { width: 100%; background-color: #2563eb; color: #ffffff; border: none; padding: 16px; border-radius: 14px; font-size: 16px; font-weight: bold; cursor: pointer; margin-top: 20px; box-shadow: 0 4px 6px rgba(37, 99, 235, 0.2); }
        </style>
    </head>
    <body>
        <div class="navbar">
            <div class="brand">📊 КОМПАНИУДЫН НЭГДҮҮР САН</div>
            <div>
                <span style="font-size: 14px; margin-right: 15px; font-weight:500;">👤 """ + session_user + """</span>
                <a href="/logout" class="logout-btn">Гарах 🚪</a>
            </div>
        </div>

        <div class="container">
            <div class="header-section">
                <h1>Бараа материалын дата оруулах</h1>
            </div>

            """ + msg_html + """

            <div class="company-info-box">
                🏢 ХАРЬЯАЛАХ КОМПАНИ: """ + company_name + """ (РД: """ + company_rd + """)
            </div>

            <div class="card">
                <form action="/upload-data/" method="post" enctype="multipart/form-data">
                    <div class="card-title">📁 Бараа материалын файл оруулах</div>
                    <div class="card-desc">Тухайн компанийн орлого, зарлагын Excel файлыг сонгож оруулна уу.</div>
                    <input type="file" name="excel_file" required class="file-input"/>
                    <button type="submit" class="btn-submit">📤 Сонгосон компанийн датаг илгээх</button>
                </form>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# 3. ДАТА ХҮЛЭЭН АВЧ НЭГДСЭН САНД БҮРТГЭХ
@app.post("/upload-data/")
async def upload_data(
    excel_file: UploadFile = File(...),
    session_user: Optional[str] = Cookie(None)
):
    if not session_user or session_user not in USER_DATABASE:
        raise HTTPException(status_code=401, detail="Нэвтрэх эрх баталгаажаагүй.")
        
    user_info = USER_DATABASE[session_user]
    company_rd = user_info["rd"]
    company_name = user_info["company"]

    try:
        df = pd.read_excel(io.BytesIO(await excel_file.read()))
        
        # Оруулсан мөр бүрт тухайн компанийн РД болон Нэрийг автоматаар хаяглаж зооно
        df.insert(0, 'Регистрийн_Дугаар', company_rd)
        df.insert(1, 'Компанийн_Нэр', company_name)
        
        # Төв дата бааз руу нэмж нэгтгэх
        global CENTRAL_DATABASE
        CENTRAL_DATABASE.extend(df.to_dict(orient="records"))
        
        url_msg = urllib.parse.quote(f"{company_name}-ийн дата нэгдсэн санд амжилттай бүртгэгдлээ!")
        return RedirectResponse(url=f"/?message={url_msg}", status_code=303)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Файлыг уншихад алдаа гарлаа: {str(e)}")
