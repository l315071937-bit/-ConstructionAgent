"""Nested folder API for a project's persisted document library."""
from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.models import User
from db.session import get_db
from dependencies import get_current_project, get_current_user
from services import folder_service

router = APIRouter(prefix="/projects/{project_id}/folders", tags=["folders"])


class FolderCreate(BaseModel):
    name: str
    parent_id: str | None = None


class FolderRename(BaseModel):
    name: str


@router.get("")
def list_folders(project=Depends(get_current_project),
                 db: Session = Depends(get_db)):
    items = [folder_service.folder_item(folder)
             for folder in folder_service.list_folders(db, project.id)]
    return {"items": items, "total": len(items)}


@router.post("", status_code=201)
def create_folder(body: FolderCreate,
                  project=Depends(get_current_project),
                  user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    folder = folder_service.create_folder(
        db, project.id, user.id, body.name, body.parent_id)
    return folder_service.folder_item(folder)


@router.patch("/{folder_id}")
def rename_folder(folder_id: str, body: FolderRename,
                  project=Depends(get_current_project),
                  db: Session = Depends(get_db)):
    folder = folder_service.rename_folder(db, project.id, folder_id, body.name)
    return folder_service.folder_item(folder)


@router.delete("/{folder_id}", status_code=204)
def delete_folder(folder_id: str, project=Depends(get_current_project),
                  db: Session = Depends(get_db)):
    folder_service.delete_folder(db, project.id, folder_id)
    return Response(status_code=204)


@router.put("/{folder_id}/documents/{document_id}", status_code=204)
def assign_document(folder_id: str, document_id: str,
                    project=Depends(get_current_project),
                    db: Session = Depends(get_db)):
    folder_service.assign_document(db, project.id, document_id, folder_id)
    return Response(status_code=204)
