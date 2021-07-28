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
    b_run(true),
    oneCamInfo({nullptr,1280,720,0}),
    oneFrameInfo({nullptr,1280,720,0}),
    b_dataValid(false),
    m_countNOdata(0),
    imageExtraDataBuf(nullptr),
    m_tryGetDataTimes(0)
{
    myTimer = new QTimer(this);
    getFrameTimer = new QTimer(this);
    //    extraDataSize=0;
    m_pictureSocket = new controlTCP(this); //add 0216
    //    connect(getFrameTimer,SIGNAL(timeout()),this,SLOT(getOneFrame()));
    //    connect(m_pictureSocket,SIGNAL(dataReady(QByteArray)),this,SLOT(receivePic(QByteArray)));
    connect(m_pictureSocket,SIGNAL(dataReady(QByteArray)),this,SLOT(receiveValidPicture(QByteArray)));
    connect(m_pictureSocket,SIGNAL(signalSocketDisconnect()),this,SLOT(socket_disconnect()));
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

    qDebug()<<__func__<< "currentThreadId"<<QThread::currentThreadId();
    int i=0;

    while(b_run)
    {

        time_debug.start();
        if(camSaveQueue.size()>=2){
            getOneFrame();//每次取一帧
            qDebug()<<"getOneFrame time"<<time_debug.elapsed();
                        QThread::msleep(150);//避免显示取不到 或卡住 0704
        }
        else{
            QThread::msleep(200);
            m_tryGetDataTimes++;
            LogInfo("m_tryGetDataTimes: %d\n",m_tryGetDataTimes);
            if(m_tryGetDataTimes%5==0){
                QThread::sleep(1);
                //睡眠1秒后，有数据，将之前的计数清零，避免取数据不及时
                if(camSaveQueue.size()!=0){
                    m_tryGetDataTimes=0;
                }
            }
            if(m_tryGetDataTimes%10==0){
                QThread::sleep(3);

            }
            //超过50次未获取数据，睡眠5s，线程不能退出，否则数据一直累积！！ 0704
            if(m_tryGetDataTimes>=50)
            {
                qDebug()<<"thread stop...m_tryGetDataTimes:"<<m_tryGetDataTimes;
                QThread::sleep(5);
                LogError("m_tryGetDataTimes: %d >50次\n",m_tryGetDataTimes);
                m_tryGetDataTimes=0;
            }
            qDebug()<<"After sleep, ALG time"<<time_debug.elapsed();
        }
//        QThread::msleep(100);//避免显示取不到 或卡住 0704
        i++;

    }

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
        getFrameTimer->start(800);
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



void MyThread::sendCmdToServer()
{
    m_pictureSocket->write("PIC");
    m_pictureSocket->flush();
    qDebug()<<"fun"<<__func__<<"line"<<__LINE__<<"send CMD:PIC"<< "\n";
    //    ui->label_RecvPictureNums->setText(QString::number(imageCount));
}


void MyThread::receiveValidPicture(QByteArray bytes)
{
    if(bytes.size()>=IMAGESIZE*3)
    {
        oneCamInfo.imageBuf=(uint8_t*)malloc(sizeof(uint8_t)*IMAGESIZE*3); //分配内存 RGB 3倍

        if (oneCamInfo.imageBuf!=nullptr)
        {
            memcpy(oneCamInfo.imageBuf,bytes,IMAGESIZE*3);
            qDebug() <<"bytes.size()>=IMAGESIZE*3:" <<bytes.size();
            LogInfo("bytes.size()>=IMAGESIZE*3 ,SIZE:%d\n",bytes.size());
            LogInfo("imageCount: %d\n",imageCount);
            imageCount++;
            camSaveQueue.push(oneCamInfo);
            qDebug() <<"fun"<<__func__<<"line"<<__LINE__<<" camSaveQueue.size() "<<camSaveQueue.size();
            LogError("camSaveQueue.size() %d\n ",camSaveQueue.size());
        }
        else
        {
            qDebug()  <<"malloc pic mem failed\n";
            LogError("%s\n","malloc pic mem failed");
        }
    }
    else
    {
         qDebug()<<__func__<<":"<<__LINE__<<"clear small size cam data\n";
        bytes.clear();
    }



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
                qDebug()<<__func__<<__LINE__;
                //修改  判断imageExtraDataBuf指针  0320-----》  问题还是出在下面 0323
                if(imageExtraDataBuf!=nullptr){
                    qDebug()<<__func__<<__LINE__;
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
                    qDebug()<<__func__<<__LINE__;
                    free(imageExtraDataBuf);
                }

                if(extraDataSize+bytes.size()<IMAGESIZE*3)
                {
                    //地址应在之前的基础上进行偏移！！！！！地址增加，按p+1进行计算，不用每次增加4个   0219
                    qDebug()<<__func__<<__LINE__;
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

                if(extraDataSize>0&&extraDataSize<IMAGESIZE)
                {
                    qDebug()<<__func__<<__LINE__<< "extraDataSize"<<extraDataSize<<\
                              "oneCamInfo.imageBuf+extraDataSize:%x"<<oneCamInfo.imageBuf+extraDataSize;
                    //FIX ME
                    qDebug()<<__LINE__<<"imageExtraDataBuf:"<<imageExtraDataBuf;
                    // 增加指针判断 0320
                    if(imageExtraDataBuf!=nullptr){
                        memcpy(oneCamInfo.imageBuf,imageExtraDataBuf,extraDataSize);
                    }

                    if(IMAGESIZE*3-extraDataSize<bytes.size())
                    {
                        qDebug()<<__func__<<__LINE__<<"IMAGESIZE*3-extraDataSize="<<IMAGESIZE*3-extraDataSize<<"<"<<bytes.size();
                        memcpy(oneCamInfo.imageBuf+extraDataSize,bytes,IMAGESIZE*3-extraDataSize);
                    }
                    else
                    {
                        //IMAGESIZE*3-extraDataSize大于bytes.size()时，只能拷贝bytes.size()，避免内存溢出！  0317
                        qDebug()<<"IMAGESIZE*3-extraDataSize="<<IMAGESIZE*3-extraDataSize<<">"<<bytes.size();
                        memcpy(oneCamInfo.imageBuf+extraDataSize,bytes,bytes.size());
                    }

                    extraDataSize=0; //拷贝后，将其置零！！！！0323
                    //优化指针内存的释放 0621
                    if(imageExtraDataBuf!=nullptr){
                        free(imageExtraDataBuf);
                        imageExtraDataBuf=nullptr;
                    }
                }
                else
                {
                    qDebug() <<"\n **********extraDataSize >IMAGESIZE:" <<extraDataSize;
                    memcpy(oneCamInfo.imageBuf,bytes,IMAGESIZE*3);
                    if(imageExtraDataBuf!=nullptr){
                        free(imageExtraDataBuf);
                        imageExtraDataBuf=nullptr;
                    }

                }

            }
            else
            {
                qDebug()<< "read just the right size~~~~~~~~\n";
                memcpy(oneCamInfo.imageBuf,bytes,bytes.size());
            }


            imageCount++;
        }
        qDebug() <<" \n -----Total bytes.size() "<<bytes.size()<<"------------ \n";
        //只把读取是完整字节及以上的数据存到队列  0620----->bytes.size()+extraDataSize  0626
        //将cam数据加入队列后，这部分内存需要释放
        if(bytes.size()+extraDataSize>=IMAGESIZE*3)
        {
            camSaveQueue.push(oneCamInfo);
        }
        else if(bytes.size()+extraDataSize>=IMAGESIZE)
        {
            camSaveQueue.push(oneCamInfo);
        }
        else
        {
            qDebug()<<__LINE__<<"read bytes.size()+extraSize<IMAGESIZE*3,free mem...\n";
            free(oneCamInfo.imageBuf);
            oneCamInfo.imageBuf=nullptr;
        }

        qDebug() <<" camSaveQueue.size() "<<camSaveQueue.size()<<"End \n";
        LogError("camSaveQueue.size() %d\n ",camSaveQueue.size());
    }
    else
    {
        LogError("Read size failed,size %d",bytes.size());
        return ;
    }
}



bool MyThread::getOneFrame()
{
    if(camSaveQueue.size()!=0)
    {
        oneFrameInfo=camSaveQueue.front();
        qDebug() << "\n fun: " <<__func__<<__LINE__<<"After get, camSaveQueue.size() "<<camSaveQueue.size();
        camSaveQueue.pop();//   弹出队首元素
        //qDebug() <<"oneFrameInfo.imageBuf:"<<oneFrameInfo.imageBuf;
        //        qDebug()<<"emit signal SIGNAL_get_one_frame";
//        emit SIGNAL_get_one_frame(oneFrameInfo);
        b_dataValid=true;
        return true;
    }
    else
    {
        qDebug() <<"camSaveQueue.size():"<<camSaveQueue.size()<<"IS Empty,sleep... \n";
        msleep(500);
        m_countNOdata++;
        if(m_countNOdata>=5)
        {
            LogError("no data get,计数次数 %d",m_countNOdata);
            sleep(2);
            m_countNOdata=0;
        }
        b_dataValid=false;
         return false;
    }
    return false;



}

camInfo MyThread::getCamOneFrame()
{

      if(b_dataValid){
          qDebug() << "\n fun: " <<__func__<<__LINE__<<"get one frame to show\n ";
          return oneFrameInfo; //取队列中弹出的一帧数据 0717
      }
      else{
          qDebug() << " fun: " <<__func__<<__LINE__<<"NO frame to show-----\n ";
               return {nullptr,1280,720,0};
      }



}

void MyThread::socket_disconnect()
{

    myTimer->stop();
    getFrameTimer->stop();
    emit SIGNAL_camSocketDisconnect();
    if(camSaveQueue.size()==0){
        b_run=true;
    }

}


void MyThread::setThreadStop()
{
    m_pictureSocket->disconnectSocket();
    b_run=false;
}

void MyThread::setThreadFlag(bool b_runFlag)
{
    b_run=b_runFlag;
}


