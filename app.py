from fastapi import FastAPI

#Skeleton
app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}