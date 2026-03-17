from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base

viewer_follows = Table(
    "viewer_follows",
    Base.metadata,
    Column("viewer_id", Integer, ForeignKey("viewers.id", ondelete="CASCADE"), primary_key=True),
    Column("designer_id", Integer, ForeignKey("designers.id", ondelete="CASCADE"), primary_key=True),
)

viewer_likes = Table(
    "viewer_likes",
    Base.metadata,
    Column("viewer_id", Integer, ForeignKey("viewers.id", ondelete="CASCADE"), primary_key=True),
    Column("project_id", Integer, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
)

viewer_wishlist = Table(
    "viewer_wishlist",
    Base.metadata,
    Column("viewer_id", Integer, ForeignKey("viewers.id", ondelete="CASCADE"), primary_key=True),
    Column("project_id", Integer, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
)


class Designer(Base):
    __tablename__ = "designers"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(120), nullable=False)
    username = Column(String(80), nullable=True, unique=True, index=True)
    email = Column(String(180), nullable=False, unique=True, index=True)
    whatsapp = Column(String(40), nullable=False, default="")
    address = Column(String(255), nullable=False, default="")
    bio = Column(Text, nullable=False, default="")
    website_url = Column(String(255), nullable=False, default="")
    facebook_url = Column(String(255), nullable=False, default="")
    instagram_url = Column(String(255), nullable=False, default="")
    behance_url = Column(String(255), nullable=False, default="")
    dribbble_url = Column(String(255), nullable=False, default="")
    password = Column(String(255), nullable=False)
    skills = Column(String(255), nullable=False)
    profile_image = Column(String(255), nullable=False, default="default-profile.svg")
    cover_image = Column(String(255), nullable=False, default="default-cover.svg")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    projects = relationship("Project", back_populates="designer", cascade="all, delete-orphan")
    followers = relationship("Viewer", secondary=viewer_follows, back_populates="following_designers")


class Viewer(Base):
    __tablename__ = "viewers"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(120), nullable=False)
    username = Column(String(80), nullable=True, unique=True, index=True)
    email = Column(String(180), nullable=False, unique=True, index=True)
    password = Column(String(255), nullable=False, default="")
    profile_image = Column(String(255), nullable=False, default="default-profile.svg")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    following_designers = relationship("Designer", secondary=viewer_follows, back_populates="followers")
    liked_projects = relationship("Project", secondary=viewer_likes, back_populates="liked_by")
    wishlist_projects = relationship("Project", secondary=viewer_wishlist, back_populates="wishlisted_by")


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("designer_id", "title", name="uq_project_designer_title"),
    )

    id = Column(Integer, primary_key=True, index=True)
    designer_id = Column(Integer, ForeignKey("designers.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(180), nullable=False)
    description = Column(Text, nullable=False, default="")
    category = Column(String(80), nullable=False)
    tags = Column(String(255), nullable=False, default="")
    image_filename = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    designer = relationship("Designer", back_populates="projects")
    liked_by = relationship("Viewer", secondary=viewer_likes, back_populates="liked_projects")
    wishlisted_by = relationship("Viewer", secondary=viewer_wishlist, back_populates="wishlist_projects")


class ProjectRating(Base):
    __tablename__ = "project_ratings"
    __table_args__ = (UniqueConstraint("viewer_id", "project_id", name="uq_project_rating"),)

    id = Column(Integer, primary_key=True, index=True)
    viewer_id = Column(Integer, ForeignKey("viewers.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    rating = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
