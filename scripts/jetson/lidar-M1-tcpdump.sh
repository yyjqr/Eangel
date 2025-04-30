activeNet=eth0
#sudo tcpdump -i $activeNet src 192.168.1.18 and  port 8080 -nAxx -vvv -c 3
#sudo tcpdump -i $activeNet src 192.168.1.37 and  port 7070 -nAxx -vvv -c 3
#sudo tcpdump -i $activeNet src 192.168.1.36 and  port 3030 -nAxx -vvv -c 3
#sudo tcpdump -i $activeNet src 192.168.1.48 and  port 4040 -nAxx -vvv -c 3

case "$1" in
	"0") #sudo tcpdump -i $activeNet src 192.168.1.18 and  port 8080 -nAxx -vvv -c 3
             sudo tcpdump -i $activeNet src 192.168.1.37 and  port 7070 -nAxx -vvv -c 3
             sudo tcpdump -i $activeNet src 192.168.1.36 and  port 3030 -nAxx -vvv -c 3
             sudo tcpdump -i $activeNet src 192.168.1.48 and  port 4040 -nAxx -vvv -c 3
	     ;;
	 "18") sudo tcpdump -i eth0 src 192.168.1.18 and  port 8080 -nAxx -vvv |grep 0x0030
             ;;
	"37") sudo tcpdump -i eth0 src 192.168.1.37 and  port 7070 -nAxx -vvv |grep 0x0030
             ;;
	"36") sudo tcpdump -i eth0 src 192.168.1.36 and  port 3030 -nAxx -vvv |grep 0x0030
             ;;
        "48") sudo tcpdump -i eth0 src 192.168.1.48 and  port 4040 -nAxx -vvv |grep 0x0030
             ;;
	"3") #sudo tcpdump -i $activeNet src 192.168.1.18 and  port 8080 -nAxx -vvv|grep 0x0030
		sudo tcpdump -i $activeNet src 192.168.1.37 and  port 7070 -nAxx -vvv -c 10|grep -E -B 1 -A 2 "192\.168\.|([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}|0x0030"
		sudo tcpdump -i $activeNet src 192.168.1.48 and  port 4040 -nAxx -vvv -c 10| grep -E -B 1 -A 2 "192\.168\.|([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}|0x0030"
		sudo tcpdump -i $activeNet src 192.168.1.36 and  port 3030 -nAxx -vvv -c 10| grep -E -B 1 -A 2 "192\.168\.|([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}|0x0030"
             ;;
esac
