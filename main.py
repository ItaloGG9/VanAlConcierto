import os
import qrcode
from io import BytesIO
from fastapi import FastAPI, Request, HTTPException
from mercadopago import SDK
from supabase import create_client, Client
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

# 1. Cargamos las variables PRIMERO
load_dotenv()

# 2. Creamos la APP
app = FastAPI(title="VanAlConcierto API")

# 3. Configuramos CORS (Después de crear la app)
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

@app.get("/")
def read_root():
    return {"status": "Servidor Funcionando", "project": "VanAlConcierto"}

# --- FLUJO MERCADO PAGO ---

@app.post("/create-preference")
async def create_preference(viaje_id: str, nombre: str, precio: int):
    try:
        # 1. Insertar ticket
        res = supabase.table("tickets").insert({
            "viaje_id": viaje_id,
            "nombre_pasajero": nombre,
            "correo_pasajero": "test@italo.cl",
            "pagado": False
        }).execute()
        
        ticket_id = res.data[0]['id']

        # 2. Configurar Mercado Pago
        preference_data = {
            "items": [
                {
                    "title": f"Pasaje ID: {viaje_id}",
                    "quantity": 1,
                    "unit_price": float(precio),
                    "currency_id": "CLP"
                }
            ],
            "external_reference": str(ticket_id)
        }
        
        result = sdk.preference().create(preference_data)
        
        if "response" in result and "init_point" in result["response"]:
            return {
                "init_point": result["response"]["init_point"],
                "ticket_id": ticket_id
            }
        else:
            print("Error MP:", result)
            raise HTTPException(status_code=400, detail=f"MP Error: {result.get('status')}")

    except Exception as e:
        print(f"Error completo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- FLUJO TRANSFERENCIA ---

@app.post("/solicitar-transferencia")
async def solicitar_transferencia(viaje_id: str, nombre: str):
    """Registra la intención de pago por transferencia"""
    res = supabase.table("tickets").insert({
        "viaje_id": viaje_id,
        "nombre_pasajero": nombre,
        "correo_pasajero": "italo@prueba.com",
        "pagado": False
    }).execute()
    
    return {"message": "Ticket registrado. Por favor envía el comprobante.", "ticket_id": res.data[0]['id']}

# --- WEBHOOK ---

@app.post("/webhook-mp")
async def webhook_mp(request: Request):
    data = await request.json()
    return {"status": "received"}