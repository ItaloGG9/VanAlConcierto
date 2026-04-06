from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import eventos, pagos, admin # <--- Importar admin

app = FastAPI(title="VanAlConcierto API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar las rutas
app.include_router(eventos.router)
app.include_router(pagos.router)
app.include_router(admin.router) # <--- Nueva ruta registrada

@app.get("/")
def home():
    return {"status": "Online", "agency": "Código Visual"}