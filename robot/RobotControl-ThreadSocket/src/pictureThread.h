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
//    camInfo getCamOneFrame();
protected:
    virtual void run();

private slots:
    void getPicThread();
    void receivePic(QByteArray bytes);
    void receivePic0(QByteArray bytes);
    void receivePic();
    void startTime();

    void sendCmdToServer();
    void socket_disconnect();

    void  getOneFrame();
signals:
    void SIGNAL_get_one_frame(camInfo);
private:
    //    volatile bool stopped;
    bool stopped;

    int m_index=0;
    bool b_dataFlag;
    controlTCP* m_pictureSocket;
    QTcpSocket* m_tcpSocket;
    queue<camInfo> camSaveQueue;
    QTimer *myTimer;
    QTimer *getFrameTimer;
    int imageCount=0;
    int imageWidth,imageHeight;
    int m_countNOdata;
    camInfo oneCamInfo;
    camInfo oneFrameInfo; //队列中取一帧数据,此后面声明变量有报错

    uint8_t *imageExtraDataBuf;

};

#endif // PICTURETHREAD_H
