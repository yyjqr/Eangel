#ifndef PICTURETHREAD_H
#define PICTURETHREAD_H
#include <QThread>
#include <vector>

#include <queue>
#include <QTimer>
#include "camSocketParam.h"
#include "controlTCP.h"
#include <QMutex>
using namespace std;



class MyThread : public QThread
{
    Q_OBJECT
public:
    MyThread();
    ~MyThread();
    //    void receivePic();
       void setThreadStop();
    //    camInfo getOneFrame();
    bool connectTCPSocket(QString addr);
    //取出一帧的数据，用于显示
    camInfo getCamOneFrame();
    void setThreadFlag(bool b_runFlag);

protected:
    virtual void run();

private:
     bool  getOneFrame();

private slots:
    void receivePic(QByteArray bytes);
    void receiveValidPicture(QByteArray bytes);
    void socket_disconnect();

//    void  getOneFrame();
signals:
    void SIGNAL_get_one_frame(camInfo);
    void SIGNAL_camSocketDisconnect();
private:
    bool b_run;

    int m_index=0;
    bool b_dataFlag;
    controlTCP* m_pictureSocket;
    QTcpSocket* m_tcpSocket;
    queue<camInfo> camSaveQueue;
//    QTimer *getFrameTimer;
    int imageCount=0;
    int imageWidth,imageHeight;
    //多线程读取与保护
    QMutex m_dataMutex;
    int m_countNOdata,m_tryGetDataTimes;
    QByteArray m_getFrame_byteArray;
    camInfo oneCamInfo;
    camInfo oneFrameInfo,OneTempFrame; //队列中取一帧数据,此后面声明变量有报错
    bool   b_dataValid;
    uint8_t *imageExtraDataBuf;
    int    m_countGet;
};

#endif // PICTURETHREAD_H
