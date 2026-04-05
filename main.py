import os
from fastapi import FastAPI, Request, HTTPException
from mercadopago import SDK
from supabase import create_client, Client
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 1. Carga de variables
load_dotenv()

app = FastAPI(title="Código Visual API - Panel Admin")

# 2. Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://van-concierto-front.vercel.app"], # En producción cambia esto por tu URL de Vercel
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuración de Clientes
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

sdk = SDK(MP_ACCESS_TOKEN)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Modelo para recibir nuevos eventos desde el Front
class NuevoEvento(BaseModel):
    titulo: str
    fecha: str
    lugar: str
    precio: int
    imagen_url: str
    descripcion: Optional[str] = None

@app.get("/")
def read_root():
    return {"status": "Servidor Funcionando", "project": "Código Visual"}

# --- APARTADO DE ADMINISTRADOR (GESTIÓN DE EVENTOS) ---

@app.get("/eventos")
async def obtener_eventos():
    """Trae todos los eventos activos de Supabase"""
    try:
        res = supabase.table("eventos").select("*").eq("activo", True).execute()
        return res.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/nuevo-evento")
async def crear_evento(evento: NuevoEvento):
    """Agrega un nuevo concierto al mostrador"""
    try:
        res = supabase.table("eventos").insert({
            "titulo": evento.titulo,
            "fecha": evento.fecha,
            "lugar": evento.lugar,
            "precio": evento.precio,
            "imagen_url": evento.imagen_url
        }).execute()
        return {"message": "Evento creado con éxito", "data": res.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/admin/eliminar-evento/{evento_id}")
async def eliminar_evento(evento_id: int):
    """Desactiva un evento (Soft Delete)"""
    try:
        # En lugar de borrarlo, lo ponemos como activo=false
        res = supabase.table("eventos").update({"activo": False}).eq("id", evento_id).execute()
        return {"message": "Evento eliminado del mostrador"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- FLUJO MERCADO PAGO (ACTUALIZADO A TUS TABLAS SQL) ---

@app.post("/create-preference")
async def create_preference(evento_id: int, nombre: str, precio: int):
    try:
        # 1. Insertar en la tabla 'reservas' (la que creamos con SQL)
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
                    "title": f"Reserva Código Visual - Evento {evento_id}",
                    "quantity": 1,
                    "unit_price": float(precio),
                    "currency_id": "CLP"
                }
            ],
            "external_reference": str(reserva_id)
        }
        
        result = sdk.preference().create(preference_data)
        
        if "response" in result:
            # Actualizamos la reserva con el preference_id de MP
            pref_id = result["response"]["id"]
            supabase.table("reservas").update({"preference_id": pref_id}).eq("id", reserva_id).execute()
            
            return {
                "id": pref_id, # Enviamos el ID para el componente Wallet de React
                "init_point": result["response"]["init_point"]
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- WEBHOOK ---
@app.post("/webhook-mp")
async def webhook_mp(request: Request):
    # Aquí es donde MP te avisará cuando el pago pase de 'pendiente' a 'aprobado'
    return {"status": "received"}