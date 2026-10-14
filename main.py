from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
import pandas as pd
import io
import numpy as np

app = FastAPI(title="Diamond болон 2-р Програмын Тулгалтын Систем")

# 1. Хэрэглэгчид харагдах гоё дизайнтай нүүр хуудас (HTML + Tailwind CSS)
@app.get("/", response_class=HTMLResponse)
def get_ui():
    html_content = """
    <!DOCTYPE html>
    <html lang="mn">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Бараа Материалын Тулгалтын Систем</title>
        <script src="https://tailwindcss.com"></script>
    </head>
    <body class="bg-gray-50 font-sans antialiased text-gray-800">
        <!-- Толгой хэсэг -->
        <header class="bg-white border-b border-gray-200 sticky top-0 z-50">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
                <div class="flex items-center space-x-3">
                    <span class="text-2xl">📊</span>
                    <span class="font-bold text-lg tracking-tight text-gray-900">ТУЛГАЛТЫН НЭГДСЭН СИСТЕМ</span>
                </div>
                <div class="text-sm text-gray-500 font-medium">Хэрэглэгч: Түмэн Төмөр Групп</div>
            </div>
        </header>

        <!-- Үндсэн хэсэг -->
        <main class="max-w-4xl mx-auto px-4 py-12">
            <div class="text-center mb-10">
                <h1 class="text-3xl font-extrabold text-gray-900 sm:text-4xl">Бараа материалын орлого зарлагын тулгалт</h1>
                <p class="mt-3 text-lg text-gray-500">Diamond санхүүгийн программ болон 2-р аппликейшны Excel файлыг хооронд нь тулгаж, зөрүүг олох систем</p>
            </div>

            <form action="/reconcile/" method="post" enctype="multipart/form-data" class="space-y-6">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <!-- Diamond Файл оруулах -->
                    <div class="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm hover:shadow-md transition-shadow">
                        <div class="flex items-center space-x-3 mb-4">
                            <div class="p-2 bg-blue-50 text-blue-600 rounded-lg text-xl">💎</div>
                            <h2 class="text-lg font-bold text-gray-900">Diamond Программ</h2>
                        </div>
                        <p class="text-xs text-gray-400 mb-3">Diamond системээс татсан орлого, зарлагын Excel файл</p>
                        <input type="file" name="diamond_file" required class="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 cursor-pointer"/>
                    </div>

                    <!-- 2-р Програм Файл оруулах -->
                    <div class="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm hover:shadow-md transition-shadow">
                        <div class="flex items-center space-x-3 mb-4">
                            <div class="p-2 bg-purple-50 text-purple-600 rounded-lg text-xl">📱</div>
                            <h2 class="text-lg font-bold text-gray-900">2-р Программ / Касс</h2>
                        </div>
                        <p class="text-xs text-gray-400 mb-3">Борлуулалтын систем эсвэл кассаас татсан Excel файл</p>
                        <input type="file" name="second_app_file" required class="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-semibold file:bg-purple-50 file:text-purple-700 hover:file:bg-purple-100 cursor-pointer"/>
                    </div>
                </div>

                <!-- Идэвхжүүлэх товч -->
                <div class="pt-4">
                    <button type="submit" class="w-full flex justify-center py-4 px-6 border border-transparent rounded-2xl shadow-sm text-lg font-bold text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors">
                        🔄 Тулгалт хийж, Зөрүүний Excel татах
                    </button>
                </div>
            </form>
        </main>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# 2. Арын албаны тулгалт хийх логик (Хэвээрээ үлдэнэ)
@app.post("/reconcile/")
async def reconcile_inventory(
    diamond_file: UploadFile = File(...),
    second_app_file: UploadFile = File(...)
):
    try:
        df_diamond = pd.read_excel(io.BytesIO(await diamond_file.read()))
        df_second = pd.read_excel(io.BytesIO(await second_app_file.read()))
        
        # Баганын нэрсийг шалгаж, форматанд оруулах
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
