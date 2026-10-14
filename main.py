from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Response, Cookie
from fastapi.responses import StreamingResponse, HTMLResponse, RedirectResponse
import pandas as pd
import io
import numpy as np
import urllib.parse
from typing import Optional

app = FastAPI(title="Хэрэглэгчийн эрхтэй Тулгалтын Систем")

# 6 Компанийн нягтлангуудын мэдээлэл
USER_DATABASE = {
    "buyant@tumen.mn": {"password": "pass123", "rd": "1111111", "company": "Буянт тэнгис ХХК"},
    "tera@tumen.mn": {"password": "pass123", "rd": "2222222", "company": "Тера стийл ХХК"},
    "grand@tumen.mn": {"password": "pass123", "rd": "3333333", "company": "Гранд рояал стийл ХХК"},
    "tumurt@tumen.mn": {"password": "pass123", "rd": "4444444", "company": "Түмэн төмөрт групп ХХК"},
    "tengis@tumen.mn": {"password": "pass123", "rd": "5555555", "company": "Түмэн тэнгис ХХК"},
    "tseel@tumen.mn": {"password": "pass123", "rd": "6666666", "company": "Цээл мөрөн ХХК"}
}

# 1. НЭВТРЭХ ХУУДАС (Загварыг бүрэн шинэчилсэн)
@app.get("/login", response_class=HTMLResponse)
def login_page(error: Optional[str] = None):
    error_html = f'<div style="color: #ef4444; font-size: 14px; margin-bottom: 20px; text-align: center; background: #fee2e2; padding: 10px; border-radius: 10px; font-weight: 500;">{error}</div>' if error else ''
    
    html_content = """
    <!DOCTYPE html>
    <html lang="mn">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Нэвтрэх - Тулгалтын Систем</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 0; background-color: #f3f4f6; display: flex; justify-content: center; align-items: center; height: 100vh; }
            .login-card { background: #ffffff; padding: 40px; border-radius: 24px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1), 0 8px 10px -6px rgba(0,0,0,0.1); width: 100%; max-width: 380px; border: 1px solid #e5e7eb; }
            .logo-area { text-align: center; font-size: 40px; margin-bottom: 10px; }
            .login-card h2 { text-align: center; margin: 0 0 8px 0; color: #111827; font-size: 24px; font-weight: 800; letter-spacing: -0.5px; }
            .login-card p { text-align: center; margin: 0 0 25px 0; color: #6b7280; font-size: 14px; }
            .input-group { margin-bottom: 20px; }
            .input-group label { display: block; font-size: 14px; font-weight: 600; margin-bottom: 8px; color: #374151; }
            .input-group input { width: 100%; padding: 14px; border: 1px solid #d1d5db; border-radius: 12px; box-sizing: border-box; font-size: 15px; background-color: #f9fafb; transition: all 0.2s; }
            .input-group input:focus { outline: none; border-color: #2563eb; background-color: #ffffff; box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.1); }
            .btn-login { width: 100%; background: #2563eb; color: white; border: none; padding: 14px; border-radius: 12px; font-size: 16px; font-weight: bold; cursor: pointer; transition: background 0.2s; box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2); }
            .btn-login:hover { background: #1d4ed8; }
        </style>
    </head>
    <body>
        <div class="login-card">
            <div class="logo-area">📊</div>
            <h2>Системд нэвтрэх</h2>
            <p>Бараа материалын нэгдсэн тулгалтын сан</p>
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

# 2. ҮНДСЭН АЖЛЫН ХУУДАС (Дизайн, картуудыг 100% зассан)
@app.get("/", response_class=HTMLResponse)
def get_ui(session_user: Optional[str] = Cookie(None)):
    if not session_user or session_user not in USER_DATABASE:
        return RedirectResponse(url="/login", status_code=303)
        
    user_info = USER_DATABASE[session_user]
    company_name = user_info["company"]
    company_rd = user_info["rd"]
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="mn">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Бараа Материалын Тулгалтын Систем</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 0; background-color: #f3f4f6; color: #1f2937; }}
            .navbar {{ background-color: #ffffff; border-bottom: 1px solid #e5e7eb; padding: 15px 30px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
            .brand {{ font-size: 18px; font-weight: bold; color: #111827; display: flex; align-items: center; gap: 8px; }}
            .logout-btn {{ color: #ef4444; text-decoration: none; font-size: 14px; font-weight: 600; background: #fee2e2; padding: 8px 14px; border-radius: 10px; transition: background 0.2s; }}
            .logout-btn:hover {{ background: #fca5a5; }}
            .container {{ max-width: 800px; margin: 40px auto; padding: 0 20px; }}
            .header-section {{ text-align: center; margin-bottom: 35px; }}
            .header-section h1 {{ font-size: 28px; font-weight: 800; color: #111827; margin-bottom: 10px; letter-spacing: -0.5px; }}
            .header-section p {{ font-size: 15px; color: #4b5563; margin: 0; }}
            .company-info-box {{ background: #eff6ff; padding: 20px; border-radius: 18px; border: 1px solid #bfdbfe; margin-bottom: 30px; text-align: center; font-weight: 700; color: #1e40af; font-size: 16px; box-shadow: 0 2px 4px rgba(37,99,235,0.02); }}
            .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 35px; }}
            @media (max-width: 640px) {{ .grid {{ grid-template-columns: 1fr; }} }}
            .card {{ background: #ffffff; padding: 28px; border-radius: 20px; border: 1px solid #e5e7eb; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.03); box-sizing: border-box; }}
            .card-title {{ font-size: 17px; font-weight: 700; margin-bottom: 8px; color: #111827; display: flex; align-items: center; gap: 8px; }}
            .card-desc {{ font-size: 13px; color: #6b7280; margin-bottom: 20px; line-height: 1.4; }}
            .file-input {{ width: 100%; font-size: 14px; color: #4b5563; padding: 10px; background: #f9fafb; border: 1px dashed #d1d5db; border-radius: 12px; cursor: pointer; box-sizing: border-box; }}
            .btn-submit {{ width: 100%; background-color: #2563eb; color: #ffffff; border: none; padding: 18px; border-radius: 18px; font-size: 17px; font-weight: bold; cursor: pointer; box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.3); display: flex; justify-content: center; align-items: center; gap: 10px; transition: all 0.2s; }}
            .btn-submit:hover {{ background-color: #1d4ed8; transform: translateY(-1px); box-shadow: 0 12px 20px -3px rgba(37, 99, 235, 0.4); }}
            .btn-submit:active {{ transform: translateY(0); }}
        </style>
    </head>
    <body>
        <div class="navbar">
            <div class="brand">📊 ТУЛГАЛТЫН НЭГДСЭН СИСТЕМ</div>
            <div style="display: flex; align-items: center; gap: 15px;">
                <span style="font-size: 14px; font-weight: 500; color: #374151;">👤 {session_user}</span>
                <a href="/logout" class="logout-btn">Гарах 🚪</a>
            </div>
        </div>

        <div class="container">
            <div class="header-section">
                <h1>Бараа материалын орлого зарлагын тулгалт</h1>
                <p>Excel файлуудаа хуулж, зөрүүтэй гүйлгээг секундын дотор шүүнэ үү</p>
            </div>

            <div class="company-info-box">
                🏢 ИДЭВХТЭЙ АГУУЛАХ: {company_name} <span style="font-weight:500; color:#2563eb; margin-left:10px;">(РД: {company_rd})</span>
            </div>

            <form action="/reconcile/" method="post" enctype="multipart/form-data">
                <div class="grid">
                    <!-- Diamond Card -->
                    <div class="card" style="border-top: 5px solid #2563eb;">
                        <div class="card-title">💎 Diamond Программ</div>
                        <div class="card-desc">Санхүүгийн системээс татсан орлого, зарлагын Excel файл</div>
                        <input type="file" name="diamond_file" required class="file-input"/>
                    </div>

                    <!-- 2nd App Card -->
                    <div class="card" style="border-top: 5px solid #7c3aed;">
                        <div class="card-title">📱 2-р Программ / Касс</div>
                        <div class="card-desc">Борлуулалтын систем эсвэл кассаас татсан Excel файл</div>
                        <input type="file" name="second_app_file" required class="file-input"/>
                    </div>
                </div>


