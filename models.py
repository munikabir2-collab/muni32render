from sqlalchemy import Column, Integer, String, ForeignKey, Text
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    password = Column(String)

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    repo_url = Column(String)
    status = Column(String, default="Not Deployed")
    live_url = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"))



class DeploymentLog(Base):
    __tablename__ = "deployment_logs"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    log = Column(Text)    