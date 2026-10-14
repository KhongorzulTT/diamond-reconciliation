from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
import pandas as pd
import io
import numpy as np
import urllib.parse
from typing import Optional, Dict

app = FastAPI(title="Олон Компанийн Нэгдсэн Хяналтын Самбар")

# 6 Компанийн нягтлангуудын албан ёсны мэдээлэл (Регистрийн дугаарыг таны өгснөөр зассан)
USER_DATABASE = {
    "buyant@tumen.mn": {"password": "pass123", "rd": "5560713", "company": "Буянт тэнгис ХХК"},
    "tumurt@tumen.mn": {"password": "pass123", "rd": "5136717", "company": "Түмэн төмөрт групп ХХК"},
    "tera@tumen.mn": {"password": "pass123", "rd": "6587275", "company": "Тера стийл ХХК"},
    "grand@tumen.mn": {"password": "pass123", "rd": "7286681", "company": "Гранд рояал стийл ХХК"},
    "tengis@tumen.mn": {"password": "pass123", "rd": "3632725", "company": "Түмэн тэнгис ХХК"},
    "tseel@tumen.mn": {"password": "pass123", "rd": "2770474", "company": "Цээл мөрөн ХХК"}
}

# Бүх компаниудын дата оруулалтын төлөвийг хянах глобал сан
COMPANY_STATUS = {rd: "❌ Оруулаагүй" for rd in ["5560713", "5136717", "6587275", "7286681", "3632725", "2770474"]}
RECONCILIATION_RESULTS: Dict[str, Dict] = {}

@app.get("/login", response_class=HTMLResponse)
def login_page(error: Optional[str] = None):
    error_html = f'<div style="color: #ef4444; font-size: 14px; margin-bottom: 20px; text-align: center; background: #fee2e2; padding: 12px; border-radius: 12px; font-weight: 500;">{error}</div>' if error else ''
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Нэвтрэх</title>
        <style>
            body { font-family: -apple-system, sans-serif; margin: 0; padding: 0; background-color: #f3f4f6; display: flex; justify-content: center; align-items: center; height: 100vh; }
            .login-card { background: #ffffff; padding: 40px; border-radius: 24px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1); width: 100%; max-width: 380px; border: 1px solid #e5e7eb; box-sizing: border-box; }
            .login-card h2 { text-align: center; margin: 0 0 25px 0; color: #111827; }
            .input-group { margin-bottom: 20px; }
            .input-group label { display: block; font-size: 14px; font-weight: 600; margin-bottom: 8px; color: #374151; }
            .input-group input { width: 100%; padding: 14px; border: 1px solid #d1d5db; border-radius: 12px; box-sizing: border-box; }
            .btn-login { width: 100%; background: #2563eb; color: white; border: none; padding: 14px; border-radius: 12px; font-size: 16px; font-weight: bold; cursor: pointer; }
        </style>
    </head>
    <body>
        <div class="login-card">
            <h2 style="text-align:center;">📊 Тулгалтын Систем</h2>
            """ + error_html + """
            <form action="/login" method="post">
                <div class="input-group">
                    <label>Цахим шуудан (Email):</label>
                    <input type="email" name="email" required placeholder="username@tumen.mn">
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
    """)

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

@app.get("/", response_class=HTMLResponse)
def get_ui(session_user: Optional[str] = Cookie(None)):
    if not session_user or session_user not in USER_DATABASE:
        return RedirectResponse(url="/login", status_code=303)
        
    user_info = USER_DATABASE[session_user]
    company_name = user_info["company"]
    company_rd = user_info["rd"]
    
    result = RECONCILIATION_RESULTS.get(session_user, {"total": 0, "matched": 0, "discrepancy_count": 0, "rows": []})
    
    # 1. Алдаатай баримтуудын хүснэгт бэлдэх
    table_rows_html = ""
    for row in result["rows"][:50]:
        bg_color = "#fef2f2" if "дутуу" in row["Төлөв"] else "#fffb001a"
        table_rows_html += f"""
        <tr style="background: {bg_color}; border-bottom: 1px solid #e5e7eb;">
            <td style="padding: 12px; font-size: 14px;">{row['Огноо']}</td>
            <td style="padding: 12px; font-size: 14px; font-weight:600;">{row['Baarany_Kod']}</td>
            <td style="padding: 12px; font-size: 14px; text-align:right;">{int(row['Diamond_Too'])}</td>
            <td style="padding: 12px; font-size: 14px; text-align:right;">{int(row['App2_Too'])}</td>
            <td style="padding: 12px; font-size: 14px; text-align:right; color:#ef4444; font-weight:600;">{int(row['Too_Zuruu'])}</td>
            <td style="padding: 12px; font-size: 14px; text-align:right; color:#ef4444;">{row['Urtug_Zuruu']:,.2f}</td>
            <td style="padding: 12px; font-size: 14px; color:#b91c1c; font-weight:500;">{row['Tuluv']}</td>
        </tr>
        """
    if not result["rows"] and result["total"] > 0:
        table_rows_html = '<tr><td colspan="7" style="text-align:center; padding:30px; color:#059669; font-weight:600;">🎉 Ямар нэгэн зөрүүтэй баримт олдсонгүй. Бүх дата таарлаа.</td></tr>'
    elif not result["rows"]:
        table_rows_html = '<tr><td colspan="7" style="text-align:center; padding:30px; color:#9ca3af;">Дээд талын картуудад Excel файлуудаа хуулж тулгалт хийнэ үү.</td></tr>'

    # 2. ШИНЭ: Компаниудын мэдээлэл оруулалтын хяналтын хүснэгт бэлдэх
    company_status_html = ""
    for u_email, u_data in USER_DATABASE.items():
        status_now = COMPANY_STATUS.get(u_data["rd"], "❌ Оруулаагүй")
        badge_style = "background:#d1fae5; color:#065f46;" if "Дата" in status_now else "background:#fee2e2; color:#991b1b;"
        company_status_html += f"""
        <tr style="border-bottom: 1px solid #e5e7eb;">
            <td style="padding: 12px; font-size: 14px; font-weight:600; color:#374151;">{u_data['company']}</td>
            <td style="padding: 12px; font-size: 14px; color:#6b7280;">{u_data['rd']}</td>
            <td style="padding: 12px; font-size: 14px; color:#6b7280;">{u_email}</td>
            <td style="padding: 12px; font-size: 13px;"><span style="padding:4px 10px; border-radius:8px; font-weight:bold; {badge_style}">{status_now}</span></td>
        </tr>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Нэгдсэн Хяналтын Самбар</title>
        <style>
            body {{ font-family: -apple-system, sans-serif; margin: 0; padding: 0; background-color: #f3f4f6; color: #1f2937; }}
            .navbar {{ background-color: #ffffff; border-bottom: 1px solid #e5e7eb; padding: 15px 30px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
            .container {{ max-width: 950px; margin: 30px auto; padding: 0 20px; }}
            .company-header {{ background: #eff6ff; padding: 15px 25px; border-radius: 14px; border: 1px solid #bfdbfe; font-weight: 700; color: #1e40af; display:flex; justify-content:space-between; align-items:center; margin-bottom:25px; }}
            .stats-grid {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin-bottom: 30px; }}
            .stat-card {{ background: white; padding: 20px; border-radius: 16px; border: 1px solid #e5e7eb; }}
            .stat-title {{ font-size: 13px; color: #6b7280; font-weight: 600; text-transform: uppercase; margin-bottom: 5px; }}
            .stat-value {{ font-size: 28px; font-weight: 800; }}
            .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px; }}
            .card {{ background: #ffffff; padding: 22px; border-radius: 16px; border: 1px solid #e5e7eb; box-sizing: border-box; }}
            .file-input {{ width: 100%; font-size: 13px; padding: 8px; background: #f9fafb; border: 1px dashed #d1d5db; border-radius: 10px; cursor: pointer; box-sizing: border-box; }}
            .btn-submit {{ width: 100%; background-color: #2563eb; color: #ffffff; border: none; padding: 15px; border-radius: 12px; font-size: 16px; font-weight: bold; cursor: pointer; display: flex; justify-content: center; align-items: center; gap: 10px; }}
            .table-card {{ background: white; border-radius: 16px; border: 1px solid #e5e7eb; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); overflow: hidden; margin-bottom: 30px; }}
            .table-header {{ padding: 20px; border-bottom: 1px solid #e5e7eb; display: flex; justify-content: space-between; align-items: center; background:#fafafa; }}
            table {{ width: 100%; border-collapse: collapse; text-align: left; }}
            th {{ padding: 12px; background: #f9fafb; font-size: 13px; font-weight: 700; color: #4b5563; border-bottom: 1px solid #e5e7eb; }}
        </style>
    </head>
    <body>
        <div class="navbar">
            <div style="font-weight:bold; font-size:16px;">📊 СИСТЕМИЙН НЭГДҮҮР ХЯНАЛТ</div>
            <div>
                <span style="font-size: 14px; margin-right: 15px; font-weight:500;">👤 {session_user}</span>
                <a href="/logout" style="color:#ef4444; font-size:14px; font-weight:bold; text-decoration:none;">Гарах 🚪</a>
            </div>
        </div>

        <div class="container">
