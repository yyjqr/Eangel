#include "tcpsocket.h"
#include <stdio.h>
#include <string.h> //strcpy
#include <iostream>
#include "logging.h"
using namespace std;

tcpSocket::tcpSocket()
{
    m_server_sockfd = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    //       if (m_server_sockfd == INVALID_SOCKET)
    //     {
    //       printf("invalid socket !\n");
    // }




}

tcpSocket::~tcpSocket()
{
    cout<<"close socket,recycle resources"<<endl;

    close(m_server_sockfd);
    close(m_connfd);

}

bool tcpSocket::connectSocket()
{
    sockaddr_in serAddr;
    int server_len;
    serAddr.sin_family = AF_INET;
    serAddr.sin_port = htons(6800);
    //    serAddr.sin_addr.s_addr = inet_addr("127.0.0.1"); //这里可以改成服务端的IP，若是都在一台电脑就不用改变
    serAddr.sin_addr.s_addr = htonl(INADDR_ANY); //这里可以改成服务端的IP，若是都在一台电脑就不用改变
    server_len = sizeof(serAddr);
    bind(m_server_sockfd, (struct sockaddr *)&serAddr, server_len);
    listen(m_server_sockfd, 5); //监听队列最多容纳5个
    cout<<"Server start to listen"<<endl;

    struct sockaddr_in client_address;  //记录进行连接的客户端的地址
    socklen_t client_addrlength = sizeof(client_address);
    m_connfd = accept(m_server_sockfd,(struct sockaddr*)&client_address,&client_addrlength);
    //       printf("client_address ip:%d",client_address.sin_addr.s_addr);
    if(m_connfd < 0)
    {
        printf("Fail to accept!\n");
        return false;
        close(m_server_sockfd);
    }
    else{
        getpeername(m_connfd,(struct sockaddr*)&client_address,&client_addrlength);

        char szPeerAddress[16];
        //Sets buffers to a specified character.
        memset((void *)szPeerAddress,0,sizeof(szPeerAddress));
        cout << szPeerAddress << "**************" <<endl;
        //If no error occurs, inet_ntoa returns a character pointer to a static buffer
        //containing the text address in standard ".'' notation
        strcpy(szPeerAddress,inet_ntoa(client_address.sin_addr));//将ip地址从字符串转换为xxx.xxx.xxx.xxx 0301
        //Copy a string.the second parameter strSource Null-terminated source string
        cout << szPeerAddress << endl;
        LogInfo("client ip:%s\n",szPeerAddress);
        // 原文链接：https://blog.csdn.net/gukesdo/article/details/6889594
    }
    return true;
}


int tcpSocket::sendData(char* buf,size_t len)
{
    int ret=0;
//发送正常的话，返回的是发送长度，2764800
    ret= send(m_connfd,buf,len,0);
    //cout<<"test send:"<<ret<<endl;
    return ret;
}

int tcpSocket::recvData(char* buf,size_t len)
{
    int ret=0;
    ret= recv(m_connfd,buf,len,0);
    return ret;
}

