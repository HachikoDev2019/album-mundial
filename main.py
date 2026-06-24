from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import sqlite3
import urllib.parse

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

DB_FILE = "album.db"

# Datos iniciales completos — Lista de países y sus figuritas faltantes
INITIAL_DATA = {
    "México": [3, 7, 8, 10, 11, 12, 14, 15, 16, 19, 20],
    "Sudáfrica": [3, 7, 8, 9, 11, 12, 14, 16, 17, 18, 19, 20],
    "Corea del Sur": [3, 4, 5, 6, 7, 8, 16, 20],
    "Panamá": [1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
    "Argentina": [1, 5, 9, 13, 17],
    "Brasil": [2, 4, 6, 8, 10, 12, 14, 16, 18, 20],
    "España": [1, 3, 5, 7, 11, 15, 19],
    "Francia": [2, 6, 10, 14, 18],
    "Alemania": [1, 4, 7, 10, 13, 16, 19],
    "Portugal": [3, 6, 9, 12, 15, 18],
    "Uruguay": [2, 5, 8, 11, 14, 17, 20],
    "Colombia": [1, 3, 6, 9, 12, 15, 18],
    "Perú": [2, 4, 7, 10, 13, 16, 19, 20],
    "Chile": [1, 5, 9, 13, 17],
    "Ecuador": [3, 6, 9, 12, 15, 18],
    "Venezuela": [2, 5, 8, 11, 14, 17],
    "Bolivia": [1, 4, 7, 10, 13, 16],
    "Paraguay": [3, 6, 9, 12, 15, 18],
    "Estados Unidos": [1, 2, 5, 8, 11, 14, 17, 20],
    "Canadá": [3, 6, 9, 12, 15, 18],
    "Costa Rica": [2, 5, 8, 11, 14, 17],
    "Jamaica": [1, 4, 7, 10, 13, 16, 19],
    "Honduras": [2, 5, 8, 11, 14, 17, 20],
    "El Salvador": [3, 6, 9, 12, 15, 18],
    "Guatemala": [1, 4, 7, 10, 13, 16],
    "Trinidad y Tobago": [2, 5, 8, 11, 14, 17],
    "Marruecos": [1, 3, 5, 7, 9, 11, 13, 15, 17, 19],
    "Nigeria": [2, 4, 6, 8, 10, 12, 14, 16, 18, 20],
    "Senegal": [1, 3, 5, 7, 9, 11, 15, 19],
    "Egipto": [2, 4, 6, 8, 12, 16, 20],
    "Camerún": [1, 5, 9, 13, 17],
    "Costa de Marfil": [2, 6, 10, 14, 18],
    "Ghana": [3, 7, 11, 15, 19],
    "Túnez": [4, 8, 12, 16, 20],
    "Mali": [1, 5, 9, 13, 17],
    "Japón": [2, 4, 6, 8, 10, 14, 18],
    "Arabia Saudita": [1, 3, 7, 11, 15, 19],
    "Iran": [2, 6, 10, 14, 18],
    "Australia": [3, 7, 11, 15, 19],
    "Nueva Zelanda": [1, 5, 9, 13, 17, 20],
    "Inglaterra": [2, 4, 8, 12, 16, 20],
    "Países Bajos": [1, 5, 9, 13, 17],
    "Italia": [3, 6, 9, 12, 15, 18],
    "Bélgica": [2, 5, 8, 11, 14, 17, 20],
    "Croacia": [1, 4, 7, 10, 13, 16, 19],
    "Serbia": [2, 5, 8, 11, 14, 17],
    "Suiza": [3, 6, 9, 12, 15, 18],
    "Dinamarca": [1, 4, 7, 10, 13, 16],
    "Austria": [2, 5, 8, 11, 14, 17, 20],
    "Polonia": [3, 6, 9, 12, 15, 18],
    "Suecia": [1, 4, 7, 10, 13, 16, 19],
    "Turquía": [2, 5, 8, 11, 14, 17],
    "Ucrania": [3, 6, 9, 12, 15, 18],
    "Rumania": [1, 4, 7, 10, 13, 16, 20],
    "República Checa": [2, 5, 8, 11, 14, 17],
    "Eslovaquia": [3, 6, 9, 12, 15, 18],
    "Albania": [1, 4, 7, 10, 13, 16, 19],
    "Georgia": [2, 5, 8, 11, 14, 17],
    "Eslovenia": [3, 6, 9, 12, 15, 18],
    "Hungría": [1, 4, 7, 10, 13, 16],
}


def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stickers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team TEXT NOT NULL,
            number INTEGER NOT NULL,
            quantity INTEGER DEFAULT 0,
            UNIQUE(team, number)
        )
    ''')
    cursor.execute('SELECT COUNT(*) as cnt FROM stickers')
    if cursor.fetchone()['cnt'] == 0:
        for team, numbers in INITIAL_DATA.items():
            for num in numbers:
                cursor.execute(
                    'INSERT OR IGNORE INTO stickers (team, number, quantity) VALUES (?, ?, 0)',
                    (team, num)
                )
    conn.commit()
    conn.close()


init_db()


class AdjustRequest(BaseModel):
    team: str
    number: int
    delta: int  # +1 o -1


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT team, number, quantity FROM stickers ORDER BY team, number')
    rows = cursor.fetchall()
    conn.close()

    equipos = {}
    total_stickers = 0
    total_collected = 0
    total_missing = 0
    total_repeated = 0

    for row in rows:
        team, number, quantity = row['team'], row['number'], row['quantity']
        if team not in equipos:
            equipos[team] = []
        equipos[team].append({"number": number, "quantity": quantity})
        total_stickers += 1
        if quantity == 0:
            total_missing += 1
        elif quantity == 1:
            total_collected += 1
        else:
            total_collected += 1
            total_repeated += (quantity - 1)

    collected_count = total_stickers - total_missing
    progress_pct = round((collected_count / total_stickers * 100) if total_stickers else 0)

    equipos_list = [{"nombre": k, "figuritas": v} for k, v in equipos.items()]

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "equipos": equipos_list,
            "total_stickers": total_stickers,
            "total_missing": total_missing,
            "total_repeated": total_repeated,
            "collected_count": collected_count,
            "progress_pct": progress_pct,
        }
    )


@app.post("/adjust")
async def adjust_sticker(req: AdjustRequest):
    if req.delta not in (1, -1):
        raise HTTPException(status_code=400, detail="Delta must be +1 or -1")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT quantity FROM stickers WHERE team = ? AND number = ?',
        (req.team, req.number)
    )
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Figurita no encontrada")

    new_qty = max(0, row['quantity'] + req.delta)
    cursor.execute(
        'UPDATE stickers SET quantity = ? WHERE team = ? AND number = ?',
        (new_qty, req.team, req.number)
    )
    conn.commit()
    conn.close()

    return {"status": "ok", "quantity": new_qty}


@app.get("/export/whatsapp")
async def export_whatsapp():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT team, number FROM stickers WHERE quantity = 0 ORDER BY team, number'
    )
    missing_rows = cursor.fetchall()

    cursor.execute(
        'SELECT team, number, quantity FROM stickers WHERE quantity > 1 ORDER BY team, number'
    )
    repeated_rows = cursor.fetchall()
    conn.close()

    lines = ["⚽ *MUNDIAL 2026 — Mis Figuritas* ⚽\n"]

    if missing_rows:
        lines.append("📋 *FALTANTES:*")
        missing_by_team = {}
        for row in missing_rows:
            missing_by_team.setdefault(row['team'], []).append(str(row['number']))
        for team, nums in missing_by_team.items():
            lines.append(f"  🏳️ {team}: {', '.join(nums)}")
    else:
        lines.append("✅ ¡No te faltan figuritas!")

    lines.append("")

    if repeated_rows:
        lines.append("🔁 *REPETIDAS (para cambiar):*")
        repeated_by_team = {}
        for row in repeated_rows:
            repeated_by_team.setdefault(row['team'], []).append(
                f"{row['number']}×{row['quantity'] - 1}"
            )
        for team, nums in repeated_by_team.items():
            lines.append(f"  🏳️ {team}: {', '.join(nums)}")
    else:
        lines.append("🔁 Sin repetidas por ahora.")

    lines.append("\n_Enviado desde Álbum 2026 📱_")

    text = "\n".join(lines)
    encoded = urllib.parse.quote(text)
    return JSONResponse({"url": f"https://wa.me/?text={encoded}", "text": text})