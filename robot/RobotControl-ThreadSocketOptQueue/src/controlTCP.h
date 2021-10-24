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
    explicit controlTCP(QObject *parent = Q_NULLPTR);
    ~controlTCP();
    bool connectSocket(QString ip);
    bool connectSocket(QTcpSocket* m_tcpSocket,QString ip);
    bool disconnectSocket();
    QByteArray getOneFrameDATA(); //从二维数组中取出一帧数据
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
    QTimer *myTimer;
//    queue<queue<char>> m_2vec_camDataInCHAR;
    QQueue<QByteArray> m_queue_camDataInCHAR;
    QMutex  mutex;
    QByteArray   m_byteArray_oneFrame;
};

#endif // CONTROLTCP_H
