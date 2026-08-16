"""Seed 脚本：创建租户与首个用户（bcrypt 密码）。
用法：cd backend && python -m scripts.seed_data（或 python ../scripts/seed_data.py）
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
import bcrypt

from db.session import Base, SessionLocal, engine
from db.models import Tenant, User

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
db.close()
