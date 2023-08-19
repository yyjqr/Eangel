#ifndef CONTROLTCP_H
#define CONTROLTCP_H
#include <QTcpSocket>
#include <QTimer>
#include <QWidget>
//#include <vector>
//#include <queue>
#include <QQueue>
#include <QMutex>


using namespace std;



class controlTCP :public QTcpSocket
{
    Q_OBJECT
public:
    //    controlTCP();
    explicit controlTCP(QObject *parent = Q_NULLPTR,int imagesize=2764800);
    ~controlTCP();
    bool connectSocket(QString ip);
    bool connectSocket(QTcpSocket* m_tcpSocket,QString ip);
    bool disconnectSocket();
    QByteArray getOneFrameDATA(); //从二维数组中取出一帧数据
    void startSoftTrigAndCptTimer();

private slots:
    void startTime();
    void sendCmdToServer();
    void recvData(void);
    void recvDataOpt(void);
    void stopTimer();
signals:
    void dataReady(const QString &ip, const QByteArray &data);
    void dataReady(const QByteArray &data);
    void  signalSocketToRead();
    void signalSocketDisconnect();
private:
    QTcpSocket* pictureSocket;
    QTimer *cmdTimer;
<<<<<<< HEAD:robot/RobotControl-ThreadSocketOptQueue/src/controlTCP.h
    //10ms定时器 线程
//    CTimer* m_pTimer;
    //多线程读取与保护
    QMutex m_queueQByteMutex;
    QQueue<QByteArray> m_queue_camDataInCHAR;
    QMutex  mutex;
    QByteArray   m_byteArray_oneFrame;
    int  m_NoDataTimes;
    bool b_realStopTimer;
    uint m_read_image_size;
=======
//    queue<queue<char>> m_2vec_camDataInCHAR;
    QQueue<QByteArray> m_queue_camDataInCHAR;
    QMutex  mutex;
    QByteArray   m_byteArray_oneFrame;
>>>>>>> master:robot/RobotControl-Linux/src/controlTCP.h
};

#endif // CONTROLTCP_H
