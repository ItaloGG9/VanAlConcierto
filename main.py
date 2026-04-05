import os
from fastapi import FastAPI, Request, HTTPException
from mercadopago import SDK
from supabase import create_client, Client
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional # <--- FALTA ESTA IMPORTACIÓN

# 1. Carga de variables
load_dotenv()

app = FastAPI(title="VanAlConcierto API")

# 2. Configuración de CORS - Permitimos todo para evitar bloqueos
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuración de Clientes
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

sdk = SDK(MP_ACCESS_TOKEN)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Modelo para recibir nuevos eventos
class NuevoEvento(BaseModel):
    titulo: str
    fecha: str
    lugar: str
    precio: int
    imagen_url: str
    descripcion: Optional[str] = None

@app.get("/")
def read_root():
    return {"status": "Servidor Funcionando", "project": "VanAlConcierto"}

# --- GESTIÓN DE EVENTOS ---

@app.get("/eventos")
async def obtener_eventos():
    try:
        # Traemos los eventos que NO han sido eliminados (soft delete)
        res = supabase.table("eventos").select("*").neq("activo", False).execute()
        return res.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/nuevo-evento")
async def crear_evento(evento: NuevoEvento):
    try:
        res = supabase.table("eventos").insert({
            "titulo": evento.titulo,
            "fecha": evento.fecha,
            "lugar": evento.lugar,
            "precio": evento.precio,
            "imagen_url": evento.imagen_url, # <--- AGREGADA COMA FALTA AQUÍ
            "descripcion": evento.descripcion,
            "activo": True
        }).execute()
        return {"message": "Evento creado con éxito", "data": res.data}
    except Exception as e:
        print(f"Error insertando: {e}") # Para ver el error en los logs de Railway
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/admin/eliminar-evento/{evento_id}")
async def eliminar_evento(evento_id: int):
    try:
        # Marcamos como inactivo (Soft Delete)
        res = supabase.table("eventos").update({"activo": False}).eq("id", evento_id).execute()
        return {"message": "Evento eliminado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- MERCADO PAGO ---

@app.post("/create-preference")
async def create_preference(request: Request):
    try:
        # Recibimos los datos como JSON para evitar errores de tipo
        body = await request.json()
        evento_id = body.get("evento_id")
        precio = body.get("precio")
        nombre = body.get("nombre", "Cliente")

        # 1. Insertar reserva inicial
        res = supabase.table("reservas").insert({
            "evento_id": evento_id,
            "nombre_cliente": nombre,
            "estado_pago": "pendiente"
        }).execute()
        
        reserva_id = res.data[0]['id']

        # 2. Configurar Mercado Pago
        preference_data = {
            "items": [
                {
                    "title": f"Traslado VanAlConcierto - ID {evento_id}",
                    "quantity": 1,
                    "unit_price": float(precio),
                    "currency_id": "CLP"
                }
            ],
            "external_reference": str(reserva_id),
            "back_urls": {
                "success": "https://van-concierto-front.vercel.app/",
                "failure": "https://van-concierto-front.vercel.app/",
                "pending": "https://van-concierto-front.vercel.app/"
            },
            "auto_return": "approved"
        }
        
        result = sdk.preference().create(preference_data)
        
        if "response" in result:
            pref_id = result["response"]["id"]
            supabase.table("reservas").update({"preference_id": pref_id}).eq("id", reserva_id).execute()
            return {"id": pref_id}
        
    except Exception as e:
        print(f"Error MP: {e}")
        raise HTTPException(status_code=500, detail=str(e))