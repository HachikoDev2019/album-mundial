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

# ── Figuritas FALTANTES por país ────────────────────────────
INITIAL_DATA = {
    "México":           [3, 7, 12, 14, 15, 16, 20],
    "Corea del Sur":    [5, 20],
    "República Checa":  [13, 14],
    "Canadá":           [1, 2, 6, 10, 17, 18],
    "Bosnia":           [1],
    "Qatar":            [4],
    "Brasil":           [3, 5, 12],
    "Marruecos":        [19],
    "Escocia":          [6, 8, 11, 16, 17, 18],
    "Estados Unidos":   [5, 6, 9, 10, 12],
    "Paraguay":         [14],
    "Australia":        [4, 8, 9, 18],
    "Turquía":          [9, 13],
    "Alemania":         [3],
    "Curazao":          [1, 5, 9, 18],
    "Costa de Marfil":  [2, 3, 6, 8, 9, 11, 14, 15, 16, 20],
    "Ecuador":          [1, 5, 8, 9, 10, 19],
    "Países Bajos":     [5, 9, 14],
    "Japón":            [3],
    "Suecia":           [20],
    "Túnez":            [7, 19],
    "Bélgica":          [6, 14, 16, 20],
    "Egipto":           [1, 6],
    "Irán":             [5, 9, 13, 14, 18],
    "Nueva Zelanda":    [13],
    "España":           [3, 7, 11],
    "Cabo Verde":       [4, 8, 12, 17],
    "Arabia Saudita":   [6, 7, 9],
    "Francia":          [9, 14, 16, 20],
    "Irak":             [11],
    "Argentina":        [4, 11, 16, 20],
    "Algeria":          [2, 6, 9, 10, 18, 19],
    "Austria":          [6, 7, 8],
    "Jordania":         [13],
    "Portugal":         [6, 10, 15, 16, 20],
    "Congo":            [16],
    "Colombia":         [5, 8, 14, 17, 18, 19],
    "Croacia":          [4],
    "Ghana":            [12, 17],
    "Panamá":           [5],
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
    # Insert missing stickers without touching existing quantities
    for team, numbers in INITIAL_DATA.items():
        for num in numbers:
            cursor.execute(
                'INSERT OR IGNORE INTO stickers (team, number, quantity) VALUES (?, ?, 0)',
                (team, num)
            )
    # Remove any sticker not in INITIAL_DATA (limpia países inventados)
    valid_pairs = [(t, n) for t, nums in INITIAL_DATA.items() for n in nums]
    cursor.execute('SELECT team, number FROM stickers')
    existing = cursor.fetchall()
    for row in existing:
        if (row['team'], row['number']) not in valid_pairs:
            cursor.execute('DELETE FROM stickers WHERE team=? AND number=?', (row['team'], row['number']))
    conn.commit()
    conn.close()


init_db()


class AdjustRequest(BaseModel):
    team: str
    number: int
    delta: int


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT team, number, quantity FROM stickers ORDER BY team, number')
    rows = cursor.fetchall()
    conn.close()

    equipos = {}
    total_stickers = 0
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
        elif quantity > 1:
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
    cursor.execute('SELECT team, number FROM stickers WHERE quantity = 0 ORDER BY team, number')
    missing_rows = cursor.fetchall()
    cursor.execute('SELECT team, number, quantity FROM stickers WHERE quantity > 1 ORDER BY team, number')
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