from extensions.video import Processor
from bot import start_logging
import sys

start_logging()

url = sys.argv[1]
mosh_type = sys.argv[2] if len(sys.argv) >= 3 else 'drift'

print Processor().mosh_url(url, mosh_type)
