from fastapi import APIRouter, HTTPException, Depends
from database import supabase
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/admin", tags=["Administración"])

# --- MODELOS DE DATOS ---
class UpdateEvento(BaseModel):
    titulo: Optional[str] = None
    precio: Optional[int] = None
    descripcion: Optional[str] = None
    imagen_url: Optional[str] = None
    activo: Optional[bool] = None

# --- ENDPOINTS ---

@router.get("/reservas")
async def ver_reservas():
    """Para que veas quién ha intentado pagar y el estado de sus reservas"""
    try:
        res = supabase.table("reservas").select("*, eventos(titulo)").order("created_at", desc=True).execute()
        return res.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/editar-evento/{evento_id}")
async def editar_evento(evento_id: int, datos: UpdateEvento):
    """Permite actualizar solo los campos que envíes (ej: solo el precio)"""
    try:
        # Filtramos solo los campos que no son None
        update_data = {k: v for k, v in datos.dict().items() if v is not None}
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No se enviaron datos para actualizar")

        res = supabase.table("eventos").update(update_data).eq("id", evento_id).execute()
        return {"message": "Evento actualizado", "data": res.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def obtener_metricas():
    """Un pequeño resumen para tu dashboard"""
    try:
        total_eventos = supabase.table("eventos").select("id", count="exact").neq("activo", False).execute()
        total_reservas = supabase.table("reservas").select("id", count="exact").execute()
        
        return {
            "eventos_activos": total_eventos.count,
            "total_reservas_historicas": total_reservas.count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))