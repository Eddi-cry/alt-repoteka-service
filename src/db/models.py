from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Branch(Base):
    __tablename__ = "branches"

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
    __tablename__ = "packages"

    id = Column(Integer, primary_key=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
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
        # Unique constraint to prevent duplicate packages
        # Same package cannot exist twice in the same branch with same arch
        Index(
            "idx_package_unique",
            "branch_id",
            "name",
            "arch",
            "kind",
            unique=True,
            postgresql_nulls_not_distinct=True,  # NULL = NULL for uniqueness
        ),
        # Composite index for JOIN operations (maintainer_pkgs endpoint)
        # Covers: WHERE branch_id = X AND maintainer_email = Y AND kind = Z
        Index("idx_package_branch_maintainer_kind", "branch_id", "maintainer_email", "kind"),
        # Composite index for package lookups across branches
        # Covers: WHERE name = X AND kind = Y
        Index("idx_package_name_kind", "name", "kind"),
        # Index for sisyphus package lookups in outdated_pkgs endpoint
        # Covers: WHERE branch_id = X AND name IN (...) AND kind = Y
        Index("idx_package_branch_name_kind", "branch_id", "name", "kind"),
        # Index for maintainer queries
        Index("idx_package_maintainer", "maintainer_email"),
        # Index for filtering by kind (used in many queries)
        Index("idx_package_kind", "kind"),
    )
