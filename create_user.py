from airflow.security.permissions import Permissions
from airflow.security.roles import Roles
from airflow.models.user import User
from airflow import settings

session = settings.Session()
user = User(
    username="animesh",
    email="animeshmodi2004@gmail.com",
    first_name="Animesh",
    last_name="Modi",
    password="Anand@123",
    superuser=True
)
session.add(user)
session.commit()
session.close()
{"admin": "32xq5MMS7muQNnUF"}