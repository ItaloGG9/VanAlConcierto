from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import supabase

router = APIRouter(prefix="/eventos", tags=["Eventos"])

class NuevoEvento(BaseModel):
    titulo: str
    fecha: str
    lugar: str
    precio: int
    imagen_url: str
    descripcion: Optional[str] = None

@router.get("/")
async def obtener_eventos():
    try:
        res = supabase.table("eventos").select("*").neq("activo", False).execute()
        return res.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/admin/nuevo")
async def crear_evento(evento: NuevoEvento):
    try:
        res = supabase.table("eventos").insert({
            "titulo": evento.titulo,
            "fecha": evento.fecha,
            "lugar": evento.lugar,
            "precio": evento.precio,
            "imagen_url": evento.imagen_url,
            "descripcion": evento.descripcion,
            "activo": True
        }).execute()
        return {"message": "Evento creado", "data": res.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/admin/eliminar/{evento_id}")
async def eliminar_evento(evento_id: int):
    try:
        supabase.table("eventos").update({"activo": False}).eq("id", evento_id).execute()
        return {"message": "Evento marcado como inactivo"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))