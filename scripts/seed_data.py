"""Seed 脚本：创建租户与首个用户（bcrypt 密码）。
用法：cd backend && python -m scripts.seed_data（或 python ../scripts/seed_data.py）
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
import bcrypt

from db.session import Base, SessionLocal, engine
from db.models import Project, ProjectMember, Tenant, User

Base.metadata.create_all(bind=engine)
db = SessionLocal()

tenant = db.query(Tenant).filter(Tenant.name == 'default').first()
if tenant is None:
    tenant = Tenant(name='default')
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    print('tenant created: id=', tenant.id)

user = db.query(User).filter(User.username == 'admin').first()
if user is None:
    pw = os.environ.get('CA_ADMIN_PASSWORD', 'admin123')
    user = User(tenant_id=tenant.id, username='admin',
                password_hash=bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode(),
                role='admin')
    db.add(user)
    db.commit()
    print('user created: admin /', pw)
else:
    print('user admin already exists')

test_projects = [
    ('深圳市龙华区星河幼儿园', '深圳龙华公建项目，包含幼儿园建筑、结构及机电专业资料'),
    ('深圳市龙华区中心儿童医院', '深圳龙华医疗公建项目，包含医院设计与施工资料'),
    ('深圳市龙华区儿童公园', '深圳龙华景观公建项目，包含公园景观及配套设施资料'),
]
for project_name, project_description in test_projects:
    project = (db.query(Project)
               .filter(Project.tenant_id == tenant.id,
                       Project.name == project_name).first())
    if project is None:
        project = Project(tenant_id=tenant.id, name=project_name,
                          description=project_description,
                          created_by=user.id)
        db.add(project)
        db.commit()
        db.refresh(project)
        print('test project created:', project.name)
    member = (db.query(ProjectMember)
              .filter(ProjectMember.project_id == project.id,
                      ProjectMember.user_id == user.id).first())
    if member is None:
        db.add(ProjectMember(project_id=project.id, user_id=user.id,
                             role='owner'))
        db.commit()
db.close()
