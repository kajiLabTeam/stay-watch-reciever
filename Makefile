UNITS = stay-watch-scan.timer stay-watch-post.timer

.PHONY: install status start stop restart enable disable list logs

install:
	./scripts/install.sh

status:
	systemctl status $(UNITS)

start:
	sudo systemctl start $(UNITS)

stop:
	sudo systemctl stop $(UNITS)

restart:
	sudo systemctl restart $(UNITS)

enable:
	sudo systemctl enable $(UNITS)

disable:
	sudo systemctl disable $(UNITS)

list:
	systemctl list-timers 'stay-watch-*'

logs:
	journalctl -u stay-watch-scan.service -u stay-watch-post.service -f
