from fastapi import APIRouter, Request, HTTPException
from database import sdk, supabase

router = APIRouter(prefix="/pagos", tags=["Pagos"])

@router.post("/create-preference")
async def create_preference(request: Request):
    try:
        body = await request.json()
        reserva_data = {
            "evento_id": body.get("evento_id"),
            "nombre_cliente": body.get("nombre", "Cliente"),
            "estado_pago": "pendiente"
        }

        # 1. Crear reserva en Supabase
        res = supabase.table("reservas").insert(reserva_data).execute()
        reserva_id = res.data[0]['id']

        # 2. Configurar Preferencia MP
        preference_data = {
            "items": [{
                "title": f"Traslado: {body.get('nombre_evento', 'Concierto')}",
                "quantity": 1,
                "unit_price": float(body.get("precio")),
                "currency_id": "CLP"
            }],
            "external_reference": str(reserva_id),
            "back_urls": {
                "success": "https://van-concierto-front.vercel.app/",
                "failure": "https://van-concierto-front.vercel.app/",
                "pending": "https://van-concierto-front.vercel.app/"
            },
            "auto_return": "approved"
        }
        
        result = sdk.preference().create(preference_data)
        pref_id = result["response"]["id"]

        # 3. Actualizar reserva con ID de pago
        supabase.table("reservas").update({"preference_id": pref_id}).eq("id", reserva_id).execute()
        
        return {"id": pref_id}
        
    except Exception as e:
        print(f"Error en Pago: {e}")
        raise HTTPException(status_code=500, detail=str(e))