import json
import time

from exclusionms import apihandler
from exclusionms.components import ExclusionPoint, ExclusionInterval
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)