all : install
install :
	sudo cp odyo.py /usr/bin/odyo
	sudo chmod 755 /usr/bin/odyo
uninstall :
	sudo rm -f /usr/bin/odyo
