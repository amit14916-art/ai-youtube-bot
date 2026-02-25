import os
import sys
from typing import List
from datetime import datetime, timedelta

from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from webapp import models
from main import run_pipeline
from config.settings import OUTPUT_DIR

# ─── Auth Constants ───
SECRET_KEY = "SUPER_SECRET_KEY_CHANGE_ME"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI(title="AI YouTube SaaS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── DB Setup ───
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./webapp/saas.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
models.Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ─── Auth Utils ───
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None: raise HTTPException(status_code=401)
    except JWTError: raise HTTPException(status_code=401)
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None: raise HTTPException(status_code=401)
    return user

# ─── API Routes ───

@app.post("/register")
def register(email: str, password: str, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == email).first()
    if db_user: raise HTTPException(status_code=400, detail="Email already registered")
    user = models.User(email=email, hashed_password=get_password_hash(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"status": "User created", "email": email}

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/me")
def read_users_me(current_user: models.User = Depends(get_current_user)):
    return {
        "email": current_user.email,
        "credits": current_user.credits,
        "is_premium": current_user.is_premium
    }

@app.post("/jobs/create")
def create_job(background_tasks: BackgroundTasks, topic: str = None, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.credits <= 0:
        raise HTTPException(status_code=400, detail="Not enough credits")
    
    # Generate a job ID
    job_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create job record
    new_job = models.Job(
        job_id=job_id,
        topic=topic or "Trending Research",
        status="started",
        user_id=current_user.id
    )
    db.add(new_job)
    
    # Deduct credit
    current_user.credits -= 1
    db.commit()
    db.refresh(new_job)
    
    # Background worker
    def background_run(jid, user_topic):
        # Create a fresh DB session for the background thread
        worker_db = SessionLocal()
        try:
            # Run the actual bot pipeline
            job_result = run_pipeline(dry_run=False, topic=user_topic)
            
            # Update job in DB
            db_job = worker_db.query(models.Job).filter(models.Job.job_id == jid).first()
            if db_job:
                if job_result and job_result.get("status") == "uploaded":
                    db_job.status = "completed"
                    db_job.youtube_url = job_result.get("youtube_url")
                    db_job.shorts_url = job_result.get("shorts_url")
                else:
                    db_job.status = "failed"
                worker_db.commit()
        except Exception as e:
            db_job = worker_db.query(models.Job).filter(models.Job.job_id == jid).first()
            if db_job:
                db_job.status = "failed"
                worker_db.commit()
        finally:
            worker_db.close()
    
    background_tasks.add_task(background_run, job_id, topic)
    return {"status": "Job started", "job_id": job_id, "remaining_credits": current_user.credits}

@app.get("/jobs")
def list_jobs(current_user: models.User = Depends(get_current_user)):
    return current_user.jobs

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
