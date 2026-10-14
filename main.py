from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
import pandas as pd
import io
import numpy as np

app = FastAPI(title="Diamond болон 2-р Програмын Тулгалтын Систем")

@app.get("/", response_class=HTMLResponse)
def get_ui():
    html_content = """
    <!DOCTYPE html>
    <html lang="mn">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Бараа Материалын Тулгалтын Систем</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; bg-color: #f9fafb; margin: 0; padding: 0; background-color: #f3f4f6; color: #1f2937; }
            .navbar { background-color: #ffffff; border-b: 1px solid #e5e7eb; padding: 15px 30px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
            .brand { font-size: 18px; font-weight: bold; color: #111827; display: flex; align-items: center; gap: 10px; }
            .user-info { font-size: 13px; color: #6b7280; font-weight: 500; }
            .container { max-width: 800px; mx-auto; margin: 40px auto; padding: 0 20px; }
            .header-section { text-align: center; margin-bottom: 40px; }
            .header-section h1 { font-size: 28px; font-weight: 800; color: #111827; margin-bottom: 10px; }
            .header-section p { font-size: 16px; color: #4b5563; margin: 0; }
            .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px; }
            @media (max-width: 640px) { .grid { grid-template-columns: 1fr; } }
            .card { background: #ffffff; padding: 25px; border-radius: 16px; border: 1px solid #e5e7eb; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
            .card-title { font-size: 16px; font-weight: 700; margin-bottom: 8px; display: flex; align-items: center; gap: 8px; color: #111827; }
            .card-desc { font-size: 12px; color: #9ca3af; margin-bottom: 15px; }
            .file-input { width: 100%; font-size: 14px; color: #4b5563; }
            .btn-submit { width: 100%; background-color: #2563eb; color: #ffffff; border: none; padding: 16px; border-radius: 14px; font-size: 16px; font-weight: bold; cursor: pointer; box-shadow: 0 4px 6px rgba(37, 99, 235, 0.2); transition: background 0.2s; display: flex; justify-content: center; align-items: center; gap: 10px; }
            .btn-submit:hover { background-color: #1d4ed8; }
        </style>
    </head>
    <body>
        <div class="navbar">
            <div class="brand">📊 ТУЛГАЛТЫН НЭГДСЭН СИСТЕМ</div>
            <div class="user-info">Байгууллага: Түмэн Төмөр Групп</div>
        </div>

        <div class="container">
            <div class="header-section">
                <h1>Бараа материалын орлого зарлагын тулгалт</h1>
                <p>Хоёр системийн Excel файлыг хооронд нь тулгаж, зөрүүг олох ухаалаг туслах</p>
            </div>

            <form action="/reconcile/" method="post" enctype="multipart/form-data">
                <div class="grid">
                    <!-- Diamond Card -->
                    <div class="card" style="border-top: 4px solid #2563eb;">
                        <div class="card-title">💎 Diamond Программ</div>
                        <div class="card-desc">Санхүүгийн системээс татсан орлого, зарлагын Excel файл</div>
                        <input type="file" name="diamond_file" required class="file-input"/>
                    </div>

                    <!-- 2nd App Card -->
                    <div class="card" style="border-top: 4px solid #7c3aed;">
                        <div class="card-title">📱 2-р Программ / Касс</div>
                        <div class="card-desc">Борлуулалтын систем эсвэл кассаас татсан Excel файл</div>
                        <input type="file" name="second_app_file" required class="file-input"/>
                    </div>
                </div>

                <button type="submit" class="btn-submit">
                    🔄 Тулгалт хийж, Зөрүүний Excel татах
                </button>
            </form>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/reconcile/")
async def reconcile_inventory(
    diamond_file: UploadFile = File(...),
    second_app_file: UploadFile = File(...)
):
    try:
        df_diamond = pd.read_excel(io.BytesIO(await diamond_file.read()))
        df_second = pd.read_excel(io.BytesIO(await second_app_file.read()))
        
        df_diamond['Огноо'] = pd.to_datetime(df_diamond['Огноо']).dt.strftime('%Y-%m-%d')
        df_second['Огноо'] = pd.to_datetime(df_second['Огноо']).dt.strftime('%Y-%m-%d')

        group_cols = ['Огноо', 'Барааны_Код']
        
        dia_cols = {col: 'sum' for col in ['Тоо_Хэмжээ', 'Өртөг'] if col in df_diamond.columns}
        sec_cols = {col: 'sum' for col in ['Тоо_Хэмжээ', 'Өртөг'] if col in df_second.columns}
        
        dia_grouped = df_diamond.groupby(group_cols, as_index=False).agg(dia_cols)
        sec_grouped = df_second.groupby(group_cols, as_index=False).agg(sec_cols)
        
        dia_grouped = dia_grouped.rename(columns={'Тоо_Хэмжээ': 'Diamond_Тоо', 'Өртөг': 'Diamond_Өртөг'})
        sec_grouped = sec_grouped.rename(columns={'Тоо_Хэмжээ': 'Апп2_Тоо', 'Өртөг': 'Апп2_Өртөг'})
        
        merged = pd.merge(dia_grouped, sec_grouped, on=group_cols, how='outer')
        
        for c in ['Diamond_Тоо', 'Diamond_Өртөг', 'Апп2_Тоо', 'Апп2_Өртөг']:
            merged[c] = merged[c].fillna(0) if c in merged.columns else 0
                
        merged['Тоо_Зөрүү'] = merged['Diamond_Тоо'] - merged['Апп2_Тоо']
        merged['Өртөг_Зөрүү'] = merged['Diamond_Өртөг'] - merged['Апп2_Өртөг']
        
        conditions = [
            (merged['Diamond_Тоо'] > 0) & (merged['Апп2_Тоо'] == 0),
            (merged['Апп2_Тоо'] > 0) & (merged['Diamond_Тоо'] == 0),
            (merged['Тоо_Зөрүү'] != 0) & (merged['Өртөг_Зөрүү'] == 0),
            (merged['Өртөг_Зөрүү'] != 0) & (merged['Тоо_Зөрүү'] == 0),
            (merged['Тоо_Зөрүү'] != 0) & (merged['Өртөг_Зөрүү'] != 0)
        ]
        
        choices = ["2-р Апп дээр гүйлгээ дутуу", "Diamond дээр гүйлгээ дутуу", "Зөвхөн Тоо хэмжээ зөрүүтэй", "Зөвхөн Өртөг үнэ зөрүүтэй", "Тоо болон Өртөг хоёулаа зөрүүтэй"]
        merged['Төлөв'] = np.select(conditions, choices, default="Таарсан")
        
        discrepancies = merged[merged['Төлөв'] != "Таарсан"].copy()
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            discrepancies.to_excel(writer, sheet_name='Тулгалтын Зөрүү', index=False)
        output.seek(0)
        
        return StreamingResponse(
            output, 
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=reconciliation_report.xlsx"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
