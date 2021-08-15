#ifndef CONTROLTCP_H
#define CONTROLTCP_H
#include <QTcpSocket>
#include <QTimer>
#include <QWidget>
//#include "pictureThread.h"

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

};

#endif // CONTROLTCP_H
