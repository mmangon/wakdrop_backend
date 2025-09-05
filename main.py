from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.database import engine, Base
from routers import builds, items, cdn

# Créer les tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="WakDrop API",
    description="API pour analyser les builds Wakfu et générer des roadmaps de farm",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(builds.router)
app.include_router(items.router)
app.include_router(cdn.router)

@app.get("/")
async def root():
    return {
        "message": "WakDrop API is running", 
        "version": "0.1.0",
        "docs": "/docs",
        "endpoints": {
            "builds": "/builds",
            "items": "/items", 
            "cdn": "/cdn"
        }
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)