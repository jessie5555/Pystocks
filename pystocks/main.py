import daemon
from daemon import runner

import pystocks as ps

money = 1000
lfile = "/tmp/pystocks.log"
stocks = ps.pystocks(money, log_file=lfile)

daemon_runner = daemon.runner.DaemonRunner(stocks.run())
daemon_runner.do_action()