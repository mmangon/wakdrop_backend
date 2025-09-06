from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from core.database import engine, Base
from routers import builds, items, cdn, drops, admin, search, zones_admin

# Créer les tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="WakDrop API",
    description="API pour analyser les builds Wakfu et générer des roadmaps de farm optimisées",
    version="0.4.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, remplacer par l'URL du frontend Vue.js
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(builds.router)
app.include_router(items.router)
app.include_router(cdn.router)
app.include_router(drops.router)
app.include_router(admin.router)
app.include_router(search.router)
app.include_router(zones_admin.router)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return {
        "message": "WakDrop API is running", 
        "version": "0.4.0",
        "docs": "/docs",
        "endpoints": {
            "builds": "/builds",
            "items": "/items", 
            "cdn": "/cdn",
            "drops": "/drops",
            "search": "/search",
            "zones_admin": "/admin/zones",
            "zones_interface": "/static/admin_zones.html"
        }
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)