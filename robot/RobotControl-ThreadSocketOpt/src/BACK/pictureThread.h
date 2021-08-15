#ifndef PICTURETHREAD_H
#define PICTURETHREAD_H
#include <QThread>
#include <vector>

#include <queue>
#include <QTimer>
#include "camSocketParam.h"
#include "controlTCP.h"
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
    void startTime();

    void sendCmdToServer();
    void socket_disconnect();

//    void  getOneFrame();
signals:
    void SIGNAL_get_one_frame(camInfo);
    void SIGNAL_camSocketDisconnect();
private:
    //    volatile bool stopped;
    bool b_run;

    int m_index=0;
    bool b_dataFlag;
    controlTCP* m_pictureSocket;
    QTcpSocket* m_tcpSocket;
    queue<camInfo> camSaveQueue;
    QTimer *myTimer;
    QTimer *getFrameTimer;
    int imageCount=0;
    int imageWidth,imageHeight;
    int m_countNOdata,m_tryGetDataTimes;
    camInfo oneCamInfo;
    camInfo oneFrameInfo; //队列中取一帧数据,此后面声明变量有报错
    bool   b_dataValid;
    uint8_t *imageExtraDataBuf;

};

#endif // PICTURETHREAD_H
