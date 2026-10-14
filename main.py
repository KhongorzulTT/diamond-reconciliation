from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Response, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
import pandas as pd
import io
import numpy as np
import urllib.parse
from typing import Optional, Dict

app = FastAPI(title="Админ удирдлагатай нэгдсэн систем")

# 6 Компанийн нягтлангуудын албан ёсны мэдээлэл (Регистрийн дугааруудыг суулгасан)
USER_DATABASE = {
    "admin@tumen.mn": {"password": "admin123", "rd": "0000000", "company": "Төв Администратор", "role": "ADMIN", "active": True},
    "buyant@tumen.mn": {"password": "pass123", "rd": "5560713", "company": "Буянт тэнгис ХХК", "role": "USER", "active": True},
    "tumurt@tumen.mn": {"password": "pass123", "rd": "5136717", "company": "Түмэн төмөрт групп ХХК", "role": "USER", "active": True},
    "tera@tumen.mn": {"password": "pass123", "rd": "6587275", "company": "Тера стийл ХХК", "role": "USER", "active": True},
    "grand@tumen.mn": {"password": "pass123", "rd": "7286681", "company": "Гранд рояал стийл ХХК", "role": "USER", "active": True},
    "tengis@tumen.mn": {"password": "pass123", "rd": "3632725", "company": "Түмэн тэнгис ХХК", "role": "USER", "active": True},
    "tseel@tumen.mn": {"password": "pass123", "rd": "2770474", "company": "Цээл мөрөн ХХК", "role": "USER", "active": True}
}

COMPANY_STATUS = {rd: "❌ Оруулаагүй" for rd in ["5560713", "5136717", "6587275", "7286681", "3632725", "2770474"]}
RECONCILIATION_RESULTS: Dict[str, Dict] = {}

# 1. НЭВТРЭХ ХУУДАС (Login Page)
@app.get("/login", response_class=HTMLResponse)
def login_page(error: Optional[str] = None):
    error_html = f'<div style="color: #ef4444; font-size: 14px; margin-bottom: 20px; text-align: center; background: #fee2e2; padding: 12px; border-radius: 12px; font-weight: 500;">{error}</div>' if error else ''
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Нэвтрэх</title>
        <style>
            body {{ font-family: -apple-system, sans-serif; margin: 0; padding: 0; background-color: #f3f4f6; display: flex; justify-content: center; align-items: center; height: 100vh; }}
            .login-card {{ background: #ffffff; padding: 40px; border-radius: 24px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1); width: 100%; max-width: 380px; border: 1px solid #e5e7eb; box-sizing: border-box; }}
            .login-card h2 {{ text-align: center; margin: 0 0 25px 0; color: #111827; }}
            .input-group {{ margin-bottom: 20px; }}
            .input-group label {{ display: block; font-size: 14px; font-weight: 600; margin-bottom: 8px; color: #374151; }}
            .input-group input {{ width: 100%; padding: 14px; border: 1px solid #d1d5db; border-radius: 12px; box-sizing: border-box; }}
            .btn-login {{ width: 100%; background: #2563eb; color: white; border: none; padding: 14px; border-radius: 12px; font-size: 16px; font-weight: bold; cursor: pointer; }}
        </style>
    </head>
    <body>
        <div class="login-card">
            <h2 style="text-align:center;">📊 Нэгдсэн Систем</h2>
            {error_html}
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
    """
    return HTMLResponse(content=html_content)

@app.post("/login")
def do_login(email: str = Form(...), password: str = Form(...)):
    user = USER_DATABASE.get(email)
    if not user or user["password"] != password:
        return RedirectResponse(url="/login?error=Мэйл+эсвэл+нууц+үг+буруу+байна", status_code=303)
    if not user.get("active", True):
        return RedirectResponse(url="/login?error=Таны+эрх+хязгаарлагдсан+байна", status_code=303)
        
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(key="session_user", value=email, httponly=True)
    return response

@app.get("/logout")
def do_logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key="session_user")
    return response

# Админ үйлдлүүд
@app.post("/admin/add-user")
def add_user(email: str = Form(...), password: str = Form(...), rd: str = Form(...), company: str = Form(...), session_user: Optional[str] = Cookie(None)):
    if not session_user or USER_DATABASE.get(session_user, {}).get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Зөвхөн админ нэвтрэх эрхтэй")
    USER_DATABASE[email] = {"password": password, "rd": rd, "company": company, "role": "USER", "active": True}
    if rd not in COMPANY_STATUS:
        COMPANY_STATUS[rd] = "❌ Оруулаагүй"
    return RedirectResponse(url="/", status_code=303)

@app.get("/admin/toggle-user/{email}")
def toggle_user(email: str, session_user: Optional[str] = Cookie(None)):
    if not session_user or USER_DATABASE.get(session_user, {}).get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Зөвхөн админ нэвтрэх эрхтэй")
    if email in USER_DATABASE and email != "admin@tumen.mn":
        USER_DATABASE[email]["active"] = not USER_DATABASE[email]["active"]
    return RedirectResponse(url="/", status_code=303)

@app.get("/admin/delete-user/{email}")
def delete_user(email: str, session_user: Optional[str] = Cookie(None)):
    if not session_user or USER_DATABASE.get(session_user, {}).get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Зөвхөн админ нэвтрэх эрхтэй")
    if email in USER_DATABASE and email != "admin@tumen.mn":
        del USER_DATABASE[email]
    return RedirectResponse(url="/", status_code=303)

# 2. ҮНДСЭН ХЯНАЛТЫН САМБАР (Dashboard & Admin View)
@app.get("/", response_class=HTMLResponse)
def get_ui(session_user: Optional[str] = Cookie(None)):
    if not session_user or session_user not in USER_DATABASE:
        return RedirectResponse(url="/login", status_code=303)
        
    current_user = USER_DATABASE[session_user]
    company_name = current_user["company"]
    company_rd = current_user["rd"]
    is_admin = current_user["role"] == "ADMIN"
    
    result = RECONCILIATION_RESULTS.get(session_user, {"total": 0, "matched": 0, "discrepancy_count": 0, "rows": []})
    
    # Тулгалтын хүснэгтийн мөрүүд үүсгэх
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
        table_rows_html = '<tr><td colspan="7" style="text-align:center; padding:30px; color:#059669; font-weight:600;">🎉 Ямар нэгэн зөрүүтэй баримт олдсонгүй.</td></tr>'
    elif not result["rows"]:
        table_rows_html = '<tr><td colspan="7" style="text-align:center; padding:30px; color:#9ca3af;">Дээд талын картуудад Excel файлуудаа хуулж тулгалт хийнэ үү.</td></tr>'

    # Компаниудын мэдээлэл оруулалтын нэгдсэн жагсаалт
    company_status_html = ""
    for u_email, u_data in USER_DATABASE.items():
        if u_data["role"] == "ADMIN": continue
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

    # АДМИН ПАНЕЛИЙГ АЛДААГҮЙ УНШИХ ШИНЭ СТАНДАРТ АРГА
    admin_panel_html = ""
    if is_admin:
        user_manage_rows = ""
        for u_email, u_data in USER_DATABASE.items():
            if u_email == "admin@tumen.mn": continue
            status_text = "🟢 Идэвхтэй" if u_data["active"] else "🔴 Хаагдсан"
            btn_toggle_text = "Эрх Хаах" if u_data["active"] else "Эрх Нээх"
            
            # f-string хаалтны алдаанаас сэргийлж мөрүүдийг энгийн конкатенациар холбоно
            user_manage_rows += "<tr style='border-bottom: 1px solid #e5e7eb;'>"
            user_manage_rows += f"<td style='padding: 10px; font-size: 14px;'>{u_data['company']}</td>"
            user_manage_rows += f"<td style='padding: 10px; font-size: 14px;'>{u_email}</td>"
