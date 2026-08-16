"""Project folder operations with project isolation and nested paths."""
from sqlalchemy.orm import Session

from core.exceptions import AppError, NotFoundError
from db.models import Document, DocumentFolderLink, ProjectFolder

MAX_FOLDER_DEPTH = 10


def get_folder(db: Session, project_id: int, folder_id: str) -> ProjectFolder:
    folder = (db.query(ProjectFolder)
              .filter(ProjectFolder.id == folder_id,
                      ProjectFolder.project_id == project_id).first())
    if folder is None:
        raise NotFoundError("FOLDER_NOT_FOUND", "文件夹不存在")
    return folder


def _validate_name(name: str) -> str:
    value = name.strip()
    if not value:
        raise AppError("FOLDER_NAME_REQUIRED", "请输入文件夹名称", 422)
    if len(value) > 128:
        raise AppError("FOLDER_NAME_TOO_LONG", "文件夹名称不能超过 128 个字符", 422)
    if "/" in value or "\\" in value:
        raise AppError("FOLDER_NAME_INVALID", "文件夹名称不能包含路径分隔符", 422)
    return value


def _parent_depth(db: Session, project_id: int,
                  parent: ProjectFolder | None) -> int:
    depth = 0
    visited = set()
    while parent is not None:
        if parent.id in visited:
            raise AppError("FOLDER_TREE_INVALID", "文件夹层级存在循环", 409)
        visited.add(parent.id)
        depth += 1
        if depth >= MAX_FOLDER_DEPTH:
            raise AppError(
                "FOLDER_DEPTH_LIMIT",
                "文件夹最多支持 {} 层".format(MAX_FOLDER_DEPTH), 409)
        parent = (get_folder(db, project_id, parent.parent_id)
                  if parent.parent_id else None)
    return depth


def _ensure_unique(db: Session, project_id: int, parent_id: str | None,
                   name: str, exclude_id: str | None = None) -> None:
    query = db.query(ProjectFolder).filter(
        ProjectFolder.project_id == project_id,
        ProjectFolder.parent_id.is_(None) if parent_id is None
        else ProjectFolder.parent_id == parent_id,
        ProjectFolder.name == name)
    if exclude_id:
        query = query.filter(ProjectFolder.id != exclude_id)
    if query.first() is not None:
        raise AppError("FOLDER_ALREADY_EXISTS", "同级目录下已存在同名文件夹", 409)


def create_folder(db: Session, project_id: int, user_id: int, name: str,
                  parent_id: str | None = None) -> ProjectFolder:
    value = _validate_name(name)
    parent = get_folder(db, project_id, parent_id) if parent_id else None
    _parent_depth(db, project_id, parent)
    _ensure_unique(db, project_id, parent_id, value)
    folder = ProjectFolder(project_id=project_id, parent_id=parent_id,
                           name=value, created_by=user_id)
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return folder


def list_folders(db: Session, project_id: int) -> list[ProjectFolder]:
    return (db.query(ProjectFolder)
            .filter(ProjectFolder.project_id == project_id)
            .order_by(ProjectFolder.created_at.asc()).all())


def rename_folder(db: Session, project_id: int, folder_id: str,
                  name: str) -> ProjectFolder:
    folder = get_folder(db, project_id, folder_id)
    value = _validate_name(name)
    _ensure_unique(db, project_id, folder.parent_id, value, folder.id)
    folder.name = value
    db.commit()
    db.refresh(folder)
    return folder


def delete_folder(db: Session, project_id: int, folder_id: str) -> None:
    folder = get_folder(db, project_id, folder_id)
    has_children = (db.query(ProjectFolder)
                    .filter(ProjectFolder.parent_id == folder.id).first())
    has_documents = (db.query(DocumentFolderLink)
                     .filter(DocumentFolderLink.folder_id == folder.id).first())
    if has_children or has_documents:
        raise AppError("FOLDER_NOT_EMPTY", "文件夹非空，请先处理子文件夹和文件", 409)
    db.delete(folder)
    db.commit()


def assign_document(db: Session, project_id: int, document_id: str,
                    folder_id: str | None) -> None:
    document = (db.query(Document)
                .filter(Document.id == document_id,
                        Document.project_id == project_id).first())
    if document is None:
        raise NotFoundError("DOCUMENT_NOT_FOUND", "文档不存在")
    if folder_id:
        get_folder(db, project_id, folder_id)
    link = (db.query(DocumentFolderLink)
            .filter(DocumentFolderLink.document_id == document_id).first())
    if folder_id is None:
        if link:
            db.delete(link)
    elif link:
        link.folder_id = folder_id
    else:
        db.add(DocumentFolderLink(document_id=document_id, folder_id=folder_id))
    db.commit()


def folder_item(folder: ProjectFolder) -> dict:
    return {"folder_id": folder.id, "parent_id": folder.parent_id,
            "name": folder.name,
            "created_at": folder.created_at.isoformat() + "Z"}
