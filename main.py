from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
import pandas as pd
import io
import numpy as np

app = FastAPI(title="Diamond болон 2-р Програмын Тулгалтын Систем")

@app.post("/reconcile/")
async def reconcile_inventory(
    diamond_file: UploadFile = File(..., description="Diamond-оос татсан Excel"),
    second_app_file: UploadFile = File(..., description="2-р Програмын Excel")
):
    try:
        df_diamond = pd.read_excel(io.BytesIO(await diamond_file.read()))
        df_second = pd.read_excel(io.BytesIO(await second_app_file.read()))
        
        df_diamond['Огноо'] = pd.to_datetime(df_diamond['Огноо']).dt.strftime('%Y-%m-%d')
        df_second['Огноо'] = pd.to_datetime(df_second['Огноо']).dt.strftime('%Y-%m-%d')
        
        group_cols = ['Огноо', 'Барааны_Код']
        
        dia_grouped = df_diamond.groupby(group_cols, as_index=False).agg({
            'Тоо_Хэмжээ': 'sum',
            'Өртөг': 'sum'
        }).rename(columns={'Тоо_Хэмжээ': 'Diamond_Тоо', 'Өртөг': 'Diamond_Өртөг'})
        
        sec_grouped = df_second.groupby(group_cols, as_index=False).agg({
            'Тоо_Хэмжээ': 'sum',
            'Өртөг': 'sum'
        }).rename(columns={'Тоо_Хэмжээ': 'Апп2_Тоо', 'Өртөг': 'Апп2_Өртөг'})
        
        merged = pd.merge(dia_grouped, sec_grouped, on=group_cols, how='outer')
        
        fill_cols = ['Diamond_Тоо', 'Diamond_Өртөг', 'Апп2_Тоо', 'Апп2_Өртөг']
        merged[fill_cols] = merged[fill_cols].fillna(0)
        
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
            workbook  = writer.book
            worksheet = writer.sheets['Тулгалтын Зөрүү']
            worksheet.freeze_panes(1, 0)
            
        output.seek(0)
        
        return StreamingResponse(
            output, 
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=inventory_reconciliation_report.xlsx"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Алдаа гарлаа: {str(e)}")
