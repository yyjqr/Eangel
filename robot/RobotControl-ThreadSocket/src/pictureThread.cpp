#include "pictureThread.h"
#include <QDebug>
#include <QMutex>
#include <iostream>
#include <QFile>
#include <QTime>
#include "logging.h"

using namespace  std;
unsigned int extraDataSize=0;


MyThread::MyThread():
    stopped(false),
    oneCamInfo({nullptr,1280,720,0}),
    oneFrameInfo({nullptr,1280,720,0}),
    m_countNOdata(0)
{
    //    m_pictureSocket = new QTcpSocket(this); //add 0216
    myTimer = new QTimer(this);
    getFrameTimer = new QTimer(this);
    //    extraDataSize=0;
    m_pictureSocket = new controlTCP(this); //add 0216
    connect(getFrameTimer,SIGNAL(timeout()),this,SLOT(getOneFrame()));
  connect(m_pictureSocket,SIGNAL(dataReady(QByteArray)),this,SLOT(receivePic(QByteArray)));

}

MyThread::~MyThread()
{



}

void MyThread::startTime()
{
    qDebug() << "fun: " <<__func__;
    qDebug() << "connet server OK-----";
    myTimer->start(300);

}

void MyThread::run()
{
    QTime t,time_debug;

    qDebug()<< "thread.id"<<QThread::currentThreadId();
    int i=0;

    while(!stopped)
    {

        time_debug.start();
        //        receivePic();//通过run函数来开启图像接收线程

        //        qDebug()<<"ALG time"<<t.elapsed();
        if(i%4==0){
            getOneFrame();//每次取一帧
        }
        QThread::msleep(50);
        i++;
        //        if(i%10==0){
        //            qDebug()<<"i:"<<i<<"time:"<<time_debug.elapsed();
        //        }


    }
    //    qDebug() <<"thread exit";
    //    quit();//stop==true后，退出线程循环！！！

}

bool MyThread::connectTCPSocket(QString addr)
{
    qDebug() <<"thread ,test connect"<<__func__;
    //调用controlTCP的方法！！
    bool b_status=false;
    b_status =m_pictureSocket->connectSocket(addr);
    //    startTime();//add 发送命令的定时器 0619  22:15
    if(b_status)
    {
        getFrameTimer->start(1000);
        connect(myTimer,SIGNAL(timeout()),this,SLOT(sendCmdToServer()));
        return true;
    }
    else
    {
        return false;
    }

    //    connect(m_pictureSocket,SIGNAL(readyRead()),this,SLOT(getPicThread()));

    //    connect(m_pictureSocket,SIGNAL(disconnected()),this,SLOT(socket_disconnect()));
}

//相机接收socket数据线程
void MyThread::getPicThread()
{
    //    start();  //开启线程
}

void MyThread::sendCmdToServer()
{
    m_pictureSocket->write("PIC");
    m_pictureSocket->flush();
    qDebug()<<"fun"<<__func__<<"line"<<__LINE__<<"send CMD:PIC"<< "\n";
    //    ui->label_RecvPictureNums->setText(QString::number(imageCount));
}
void MyThread::receivePic()
{

    int ret;
    char response[20];
    char *len;
    unsigned int piclen;

    QByteArray bytes=NULL;
    while(m_pictureSocket->waitForReadyRead(400))
    {
        bytes.append((QByteArray)m_pictureSocket->read(3*IMAGESIZE));//readAll--->read
        if(bytes.size()>=3*IMAGESIZE) break;
    }
    LogInfo("bytes.size %d\n",bytes.size());
    qDebug() <<"QByteArray size:" <<bytes.size();
    oneCamInfo.imageBuf=(uint8_t*)malloc(sizeof(uint8_t)*IMAGESIZE*3); //分配内存 RGB 3倍

    if(oneCamInfo.imageBuf!=nullptr && bytes.size()<IMAGESIZE*3)
    {
        memcpy(oneCamInfo.imageBuf,bytes,bytes.size());
        qDebug() <<"bytes.size()<IMAGESIZE*3:" <<bytes.size();
        LogInfo("bytes.size()<IMAGESIZE*3 ,SIZE:%d\n",bytes.size());
        LogInfo("imageCount: %d\n",imageCount);
        imageCount++;
    }
    else if (oneCamInfo.imageBuf!=nullptr)
    {
        //        memcpy(imagebuffer, bytes, IMAGESIZE);
        memcpy(oneCamInfo.imageBuf,bytes,IMAGESIZE*3);
        qDebug() <<"bytes.size()>IMAGESIZE*3:" <<bytes.size();
        LogInfo("bytes.size()>=IMAGESIZE*3 ,SIZE:%d\n",bytes.size());
        LogInfo("imageCount: %d\n",imageCount);
        imageCount++;
    }
    else
    {
        qDebug()  <<"malloc pic mem failed\n";
        LogError("%s\n","malloc pic mem failed");
    }


    camSaveQueue.push(oneCamInfo);
    qDebug() <<"fun"<<__func__<<"line"<<__LINE__<<" camSaveQueue.size() "<<camSaveQueue.size();
    LogError("camSaveQueue.size() %d\n ",camSaveQueue.size());


}


void MyThread::receivePic0(QByteArray bytes)
{

    oneCamInfo.imageBuf=(uint8_t*)malloc(sizeof(uint8_t)*IMAGESIZE*3); //分配内存 RGB 3倍

    if(oneCamInfo.imageBuf!=nullptr && bytes.size()<IMAGESIZE*3)
    {
        memcpy(oneCamInfo.imageBuf,bytes,bytes.size());
        qDebug() <<"bytes.size()<IMAGESIZE*3:" <<bytes.size();
        LogInfo("bytes.size()<IMAGESIZE*3 ,SIZE:%d\n",bytes.size());
        LogInfo("imageCount: %d\n",imageCount);
        imageCount++;
    }
    else if (oneCamInfo.imageBuf!=nullptr)
    {
        //        memcpy(imagebuffer, bytes, IMAGESIZE);
        memcpy(oneCamInfo.imageBuf,bytes,IMAGESIZE*3);
        qDebug() <<"bytes.size()>IMAGESIZE*3:" <<bytes.size();
        LogInfo("bytes.size()>=IMAGESIZE*3 ,SIZE:%d\n",bytes.size());
        LogInfo("imageCount: %d\n",imageCount);
        imageCount++;
    }
    else
    {
        qDebug()  <<"malloc pic mem failed\n";
        LogError("%s\n","malloc pic mem failed");
    }


    camSaveQueue.push(oneCamInfo);
    qDebug() <<"fun"<<__func__<<"line"<<__LINE__<<" camSaveQueue.size() "<<camSaveQueue.size();
    LogError("camSaveQueue.size() %d\n ",camSaveQueue.size());
}

void MyThread::receivePic(QByteArray bytes)
{
//    qDebug()  <<" read cam data......\n";
    if(bytes.size()>0)
    {
        oneCamInfo.imageBuf=(uint8_t*)malloc(sizeof(uint8_t)*IMAGESIZE*3); //分配内存 RGB 3倍

        if(oneCamInfo.imageBuf!=nullptr)
        {
//            qDebug()  <<"malloc pic mem OK\n";
        }
        else
        {
            // 分配内存不成功，直接返回
            qDebug()  <<"malloc pic mem failed!......\n";
            return;
        }
        if(bytes.size()<IMAGESIZE*3)
        {
            qDebug() <<"\n Test bytes.size()<IMAGESIZE*3:" <<bytes.size()<<"extraDataSize:"<<extraDataSize;
            qDebug()<<"imageExtraDataBuf:"<<imageExtraDataBuf<<"\n"; //<<" "<<*imageExtraDataBuf
            if(extraDataSize>0&&extraDataSize<IMAGESIZE)
            {
                qDebug()<<__FUNCTION__<<__LINE__;
                //修改  判断imageExtraDataBuf指针  0320-----》  问题还是出在下面 0323
                if(imageExtraDataBuf!=nullptr){
                    qDebug()<<__FUNCTION__<<__LINE__;
                    qDebug()<<"imageExtraDataBuf: "<<imageExtraDataBuf;
                    try {
                        memcpy(oneCamInfo.imageBuf,imageExtraDataBuf,extraDataSize); //FIX ME 0317
                        throw "error";
                    }  catch (exception& e) {
                        cout << e.what() << endl;
                    }

                }

                if(imageExtraDataBuf!=nullptr)
                {
                    qDebug()<<__FUNCTION__<<__LINE__;
                    free(imageExtraDataBuf);
                }

                if(extraDataSize+bytes.size()<IMAGESIZE*3)
                {
                    //地址应在之前的基础上进行偏移！！！！！地址增加，按p+1进行计算，不用每次增加4个   0219
                    qDebug()<<__FUNCTION__<<__LINE__;
                    //                    printf("oneCamInfo.imageBuf:%x\n",oneCamInfo.imageBuf);
                    memcpy(oneCamInfo.imageBuf+extraDataSize,bytes,bytes.size());

                    //                    printf("Print oneCamInfo.imageBuf+extraDataSize:%x\n",oneCamInfo.imageBuf+extraDataSize);
                }
                else
                {
                    memcpy(oneCamInfo.imageBuf,bytes,IMAGESIZE*3-extraDataSize);
                }

            }
            else
            {
                memcpy(oneCamInfo.imageBuf,bytes,bytes.size());
            }

            qDebug() <<"bytes.size()<IMAGESIZE*3:" <<bytes.size();
            LogInfo("bytes.size()<IMAGESIZE*3 ,SIZE:%d\n",bytes.size());
            LogInfo("imageCount: %d\n",imageCount);
            imageCount++;
        }
        else
        {
            qDebug() <<"bytes.size()>=IMAGESIZE*3:" <<bytes.size();
            LogInfo("bytes.size()>=IMAGESIZE*3 ,SIZE:%d\n",bytes.size());
            LogInfo("imageCount: %d\n",imageCount);
            //对读取多余IMAGESIZE*3字节数据的存储，放到后面存储
            //第一次如果读取过多，就进行多余存储处理 0323！！
            extraDataSize=bytes.size()-IMAGESIZE*3;
            qDebug() <<"extraDataSize:" <<extraDataSize;
            if(extraDataSize>0)
            {
                //             qDebug() <<"bytes.right(extraDataSize):" <<bytes.right(extraDataSize);
                imageExtraDataBuf=(uint8_t*)malloc(sizeof(uint8_t)*IMAGESIZE); //分配内存 RGB 3倍
                if(imageExtraDataBuf!=nullptr){   //对分配内存的判断
                    memcpy(imageExtraDataBuf,bytes.right(extraDataSize),extraDataSize);  //数组多余字节拷贝！！！！！ 0218
                }

            }
            if(extraDataSize>0&&extraDataSize<IMAGESIZE)
            {
                qDebug()<<__FUNCTION__<<__LINE__<< "extraDataSize"<<extraDataSize<<\
                          "oneCamInfo.imageBuf+extraDataSize:%x"<<oneCamInfo.imageBuf+extraDataSize;
                //FIX ME
                qDebug()<<__LINE__<<"imageExtraDataBuf:"<<imageExtraDataBuf;
                // 增加指针判断 0320
                if(imageExtraDataBuf!=nullptr){
                    memcpy(oneCamInfo.imageBuf,imageExtraDataBuf,extraDataSize);
                }

                if(IMAGESIZE*3-extraDataSize<bytes.size())
                {
                    qDebug()<<__FUNCTION__<<__LINE__<<"IMAGESIZE*3-extraDataSize="<<IMAGESIZE*3-extraDataSize<<"<"<<bytes.size();
                    memcpy(oneCamInfo.imageBuf+extraDataSize,bytes,IMAGESIZE*3-extraDataSize);
                }
                else
                {
                    //IMAGESIZE*3-extraDataSize大于bytes.size()时，只能拷贝bytes.size()，避免内存溢出！  0317
                    qDebug()<<"IMAGESIZE*3-extraDataSize="<<IMAGESIZE*3-extraDataSize<<">"<<bytes.size();
                    memcpy(oneCamInfo.imageBuf+extraDataSize,bytes,bytes.size());
                }

                extraDataSize=0; //拷贝后，将其置零！！！！0323
                free(imageExtraDataBuf);
            }
            else
            {
                qDebug() <<"\n **********extraDataSize >IMAGESIZE:" <<extraDataSize;
                memcpy(oneCamInfo.imageBuf,bytes,IMAGESIZE*3);
                free(imageExtraDataBuf);
            }


            imageCount++;
        }
        qDebug() <<" \n -----Total bytes.size() "<<bytes.size()<<"------------ \n";
        //只把读取是完整字节及以上的数据存到队列  0620
        if(bytes.size()>=IMAGESIZE*3)
        {
        camSaveQueue.push(oneCamInfo);
        }
        //将cam数据加入队列后，这部分内存是否需要释放？？  0620目前内存可占用600MB以上
//        free(oneCamInfo.imageBuf);
        qDebug() <<" camSaveQueue.size() "<<camSaveQueue.size()<<"End \n\n";
        LogError("camSaveQueue.size() %d\n ",camSaveQueue.size());
    }
    else
    {
        LogError("Read size failed,size %d",bytes.size());
        return ;
    }
}



void MyThread::getOneFrame()
{
    if(camSaveQueue.size()!=0)
    {

        oneFrameInfo=camSaveQueue.front();
        qDebug() <<"After get, camSaveQueue.size() "<<camSaveQueue.size();
        camSaveQueue.pop();//   弹出队首元素
        qDebug() << "\n fun: " <<__func__<<__LINE__<<"oneFrameInfo.imageBuf:"<<oneFrameInfo.imageBuf;
        //        qDebug()<<"emit signal SIGNAL_get_one_frame";
        emit SIGNAL_get_one_frame(oneFrameInfo);
    }
    else
    {
        qDebug() <<"camSaveQueue.size():"<<camSaveQueue.size()<<"IS Empty,sleep... \n";
        msleep(500);
        m_countNOdata++;
        if(m_countNOdata>=5)
        {
            LogError("no data get,计数次数 %d",m_countNOdata);
            sleep(5);
            m_countNOdata=0;
        }
    }



}

//camInfo MyThread::getCamOneFrame()
//{
//    return oneCamInfo;
//}

void MyThread::socket_disconnect()
{

    myTimer->stop();

}


void MyThread::setThreadStop()
{
    m_pictureSocket->disconnectSocket();
    stopped=true;
}


