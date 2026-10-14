from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
import pandas as pd
import io
import numpy as np

app = FastAPI(title="Diamond reconciliation system")

@app.get("/")
def read_root():
    return {"status": "Систем амжилттай ажиллаж байна. Файл тулгахын тулд /docs руу орно уу."}

@app.post("/reconcile/")
async def reconcile_inventory(
    diamond_file: UploadFile = File(...),
    second_app_file: UploadFile = File(...)
):
    try:
        df_diamond = pd.read_excel(io.BytesIO(await diamond_file.read()))
        df_second = pd.read_excel(io.BytesIO(await second_app_file.read()))
        
        # Баганын нэрсийг шалгах, Огноог форматанд оруулах
        if 'Огноо' in df_diamond.columns and 'Огноо' in df_second.columns:
            df_diamond['Огноо'] = pd.to_datetime(df_diamond['Огноо']).dt.strftime('%Y-%m-%d')
            df_second['Огноо'] = pd.to_datetime(df_second['Огноо']).dt.strftime('%Y-%m-%d')
        else:
            raise HTTPException(status_code=400, detail="Файлуудад 'Огноо' багана олдсонгүй.")
            
        if 'Барааны_Код' not in df_diamond.columns or 'Барааны_Код' not in df_second.columns:
            raise HTTPException(status_code=400, detail="Файлуудад 'Барааны_Код' багана олдсонгүй.")

        group_cols = ['Огноо', 'Барааны_Код']
        
        # Тоо хэмжээ, Өртөг багана байгаа эсэхийг тооцож сумлах
        dia_cols = {col: 'sum' for col in ['Тоо_Хэмжээ', 'Өртөг'] if col in df_diamond.columns}
        sec_cols = {col: 'sum' for col in ['Тоо_Хэмжээ', 'Өртөг'] if col in df_second.columns}
        
        dia_grouped = df_diamond.groupby(group_cols, as_index=False).agg(dia_cols)
        sec_grouped = df_second.groupby(group_cols, as_index=False).agg(sec_cols)
        
        dia_grouped = dia_grouped.rename(columns={'Тоо_Хэмжээ': 'Diamond_Тоо', 'Өртөг': 'Diamond_Өртөг'})
        sec_grouped = sec_grouped.rename(columns={'Тоо_Хэмжээ': 'Апп2_Тоо', 'Өртөг': 'Апп2_Өртөг'})
        
        merged = pd.merge(dia_grouped, sec_grouped, on=group_cols, how='outer')
        
        for c in ['Diamond_Тоо', 'Diamond_Өртөг', 'Апп2_Тоо', 'Апп2_Өртөг']:
            if c in merged.columns:
                merged[c] = merged[c].fillna(0)
            else:
                merged[c] = 0
                
        merged['Тоо_Зөрүү'] = merged['Diamond_Тоо'] - merged['Апп2_Тоо']
        merged['Өртөг_Зөрүү'] = merged['Diamond_Өртөг'] - merged['Апп2_Өртөг']
        
        conditions = [
            (merged['Diamond_Тоо'] > 0) & (merged['Апп2_Тоо'] == 0),
            (merged['Апп2_Тоо'] > 0) & (merged['Diamond_Тоо'] == 0),
            (merged['Тоо_Зөрүү'] != 0) & (merged['Өртөг_Зөрүү'] == 0),
            (merged['Өртөг_Зөрүү'] != 0) & (merged['Тоо_Зөрүү'] == 0),
            (merged['Тоо_Зөрүү'] != 0) & (merged['Өртөг_Зөрүү'] != 0)
        ]
        
        choices = [
            "2-р Апп дээр гүйлгээ дутуу",
            "Diamond дээр гүйлгээ дутуу",
            "Зөвхөн Тоо хэмжээ зөрүүтэй",
            "Зөвхөн Өртөг үнэ зөрүүтэй",
            "Тоо болон Өртөг хоёулаа зөрүүтэй"
        ]
        
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
