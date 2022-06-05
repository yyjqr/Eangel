#include "controlTCP.h"
#include "QDebug"
#include "camSocketParam.h"
#include "logging.h"
#include <QThread>
#include <QDateTime>

controlTCP::controlTCP(QObject* parent):
    QTcpSocket(parent),
    m_NoDataTimes(0),
    b_realStopTimer(false)
{
    cmdTimer = new QTimer(this);
    m_camSocket = new QTcpSocket(this);
    m_byteArray_oneFrame.resize(MAX_LEN);
    connect(cmdTimer,SIGNAL(timeout()),this,SLOT(sendCmdToServer()));
    //先把连接成功的信号，来做读取，然后再在线程里做接收处理？？？
    connect(m_camSocket,SIGNAL(readyRead()),this,SLOT(recvData()));
    connect(m_camSocket,SIGNAL(disconnected()),this,SLOT(stopTimer()));
}

controlTCP::~controlTCP()
{
    m_byteArray_oneFrame.clear(); //add 0309
    if(cmdTimer!=nullptr){
        delete  cmdTimer;
    }
    if(m_camSocket!=nullptr){
        delete  m_camSocket;
    }
}

bool controlTCP::connectSocket(QTcpSocket* m_tcpSocket,QString ip)
{
    m_tcpSocket->connectToHost(ip,6800);
    qDebug()<< "m_camSocket state  :"<<m_tcpSocket->state();
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
    //    qDebug()<< "this  :"<<this;
    m_camSocket->connectToHost(ip,6800);
    qDebug()<< "m_camSocket state  :"<<m_camSocket->state()<<endl;
    connect(m_camSocket,SIGNAL(connected()),this,SLOT(startTime()));
    qDebug()<< "m_camSocket->state:"<<m_camSocket->state();
    m_camSocket->waitForConnected(3000);//5s超时--->3s

    if(m_camSocket->state()==QTcpSocket::ConnectedState){

        return true;
    }
    else
    {
        return false;
    }
}

bool controlTCP::disconnectSocket()
{
    qDebug()<< "m_camSocket state  :"<<m_camSocket->state();
    if(m_camSocket->state()==QTcpSocket::ClosingState||m_camSocket->state()==QTcpSocket::UnconnectedState){
        return true;
    }
    else
    {
        m_camSocket->disconnectFromHost();
        return false;
    }
}

void controlTCP::startTime()
{
    qDebug() << "fun: " <<__func__<<"start CMD timer\n";
    cmdTimer->start(400);
}

void controlTCP::stopTimer()
{
    qDebug() << "fun: " <<__func__<<__LINE__<<endl;
    cmdTimer->stop();
    m_camSocket->close(); //关闭socket 202203
    b_realStopTimer=true;
    //add 每次socket断开后，再访问，避免访问内存越界 202201
    m_queue_camDataInCHAR.clear();
    emit signalSocketDisconnect();
}
void controlTCP::sendCmdToServer()
{
    m_camSocket->write("PIC");
    m_camSocket->flush();
    QDateTime datetime;
    QString timestr=datetime.currentDateTime().toString("HH:mm:ss.zzz");
    qDebug()<<__func__<<timestr<<":send CMD:PIC"<< "\n";
    LogInfo("After read,send CMD time:%s\n",timestr.toStdString().c_str());
}


void controlTCP::recvData(void)
{
    QByteArray bytes=nullptr;
    long long int bytesNum=0;
//        qDebug()<<"\n fun:"<<__func__<<"currentThreadId:"<<QThread::currentThreadId();
    //    bytes.resize(MAX_LEN);//ADD 0309
    mutex.lock();

    cout<<"socket Available bytes:"<<m_camSocket->bytesAvailable()<<endl;
    //读到一张图的字节或超时，就退出循环！！  0404
    while(m_camSocket->waitForReadyRead(200)) //200--->300 尽量读取到1张图像的数据 20211023

    {
        //        bytes.append((QByteArray)m_camSocket->readAll());

        bytes.append((QByteArray)m_camSocket->read(CAM_ResolutionRatio*IMAGESIZE));
        bytesNum=m_camSocket->bytesAvailable();
        if(bytesNum>1E7){
            qDebug()<<"\n\n After read,socket bytes:"<<bytesNum<<endl;
            LogInfo("After read,socket bytes has too much:%ld\n",bytesNum);
        }
        if(bytes.size()>=CAM_ResolutionRatio*IMAGESIZE && bytes.size()<CAM_ResolutionRatio*IMAGESIZE*1.5)
        {
            qDebug()<<" ------Socket Read data.size():"<<bytes.size()<< "\n";
            //            static int testNum=0;
            //            bytes.insert()
            //            if(testNum<3){
            //                cout<<"bytes.length():"<<bytes.length()<<endl;
            //                for(auto i=4000;i<bytes.length()/1000;i++){
            //                    cout<<bytes[i]<<" "<<endl;
            //                }

            //                testNum++;
            //            }

            m_queue_camDataInCHAR.push_back(bytes);
            qDebug()<<"Push,queue size():"<<m_queue_camDataInCHAR.size()<< "\n";
            break;
        }

    }

    qDebug()<<" \n Total Read  data.size():"<<bytes.size()<< "\n";
    if( bytes.size() < CAM_ResolutionRatio*IMAGESIZE/4 ){
        cerr<<"\n not have enough bytes to read"<<endl; //add
    }
//    else{
//        qDebug()<<"Socket don't read a picture size:"<<bytes.size()<<endl;
//    }
    mutex.unlock();


    bytes.clear();
    if(bytes.size()<CAM_ResolutionRatio*IMAGESIZE||bytes.size()>CAM_ResolutionRatio*IMAGESIZE*1.5){

        m_NoDataTimes++;
        //网络连接断开后，是不能再启动定时器的，因此增加标志位判断  0302
        if(!b_realStopTimer){
            if(m_NoDataTimes>5){
                cmdTimer->start(2000);
            }
            if(m_NoDataTimes>20){
                cmdTimer->start(5000);
            }
        }

    }*/

}

QByteArray controlTCP::getOneFrameDATA()
{
    QMutexLocker locker(&m_queueQByteMutex);
    m_byteArray_oneFrame.clear(); //每次清除，能否避免double-linked list?? 0309
    if(m_queue_camDataInCHAR.size()!=0)
    {
        qDebug()<<" ------Get m_queue_camDataInCHAR.size():"<<m_queue_camDataInCHAR.size()<< "\n";
        //容易出错的地方 corrupted double-linked list  20220309！！
        if(m_queue_camDataInCHAR.isEmpty()!=true){
            m_byteArray_oneFrame=m_queue_camDataInCHAR.front();//this line!!!
        }

        //断开后，再次连接可能出错的地方 202201
        m_queue_camDataInCHAR.pop_front();
        //        qDebug()<<" After get, m_queue_camDataInCHAR.size():"<<m_queue_camDataInCHAR.size()<< "\n";
        //Get data.size(): -1734502249
        if(m_byteArray_oneFrame.size()>0)
        {
            return m_byteArray_oneFrame;
        }
        else
        {
            return "";
        }
    }
    else
    {
        return "";
    }

}

void controlTCP::recvDataOpt(void)
{

    QByteArray bytes=NULL;
    int read_times=0;
    while(m_camSocket->waitForReadyRead(400))
    {
        while(bytes.size()<=3*IMAGESIZE)
        {
            //每次只读1280*720的大小  0627
            bytes.append((QByteArray)m_camSocket->read(IMAGESIZE));
            qDebug()<<__func__<<__LINE__<<"\n One Read data.size():"<<bytes.size()<< "\n";
            read_times++;
            if(bytes.size()>=3*IMAGESIZE||read_times>=5)
            {
                qDebug()<<"\n Read finished,bytes.size(): "<<bytes.size()<< "\n";
                break;
            }
        }
        LogInfo("m_camSocket Read data.size() %d\n",bytes.size());
        break;

    }

    qDebug()<<__func__<<__LINE__<<"\n --------Read data.size():"<<bytes.size()<< "\n";
    emit dataReady(bytes);
}
