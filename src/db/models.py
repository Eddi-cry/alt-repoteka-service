from sqlalchemy import Column, Integer, String, DateTime, BigInteger, Index, ForeignKey
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

class Branch(Base):
    __tablename__ = 'branches'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    label = Column(String(100))
    archive = Column(String(200))
    arches = Column(String(200))
    components = Column(String(200))
    last_loaded_at = Column(DateTime)
    binary_count = Column(Integer, default=0)
    source_count = Column(Integer, default=0)
    
    # Communication with packages
    packages = relationship("Package", back_populates="branch")

class Package(Base):
    __tablename__ = 'packages'
    
    id = Column(Integer, primary_key=True)
    branch_id = Column(Integer, ForeignKey('branches.id'), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    version = Column(String(100), nullable=False)
    release = Column(String(100), nullable=False)
    epoch = Column(Integer, nullable=True)
    arch = Column(String(50), nullable=True)
    kind = Column(String(20), nullable=False)
    source_rpm = Column(String(255), nullable=True)
    summary = Column(String(500), nullable=True)
    group = Column(String(100), nullable=True)
    packager = Column(String(255), nullable=True)
    maintainer_email = Column(String(255), nullable=True)
    buildtime = Column(DateTime, nullable=True)
    component = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Link to a branch
    branch = relationship("Branch", back_populates="packages")
    
    __table_args__ = (
        Index('idx_package_branch_name', 'branch_id', 'name'),
        Index('idx_package_name_kind', 'name', 'kind'),
        Index('idx_package_branch_kind', 'branch_id', 'kind'),
        Index('idx_package_maintainer', 'maintainer_email'),
    )