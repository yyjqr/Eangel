#include "controlTCP.h"
#include "QDebug"
#include "camSocketParam.h"

controlTCP::controlTCP(QObject* parent):
    QTcpSocket(parent)
{

    myTimer = new QTimer(this);
    pictureSocket = new QTcpSocket(this);
    connect(myTimer,SIGNAL(timeout()),this,SLOT(sendCmdToServer()));
    //先把连接成功的信号，来做读取，然后再在线程里做接收处理？？？
    connect(pictureSocket,SIGNAL(readyRead()),this,SLOT(recvData()));
    connect(pictureSocket,SIGNAL(disconnected()),this,SLOT(stopTimer()));
}

controlTCP::~controlTCP()
{

}

bool controlTCP::connectSocket(QTcpSocket* m_tcpSocket,QString ip)
{
    qDebug()<< "this  :"<<this;
    m_tcpSocket->connectToHost(ip,6800);
    qDebug()<< "pictureSocket state  :"<<m_tcpSocket->state();
    connect(m_tcpSocket,SIGNAL(connected()),this,SLOT(startTime()));
    if(m_tcpSocket->state()==QTcpSocket::ConnectedState){
        return true;
    }
    else
    {
        return false;
    }
}

bool controlTCP::connectSocket(QString ip)
{
    qDebug()<< "this  :"<<this;
    pictureSocket->connectToHost(ip,6800);
    qDebug()<< "pictureSocket state  :"<<pictureSocket->state();
    connect(pictureSocket,SIGNAL(connected()),this,SLOT(startTime()));
    if(pictureSocket->state()==QTcpSocket::ConnectingState||pictureSocket->state()==QTcpSocket::ConnectedState){
//        emit signalSocketToRead();
        return true;
    }
    else
    {
        return false;
    }
}

bool controlTCP::disconnectSocket()
{
    qDebug()<< "this  :"<<this;
    pictureSocket->disconnectFromHost();
    qDebug()<< "pictureSocket state  :"<<pictureSocket->state();
    if(pictureSocket->state()==QTcpSocket::ClosingState||pictureSocket->state()==QTcpSocket::UnconnectedState){
        return true;
    }
    else
    {
        return false;
    }
}

void controlTCP::startTime()
{
    qDebug() << "fun: " <<__func__;
    myTimer->start(500);
    //    systemTimer.start(500);
}

void controlTCP::stopTimer()
{
    qDebug() << "fun: " <<__func__;
    myTimer->stop();
    //    systemTimer.start(500);
}

void controlTCP::sendCmdToServer()
{
    pictureSocket->write("PIC");
    pictureSocket->flush();
//    qDebug()<<"send CMD:PIC"<< "\n";
}


void controlTCP::recvData(void)
{

    QByteArray bytes=NULL;
    while(pictureSocket->waitForReadyRead(200))
    {
//        bytes.append((QByteArray)pictureSocket->readAll());
        bytes.append((QByteArray)pictureSocket->read(3*IMAGESIZE));
         if(bytes.size()>=3*IMAGESIZE)
         {
              qDebug()<<"\n Read 3*IMAGESIZE "<< "\n";
             break;
         }
    }

    qDebug()<<__func__<<__LINE__<<"Read data.size()"<<bytes.size()<< "\n";
    emit dataReady(bytes);
}
