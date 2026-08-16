"""Nested project folder behavior and project suggestion regression tests."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.exceptions import AppError
from db.models import (Base, Document, DocumentFolderLink, Project,
                       ProjectMember, Tenant, User)
from services import folder_service, project_service


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add_all([
        Tenant(id=1, name="测试租户"),
        User(id=7, tenant_id=1, username="folder-user", password_hash="x"),
        Project(id=1, tenant_id=1, name="项目A", created_by=7),
        Project(id=2, tenant_id=1, name="项目B", created_by=8),
        ProjectMember(project_id=1, user_id=7),
    ])
    session.commit()
    yield session
    session.close()


def test_可创建根目录子目录和孙目录(db):
    root = folder_service.create_folder(db, 1, 7, "各专业图纸")
    child = folder_service.create_folder(db, 1, 7, "电气", root.id)
    grandchild = folder_service.create_folder(db, 1, 7, "强电", child.id)

    assert grandchild.parent_id == child.id
    assert [folder.name for folder in folder_service.list_folders(db, 1)] == [
        "各专业图纸", "电气", "强电"]


def test_父目录必须属于同一项目且同级不能重名(db):
    other = folder_service.create_folder(db, 2, 8, "其他项目目录")
    with pytest.raises(AppError) as wrong_project:
        folder_service.create_folder(db, 1, 7, "错误子目录", other.id)
    assert wrong_project.value.code == "FOLDER_NOT_FOUND"

    folder_service.create_folder(db, 1, 7, "施工图")
    with pytest.raises(AppError) as duplicate:
        folder_service.create_folder(db, 1, 7, "施工图")
    assert duplicate.value.code == "FOLDER_ALREADY_EXISTS"


def test_非空目录不能删除且文档可以归档(db):
    folder = folder_service.create_folder(db, 1, 7, "建筑")
    doc = Document(project_id=1, file_name="总图.pdf", file_path="x.pdf",
                   created_by=7)
    db.add(doc)
    db.commit()
    folder_service.assign_document(db, 1, doc.id, folder.id)

    link = db.query(DocumentFolderLink).filter_by(document_id=doc.id).one()
    assert link.folder_id == folder.id
    with pytest.raises(AppError) as not_empty:
        folder_service.delete_folder(db, 1, folder.id)
    assert not_empty.value.code == "FOLDER_NOT_EMPTY"

    folder_service.assign_document(db, 1, doc.id, None)
    folder_service.delete_folder(db, 1, folder.id)
    assert db.query(Document).filter_by(id=doc.id).one().file_name == "总图.pdf"


def test_深圳龙华返回三个有权限的预测项目(db):
    names = ["深圳市龙华区星河幼儿园", "深圳市龙华区中心儿童医院",
             "深圳市龙华区儿童公园"]
    for index, name in enumerate(names, start=10):
        db.add(Project(id=index, tenant_id=1, name=name,
                       description="深圳龙华公建项目", created_by=7))
        db.add(ProjectMember(project_id=index, user_id=7))
    db.add(Project(id=99, tenant_id=1, name="深圳市龙华区保密项目",
                   description="", created_by=8))
    db.commit()

    result = project_service.suggest_projects(db, 7, "深圳龙华", limit=3)

    assert len(result) == 3
    assert {project.name for project in result} == set(names)
    assert all(project.id != 99 for project in result)


def test_目录允许十层但拒绝第十一层(db):
    parent = None
    for level in range(1, 11):
        parent = folder_service.create_folder(
            db, 1, 7, "第{}层".format(level), parent.id if parent else None)

    with pytest.raises(AppError) as too_deep:
        folder_service.create_folder(db, 1, 7, "第11层", parent.id)

    assert too_deep.value.code == "FOLDER_DEPTH_LIMIT"
    assert "10 层" in too_deep.value.message
