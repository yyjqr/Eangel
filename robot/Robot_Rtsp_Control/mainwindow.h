#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QMainWindow>
#include <QDateTime>
#include <QTimer>
#include <QTcpSocket>
#include "videoplayer.h"

QT_BEGIN_NAMESPACE
namespace Ui { class MainWindow; }
QT_END_NAMESPACE

class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    MainWindow(QWidget *parent = nullptr);
    ~MainWindow();
    QString getCurrentTime();
    void ParseFromJson();

    /*---------------*/
    //通过socket的方法，将单个字母的命令写入buffer
    void writeCmdToSocketBuf(char cmd);
    //通过socket的方法，将字符串的命令写入buffer
    void writeCmdStringToSocketBuf(char *pCmd );
    void STOP();
    void goHead();
    void goBack();
    void goLeft();
    void goRight();
    void goLeftHead();
    void goLeftBack();
    void goRightHead();
    void goRightBack();
    // 清除之前发送或单片机已接收的命令buffer,避免多次执行，或响应缓慢
    void cleanCommandBuffer();
private:
    void saveImage(QImage img);
    void startTime();
    void warningOnce(QString info);

private slots:
    void on_startButton_clicked();
    void on_pauseButton_clicked(bool checked);
    void closeEvent(QCloseEvent *event);


    void slotGetOneFrame(QImage img);

    void on_pushButton_saveImg_clicked();
    void systemInfoUpdate();
    void on_pushButton_CARconnect_clicked();

    void on_comboBox_ipAddr_currentTextChanged(const QString &arg1);

    void on_pushButton_goFront_clicked();

    void on_pushButtonCARBACK_clicked();

    void on_pushButton_turnLeft_clicked();

    void on_pushButton_turnRight_clicked();

    void carControl();
    void on_pushButton_stop_clicked();

    void on_pushButton_disconnect_clicked();

    void onDisconnect();
    //接收客户端，智能车返回的相关车辆异常或其它数据 0520
    void recvData(void);

    void on_pushButton_clearCommand_clicked();

    // void on_pushButton_playControl_clicked(bool checked);

private:
    Ui::MainWindow *ui;
    VideoPlayer *mPlayer;
    bool mPlayer_run_flag;
    bool b_grabPic;
    int m_saveIndex;
    QTimer* p_systemTimer;
    QString m_str_addr,port;
//    QTimer *camTimer;
    QDateTime m_datetime;
    QString m_timestr, m_sysTimestr;
    QTcpSocket *p_controlSocket;
    QString m_ip_addr1,m_ip_addr2,m_ip_addr3,m_ip_addr4;
    const std::string m_ip_config_path="./CONFIG/ipAddr.conf";
};
#endif // MAINWINDOW_H
