#ifndef TCPSOCKET_H
#define TCPSOCKET_H
#include <unistd.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

class tcpSocket
{
public:
    tcpSocket();
    ~tcpSocket();
    bool connectSocket();
    //bool recvData(char* buf,size_t len);
    int  recvData(char* buf,size_t len);
    bool sendData(char* buf,size_t len);
private:

private:
    int m_server_sockfd;
    int m_connfd;   
 // m_sclient;
};

#endif // TCPSOCKET_H
