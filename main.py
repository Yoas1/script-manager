from fastapi import FastAPI, Request, File, UploadFile, Form, HTTPException, BackgroundTasks, Depends
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.openapi.docs import get_swagger_ui_html
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, Text, DateTime, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import datetime
import subprocess
import os

app = FastAPI(docs_url=None)

UPLOAD_DIR = "scripts"
os.makedirs(UPLOAD_DIR, exist_ok=True)



DATABASE_URL = "sqlite:///./lambda.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()



class ScriptResult(Base):
    __tablename__ = "script_results"
    filename = Column(String, primary_key=True, index=True)
    result = Column(Text)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    duration = Column(Float)


Base.metadata.create_all(bind=engine)


app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="static")


@app.get("/docs", include_in_schema=False)
async def swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="Yoas1 - Script-server API",
        swagger_favicon_url="static/favicon.ico",
    )


@app.get("/", response_class=HTMLResponse)
async def get_editor(request: Request):
    return templates.TemplateResponse("editor.html", {"request": request})

@app.get("/list_files/")
async def list_files():
    files = os.listdir(UPLOAD_DIR)
    return JSONResponse(content={"files": files})


@app.post("/save_file/")
async def save_file(filename: str = Form(...), code: str = Form(...)):
    file_location = os.path.join(UPLOAD_DIR, filename)
    with open(file_location, "w") as file:
        file.write(code)
    return {"message": f"File {filename} saved successfully."}

@app.get("/load_file/")
async def load_file(filename: str):
    file_location = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(file_location):
        with open(file_location, "r") as file:
            code = file.read()
        return {"filename": filename, "code": code}
    else:
        return {"error": "File not found."}

@app.post("/upload_file/")
async def upload_file(file: UploadFile = File(...)):
    file_location = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_location, "wb") as f:
        f.write(file.file.read())
    return {"filename": file.filename}

@app.get("/download_file/")
async def download_file(filename: str):
    file_location = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(file_location):
        return FileResponse(file_location, media_type='application/octet-stream', filename=filename)
    else:
        return {"error": "File not found."}

@app.delete("/delete_file/")
async def delete_file(filename: str):
    file_location = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(file_location):
        os.remove(file_location)
        return {"message": f"File {filename} deleted successfully."}
    else:
        raise HTTPException(status_code=404, detail="File not found.")


#install python packeges
class PackageRequest(BaseModel):
    package_name: str


@app.post("/install-package/")
async def install_package(request: PackageRequest):
    package_name = request.package_name
    try:

        subprocess.run(["pip", "install", package_name], check=True)
        return {"message": f"Package {package_name} installed successfully"}
    except subprocess.CalledProcessError:
        raise HTTPException(status_code=500, detail="Failed to install package")



def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



def run_script_and_save_result(filename: str, db: Session):

    start_time = datetime.datetime.now()


    result = subprocess.run(["python", f'./scripts/{filename}'], capture_output=True, text=True)


    end_time = datetime.datetime.now()
    duration = (end_time - start_time).total_seconds()


    script_result = ScriptResult(
        filename=filename,
        result=result.stdout or result.stderr,
        start_time=start_time,
        end_time=end_time,
        duration=duration
    )
    db.merge(script_result)
    db.commit()



@app.post("/run-script/")
async def run_script(background_tasks: BackgroundTasks, filename: str = Form(...), db: Session = Depends(get_db)):
    background_tasks.add_task(run_script_and_save_result, filename, db)
    return {"status": f"Script {filename} is running in the background"}



@app.get("/api/results/{filename}")
async def get_result_by_filename(filename: str, db: Session = Depends(get_db)):
    script_result = db.query(ScriptResult).filter(ScriptResult.filename == filename).first()
    if not script_result:
        raise HTTPException(status_code=404, detail="Script result not found")

    return {
        "filename": script_result.filename,
        "start_time": script_result.start_time,
        "end_time": script_result.end_time,
        "duration": script_result.duration,
        "result": script_result.result
    }

@app.get("/api/results")
async def get_all_results(db: Session = Depends(get_db)):
    results = db.query(ScriptResult).all()
    return [
        {
            "filename": result.filename,
            "start_time": result.start_time,
            "end_time": result.end_time,
            "duration": result.duration,
            "result": result.result
        }
        for result in results
    ]

@app.get("/results/")
async def results_page():
    return FileResponse('static/results.html')



def delete_script_result(filename: str, db: Session):
    script_result = db.query(ScriptResult).filter(ScriptResult.filename == filename).first()
    if script_result:
        db.delete(script_result)
        db.commit()
        return True
    return False


@app.delete("/api/delete/{filename}")
async def delete_result_by_filename(filename: str, db: Session = Depends(get_db)):
    if delete_script_result(filename, db):
        return {"status": "Script result deleted"}
    else:
        raise HTTPException(status_code=404, detail="Script result not found")
