"""AWS Lambda entry point (API Gateway REST proxy integration)."""
from mangum import Mangum

from app.main import app

handler = Mangum(app, lifespan="off")
