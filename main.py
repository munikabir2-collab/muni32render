from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import subprocess
import os
import re
import models
from fastapi import WebSocket
from database import engine, SessionLocal
from auth import hash_password, verify_password
from deploy_service import deploy_project

app = FastAPI()

templates = Jinja2Templates(directory="templates")

# ✅ Create tables
models.Base.metadata.create_all(bind=engine)

# ✅ Ensure folders exist
os.makedirs("projects", exist_ok=True)

clients = []

@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)

    try:
        while True:
            await websocket.receive_text()
    except:
        clients.remove(websocket)





# ---------------- ERROR HANDLER ----------------
@app.middleware("http")
async def error_handler(request: Request, call_next):
    try:
        return await call_next(request)

    except Exception as e:
        import traceback

        error = traceback.format_exc()

        print("================ ERROR ================")
        print(error)
        print("========================================")

        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "trace": error
            }
        )
# ---------------- DB ----------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------- AUTH CHECK ----------------
def get_current_user(request: Request, db: Session):
    email = request.cookies.get("user")
    if not email:
        return None
    return db.query(models.User).filter(models.User.email == email).first()

# ---------------- HOME ----------------
@app.get("/", response_class=HTMLResponse)
def home():
    return RedirectResponse("/login")

# ---------------- SIGNUP ----------------
@app.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.post("/signup")
def signup(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):

    user = models.User(
        username=username,
        email=email,
        password=hash_password(password)
    )

    db.add(user)
    db.commit()

    return RedirectResponse("/login", status_code=303)

# ---------------- LOGIN ----------------
@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
def login(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()

    if user and verify_password(password, user.password):
        response = RedirectResponse("/dashboard", status_code=303)
        response.set_cookie(key="user", value=email, httponly=True)
        return response

    return {"error": "Invalid credentials"}

# ---------------- DASHBOARD ----------------
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")

    projects = db.query(models.Project).filter(
        models.Project.user_id == user.id
    ).all()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "projects": projects
    })

# ---------------- CREATE PROJECT PAGE ----------------
@app.get("/create-project", response_class=HTMLResponse)
def create_project_page(request: Request):
    return templates.TemplateResponse("create.html", {"request": request})

# ---------------- CREATE PROJECT ----------------
@app.post("/create-project")
def create_project(
    request: Request,
    name: str = Form(...),
    repo: str = Form(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")

    # ✅ Safe name
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '', name)
    project_path = f"projects/{safe_name}"

    project = models.Project(
        name=safe_name,
        repo_url=repo,
        user_id=user.id,
        status="Cloning..."
    )

    db.add(project)
    db.commit()

    try:
        # ✅ Git clone
        if not os.path.exists(project_path):
            result = subprocess.run(
                ["git", "clone", repo, project_path],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                project.status = f"Git Error ❌: {result.stderr}"
            else:
                project.status = "Connected ✅"
        else:
            project.status = "Already Exists ✅"

    except Exception as e:
        project.status = f"Error ❌: {str(e)}"

    db.commit()
    return RedirectResponse("/dashboard", status_code=303)

# ---------------- LOGOUT ----------------
@app.get("/logout")
def logout():
    response = RedirectResponse("/login")
    response.delete_cookie("user")
    return response

# ---------------- DEPLOY ----------------
@app.get("/deploy/{project_id}")
def deploy(project_id: int, request: Request, db: Session = Depends(get_db)):

    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")

    project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.user_id == user.id
    ).first()

    if not project:
        return {"error": "Project not found"}

    project_path = f"projects/{project.name}"

    try:
        # ✅ Git pull
        result = subprocess.run(
            ["git", "-C", project_path, "pull"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            project.status = f"Git Pull Error ❌: {result.stderr}"
            db.commit()
            return RedirectResponse("/dashboard")

        project.status = "Deploying..."
        db.commit()

        # ✅ Deploy
        result = deploy_project(
            project_path,
            project.name,
            project.id
        )

        project.status = "Live 🚀"
        project.live_url = result.get("url", "")

    except Exception as e:
        project.status = f"Deploy Failed ❌: {str(e)}"

    db.commit()
    return RedirectResponse("/dashboard", status_code=303)

# ---------------- WEBHOOK ----------------
@app.post("/webhook/github")
async def github_webhook(request: Request, db: Session = Depends(get_db)):

    payload = await request.json()

    repo_url = payload["repository"]["clone_url"]
    repo_name = payload["repository"]["name"]

    project_path = f"projects/{repo_name}"

    if os.path.exists(project_path):
        subprocess.run(["git", "-C", project_path, "pull"])
    else:
        subprocess.run(["git", "clone", repo_url, project_path])

    project = db.query(models.Project).filter(
        models.Project.repo_url == repo_url
    ).first()

    if project:
        project.status = "Deploying..."
        db.commit()

        result = deploy_project(
            project_path,
            repo_name,
            project.id
        )

        project.status = "Live 🚀"
        project.live_url = result.get("url", "")
        db.commit()

    return {"status": "deployed"}

# ---------------- RESET ----------------
@app.get("/reset")
def reset(db: Session = Depends(get_db)):
    db.query(models.Project).delete()
    db.commit()
    return {"message": "All projects deleted"}

@app.get("/delete/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):

    project = db.query(models.Project).filter(
        models.Project.id == project_id
    ).first()

    if project:
        db.delete(project)
        db.commit()

    return RedirectResponse("/dashboard", status_code=303)    
