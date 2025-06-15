#!/usr/bin/env python3.10

import os
import sys

# Add your project directory to sys.path
path = '/home/yourusername/t3-chat-clone/django_app'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

from django.core.wsgi import get_wsgi_application
from django.contrib.staticfiles.handlers import StaticFilesHandler

application = StaticFilesHandler(get_wsgi_application()) 