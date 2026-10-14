from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Response, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
import pandas as pd
import io
import numpy as np
import urllib.parse
from typing import Optional, Dict

app = FastAPI(title="Reconciliation System")

# 6 Компанийн нягтлангуудын албан ёсны мэдээлэл
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
    error_msg = f'<div style="color:red;margin-bottom:15px;text-align:center;">{error}</div>' if error else ''
    
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Login</title>
        <style>
            body { font-family: sans-serif; background-color: #f3f4f6; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .card { background: white; padding: 40px; border-radius: 16px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); width: 320px; }
            .field { margin-bottom: 15px; }
            .field label { display: block; margin-bottom: 5px; font-weight: bold; font-size: 14px; }
            .field input { width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 8px; box-sizing: border-box; }
            .btn { width: 100%; background: #2563eb; color: white; border: none; padding: 12px; border-radius: 8px; font-weight: bold; cursor: pointer; }
        </style>
    </head>
    <body>
        <div class="card">
            <h2 style="text-align:center; margin-top:0;">📊 Системд нэвтрэх</h2>
            """ + error_msg + """
            <form action="/login" method="post">
                <div class="field">
                    <label>Цахим шуудан (Email):</label>
                    <input type="email" name="email" required>
                </div>
                <div class="field">
                    <label>Нууц үг:</label>
                    <input type="password" name="password" required>
                </div>
                <button type="submit" class="btn">Нэвтрэх</button>
            </form>
        </div>
    </body>
    </html>
    """
    return html_content

@app.post("/login")
def do_login(email: str = Form(...), password: str = Form(...)):
    user = USER_DATABASE.get(email)
    if not user or user["password"] != password:
        return RedirectResponse(url="/login?error=Email+esvel+nuuts+ug+buruu", status_code=303)
    if not user.get("active", True):
        return RedirectResponse(url="/login?error=Erkh+haagdsan", status_code=303)
        
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
        raise HTTPException(status_code=403, detail="Forbidden")
    USER_DATABASE[email] = {"password": password, "rd": rd, "company": company, "role": "USER", "active": True}
    if rd not in COMPANY_STATUS:
        COMPANY_STATUS[rd] = "❌ Оруулаагүй"
    return RedirectResponse(url="/", status_code=303)

@app.get("/admin/toggle-user/{email}")
def toggle_user(email: str, session_user: Optional[str] = Cookie(None)):
    if not session_user or USER_DATABASE.get(session_user, {}).get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Forbidden")
    if email in USER_DATABASE and email != "admin@tumen.mn":
        USER_DATABASE[email]["active"] = not USER_DATABASE[email]["active"]
    return RedirectResponse(url="/", status_code=303)

@app.get("/admin/delete-user/{email}")
def delete_user(email: str, session_user: Optional[str] = Cookie(None)):
    if not session_user or USER_DATABASE.get(session_user, {}).get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Forbidden")
    if email in USER_DATABASE and email != "admin@tumen.mn":
        del USER_DATABASE[email]
    return RedirectResponse(url="/", status_code=303)

# 2. ҮНДСЭН ХЯНАЛТЫН САМБАР (Workspace)
@app.get("/", response_class=HTMLResponse)
def get_ui(session_user: Optional[str] = Cookie(None)):
    if not session_user or session_user not in USER_DATABASE:
        return RedirectResponse(url="/login", status_code=303)
        
    current_user = USER_DATABASE[session_user]
    company_name = current_user["company"]
    company_rd = current_user["rd"]
    is_admin = current_user["role"] == "ADMIN"
    
    result = RECONCILIATION_RESULTS.get(session_user, {"total": 0, "matched": 0, "discrepancy_count": 0, "rows": []})
    
    table_rows = ""
    for row in result["rows"][:50]:
        table_rows += f"<tr style='border-bottom:1px solid #ddd;'>"
        table_rows += f"<td style='padding:10px;'>{row['Огноо']}</td>"
        table_rows += f"<td style='padding:10px;font-weight:bold;'>{row['Baarany_Kod']}</td>"
        table_rows += f"<td style='padding:10px;text-align:right;'>{int(row['Diamond_Too'])}</td>"
        table_rows += f"<td style='padding:10px;text-align:right;'>{int(row['App2_Too'])}</td>"
        table_rows += f"<td style='padding:10px;text-align:right;color:red;'>{int(row['Too_Zuruu'])}</td>"
        table_rows += f"<td style='padding:10px;text-align:right;color:red;'>{row['Urtug_Zuruu']:,.2f}</td>"
        table_rows += f"<td style='padding:10px;color:brown;'>{row['Tuluv']}</td>"
        table_rows += "</tr>"
        
    if not result["rows"] and result["total"] > 0:
        table_rows = '<tr><td colspan="7" style="text-align:center;padding:20px;color:green;">🎉 Зөрүүгүй таарлаа.</td></tr>'
    elif not result["rows"]:
        table_rows = '<tr><td colspan="7" style="text-align:center;padding:20px;color:#777;">Файлуудаа хуулж тулгалт хийнэ үү.</td></tr>'

    status_rows = ""
    for u_email, u_data in USER_DATABASE.items():
        if u_data["role"] == "ADMIN": continue
        st = COMPANY_STATUS.get(u_data["rd"], "❌ Оруулаагүй")
        status_rows += f"<tr style='border-bottom:1px solid #ddd;'>"
        status_rows += f"<td style='padding:10px;font-weight:bold;'>{u_data['company']}</td>"
        status_rows += f"<td style='padding:10px;'>{u_data['rd']}</td>"
        status_rows += f"<td style='padding:10px;'>{u_email}</td>"
        status_rows += f"<td style='padding:10px;'>{st}</td>"
        status_rows += "</tr>"

    admin_section = ""
    if is_admin:
        manage_rows = ""
        for u_email, u_data in USER_DATABASE.items():
            if u_email == "admin@tumen.mn": continue
            act = "🟢 Идэвхтэй" if u_data["active"] else "🔴 Хаагдсан"
            t_txt = "Хаах" if u_data["active"] else "Нээх"
            manage_rows += f"<tr style='border-bottom:1px solid #ddd;'><td>{u_data['company']}</td><td>{u_email}</td><td>{u_data['password']}</td><td>{act}</td>"
            manage_rows += f"<td><a href='/admin/toggle-user/{u_email}' style='margin-right:10px;'>{t_txt}</a><a href='/admin/delete-user/{u_email}' style='color:red;'>Устгах</a></td></tr>"
            
        admin_section = """
        <div style="background:white;padding:20px;border-radius:12px;margin-top:30px;border:1px solid #ccc;">
            <h3>🛠️ Хэрэглэгчдийг удирдах (Админ цэс)</h3>
            <form action="/admin/add-user" method="post" style="display:flex;gap:10px;margin-bottom:20px;">
                <input type="email" name="email" placeholder="Email" required style="padding:6px;width:20%;">
                <input type="text" name="password" placeholder="Нууц үг" required style="padding:6px;width:15%;">
                <input type="text" name="rd" placeholder="Регистр" required style="padding:6px;width:15%;">
                <input type="text" name="company" placeholder="Компани" required style="padding:6px;width:30%;">
                <button type="submit" style="padding:6px 15px;">➕ Нэмэх</button>
            </form>
            <table style="width:100%;border-collapse:collapse;text-align:left;">
                <thead><tr style="background:#eee;"><th>Компани</th><th>Мэйл</th><th>Нууц үг</th><th>Төлөв</th><th>Үйлдэл</th></tr></thead>
                <tbody>""" + manage_rows + """</tbody>
            </table>
        </div>
        """

    workspace = ""
    if not is_admin:
        dl_btn = f'<a href="/download-excel/" style="background:green;color:white;padding:8px 12px;border-radius:6px;text-decoration:none;font-size:14px;">📥 Excel-ээр татах</a>' if result['discrepancy_count'] > 0 else ''
        workspace = """
