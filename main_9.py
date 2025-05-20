import pandas as pd
from datetime import datetime, timedelta
import telegram
import asyncio
from db_connection import connect_aep_DB

TOKEN = '7501421824:AAFbTjHuJ8e1vO46KGnWCYu8iqqZbC8PRqk'
CHAT_ID = '-1002620433808'

def fetch_data():
    today = datetime.now().strftime('%Y/%m/%d')
    query = f"""
    SELECT
        SOTRNH.DOCDATE, 
        SOTRNH_PRINT.DT, 
        SOTRNH.DOCNO, 
        SOTRNH.CUSTNO, 
        SOTRNH_PRINT.CUSTNAME, 
        CAST(SOTRNH.SHIPLINE AS NVARCHAR(MAX)) AS Branch, 
        SOTRNH.SMCODE, 
        ARSALMAN.NAME, 
        CAST(SOTRNH_PRINT.SHIPTO AS NVARCHAR(MAX)) AS ShipAddress, 
        CAST(SOTRNH_PRINT.USERNAME AS NVARCHAR(MAX)) AS UserName
    FROM dbo.SOTRNH_PRINT
    LEFT JOIN dbo.SOTRNH
        ON SOTRNH_PRINT.COCODE = SOTRNH.COCODE AND
           SOTRNH_PRINT.DT = SOTRNH.DT AND
           SOTRNH_PRINT.DOCNO = SOTRNH.DOCNO
    LEFT JOIN dbo.ARSALMAN
        ON SOTRNH.COCODE = ARSALMAN.COCODE AND
           SOTRNH.SMCODE = ARSALMAN.SMCODE
    WHERE SOTRNH_PRINT.COCODE = 'AEPC'
        AND ARSALMAN.COCODE = 'AEPC'
        AND SOTRNH.COCODE = 'AEPC'
        AND SOTRNH_PRINT.DT = 'TX'
        AND SOTRNH.DT = 'TX'
        AND SOTRNH.DOCDATE BETWEEN ('{today}') AND ('{today}')
    GROUP BY
        SOTRNH.DOCDATE, 
        SOTRNH_PRINT.DT, 
        SOTRNH.DOCNO, 
        SOTRNH.CUSTNO, 
        SOTRNH_PRINT.CUSTNAME, 
        SOTRNH.SMCODE, 
        ARSALMAN.NAME, 
        CAST(SOTRNH_PRINT.USERNAME AS NVARCHAR(MAX)), 
        CAST(SOTRNH.SHIPLINE AS NVARCHAR(MAX)),
        CAST(SOTRNH_PRINT.SHIPTO AS NVARCHAR(MAX))
    ORDER BY SOTRNH.DOCNO ASC
    """
    conn = connect_aep_DB()
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def generate_summary_text(df):
    now = datetime.now()
    today = datetime.now()
    date_str = today.strftime("%d/%m/%Y")
    datetime_str = now.strftime("%d/%m/%Y %H:%M:%S")
    total_orders = len(df)

    sales_group = df.groupby(['SMCODE', 'NAME']).size().reset_index(name='OrderCount')
    sales_group = sales_group.sort_values(by='OrderCount', ascending=False)

    regional_codes = ['10370', '10362', '10354', '10450', '10460']
    reg_sales = sales_group[sales_group['SMCODE'].astype(str).isin(regional_codes)]
    bkk_sales = sales_group[~sales_group['SMCODE'].astype(str).isin(regional_codes)]

    branch_group = df.groupby('Branch').size().reset_index(name='OrderCount')
    branch_group = branch_group.sort_values(by='OrderCount', ascending=False)

    text = f"""📊 รายงานสรุปจำนวนบิลประจำวัน 📊
🗓 วันที่ออเดอร์: {date_str}
📦 จำนวนออเดอร์ทั้งหมด: {total_orders} บิล
=============================
"""

#👨‍💼 สรุปจำนวนบิลตามพนักงานขาย 👩‍💼
#*BKK Sales*
#    for _, row in bkk_sales.iterrows():
#        text += f"\n{row['SMCODE']} | {row['NAME']:<10} | {row['OrderCount']} บิล"

#    text += "\n\n*Regional Sales*"
#    for _, row in reg_sales.iterrows():
#        text += f"\n{row['SMCODE']} | {row['NAME']:<10} | {row['OrderCount']} บิล"

    text += "🏢 สรุปจำนวนบิลตาม สาขา"
    for _, row in branch_group.iterrows():
        text += f"\n📍 {row['Branch']}: {row['OrderCount']} บิล"

    text += f"\n=============================\n📄 เอกสารสรุปประจำวันตามไฟล์แนบ \n🤖 AUTOBOT - AEPTHAILAND \n🗓GetDate : {datetime_str}"
    return text

def export_to_excel(df):
    file_name = f"Sales_Report_{datetime.now().strftime('%Y%m%d')}.xlsx"
    df.to_excel(file_name, index=False, engine='openpyxl')
    return file_name

async def send_to_telegram(file_path, caption):
    bot = telegram.Bot(token=TOKEN)
    # 📨 ส่งข้อความแยก
    await bot.send_message(chat_id=CHAT_ID, text=caption)
    # 📎 แล้วค่อยส่งไฟล์
    with open(file_path, 'rb') as file:
        await bot.send_document(chat_id=CHAT_ID, document=file)

async def job():
    print(f"⏳ เริ่มสร้างรายงาน: {datetime.now().strftime('%H:%M:%S')}")
    df = fetch_data()
    if not df.empty:
        file_path = export_to_excel(df)
        summary_text = generate_summary_text(df)
        await send_to_telegram(file_path, summary_text)
        print("✅ ส่งรายงานเรียบร้อย")
    else:
        print("⚠️ ไม่มีข้อมูลออเดอร์ในวันนี้")

def run_async_job():
    asyncio.run(job())

# ตั้งเวลาให้รันทุกวันเวลา 16:00 น.
if __name__ == "__main__":
    print("📡 เริ่มการส่งรายงานทันทีเมื่อเปิดไฟล์")
    run_async_job()