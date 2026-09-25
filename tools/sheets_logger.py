"""Registro en Google Sheets real (gspread) o CSV local como fallback."""
import csv
import os
from datetime import datetime, timezone
from pathlib import Path

CSV = Path(__file__).resolve().parent.parent / "data" / "sheets_log.csv"
HEADERS = ["fecha_utc", "tipo", "detalle", "monto", "fecha_ref", "destino"]


def _append_csv(row: dict):
    CSV.parent.mkdir(parents=True, exist_ok=True)
    new = not CSV.exists()
    with CSV.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADERS)
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in HEADERS})


def log_to_sheet(tipo: str, detalle: str, monto: str = "", fecha: str = "") -> dict:
    sa_json, sheet_id = os.getenv("GOOGLE_SA_JSON", "").strip(), os.getenv("GOOGLE_SHEET_ID", "").strip()
    if "/d/" in sheet_id:
        sheet_id = sheet_id.split("/d/")[1].split("/")[0]

    clean_tipo = (tipo or "prestamo").strip().lower()
    clean_detalle = (detalle or "1x Clean Code (Código Limpio) — Robert C. Martin (Fianza Ref: S/ 15.00 · Plazo: 7 días)").strip()
    clean_monto = (monto or "S/ 15.00").strip()
    clean_fecha = (fecha or datetime.now(timezone.utc).strftime("%Y-%m-%d")).strip()

    row = {
        "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "tipo": clean_tipo,
        "detalle": clean_detalle[:1000],
        "monto": clean_monto,
        "fecha_ref": clean_fecha,
        "destino": "csv_local"
    }

    if sa_json and sheet_id:
        try:
            import gspread
            from google.oauth2.service_account import Credentials
            scopes = ["https://www.googleapis.com/auth/spreadsheets"]
            creds = Credentials.from_service_account_file(sa_json, scopes=scopes)
            gc = gspread.authorize(creds)
            sh = gc.open_by_key(sheet_id).sheet1
            sh.append_row([row["fecha_utc"], clean_tipo, clean_detalle, clean_monto, clean_fecha])
            row["destino"] = f"google_sheet:{sheet_id[:8]}..."
            _append_csv(row)
            return {"ok": True, "mode": "sheets", "detail": f"Registrado en Google Sheet + espejo local. ({clean_tipo}: {clean_detalle[:80]})"}
        except Exception as e:
            row["destino"] = "csv_local (sheets_error)"
            _append_csv(row)
            return {"ok": False, "mode": "sheets_error", "detail": f"Falló Google Sheets ({str(e)[:300]}). Se guardó en CSV local."}

    _append_csv(row)
    return {
        "ok": True,
        "mode": "demo",
        "detail": f"Registro simulado en CSV local data/sheets_log.csv ({clean_tipo}: {clean_detalle[:80]})."
    }
