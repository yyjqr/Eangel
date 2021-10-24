#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include  <QTcpSocket>
#include <QTimer>
#include <QMainWindow>
#include <vector>
#include<queue>
#include <QMetaType> //跨线程的信号和槽的参数传递中, 参数的类型是自定义的类型
#include "camSocketParam.h"
#include "pictureThread.h"
#include "controlTCP.h"
#include <QDateTime>
using namespace  std;


namespace Ui {
class MainWindow;
}

class MainWindow : public QMainWindow
{
    Q_OBJECT

public:

    explicit MainWindow(QWidget *parent = 0);
    ~MainWindow();

    void UP();
    void DOWN();
    void LEFT();
    void RIGHT();

    /*---------------*/
    void STOP();
    void goHead();
    void goBack();
    void goLeft();
    void goRight();
    void goLeftHead();
    void goLeftBack();
    void goRightHead();
    void goRightBack();
    void getPicToShow();
    bool ShowImage(uint8_t* pRgbFrameBuf, int nWidth, int nHeight, uint64_t nPixelFormat);
//    bool ShowImageOpt(int nWidth, int nHeight, uint64_t nPixelFormat);
private slots:
    void on_pushButtonConnect_clicked();
    void systemInfoUpdate();
    void onTimeGetFrameToShow();
    void startTime();
    void getPicToShow(camInfo& frameToShow);  //add 0213
    void tips();
    void on_pushButton_LEFT_pressed();
    //    void on_pushButton_LEFT_released();
    void on_pushButton_UP_pressed();
    void on_pushButton_DOWN_pressed();
    void on_pushButton_RIGHT_pressed();
    void on_pushButton_RIGHT_released();
    void on_pushButtonCARFRONT_pressed();
    void on_pushButtonCARFRONT_released();
    void on_pushButtonCARLF_pressed();
    void on_pushButtonCARLF_released();
    void on_pushButtonCARRF_pressed();
    void on_pushButtonCARRF_released();
    void on_pushButtonCARLEFT_pressed();
    void on_pushButtonCARLEFT_released();
    void on_pushButtonCARRIGHT_pressed();
    void on_pushButtonCARRIGHT_released();
    void on_pushButtonCARLB_pressed();
    void on_pushButtonCARLB_released();
    void on_pushButtonCARBACK_pressed();
    void on_pushButtonCARBACK_released();
    void on_pushButtonCARRB_pressed();
    void on_pushButtonCARRB_released();
    void on_pushButtonCAR_clicked();
    void on_lineEdit_IP_editingFinished();
    void on_lineEdit_port_editingFinished();
    void on_pushButtonCARRF_clicked();

    void on_pushButton_grab_clicked();
    void on_pushButton_disconnect_clicked();
    void  disconnect_Deal(); //socket 断开连接后，触发主线程的信号
    void on_comboBox_Res_currentIndexChanged(int index);

private:
    Ui::MainWindow *ui;

    QTcpSocket* controlSocket;
    QString addr,port;
    uchar imagebuffer[IMAGESIZE];
    //     QVector2D
    QTimer* systemTimer;
    QTimer *camTimer;
    queue<camInfo> camSaveQueue;


    int imageCount=0;
    int m_imageWidth,m_imageHeight;
    camInfo m_picToshow;
    camInfo oneCamInfo;
    bool b_grabPic;
    int m_saveIndex;

    MyThread *showThread;
    int m_getImageCount;
    int m_CAM_ResolutionRatio;

};

#endif // MAINWINDOW_H
