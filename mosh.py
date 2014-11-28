from extensions.video import Processor
from bot import start_logging
import sys

start_logging()
print Processor().mosh_file(sys.argv[1])
