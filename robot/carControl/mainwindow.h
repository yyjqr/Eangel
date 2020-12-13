#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include  <QTcpSocket>
#include <QTimer>
#include <QMainWindow>
#include <vector>
 #include<queue>
//1280*720=921600
#define IMAGESIZE 921600
using namespace  std;

struct camInfo
{
    uint8_t *imageBuf=NULL;
    int imageWidth;
    int imageHeight;
    int type;
};


namespace Ui {
class MainWindow;
}

class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    explicit MainWindow(QWidget *parent = 0);
    ~MainWindow();
    QTimer *myTimer;
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
    bool ShowImage(uint8_t* pRgbFrameBuf, int nWidth, int nHeight, uint64_t nPixelFormat);
private slots:
    void on_pushButtonConnect_clicked();
    void sendcmd();
    void systemInfoUpdate();
private:
    Ui::MainWindow *ui;

    QTcpSocket* pictureSocket;
    QTcpSocket* controlSocket;
     QString addr,port;
     uchar imagebuffer[IMAGESIZE];
//     QVector2D
     QTimer systemTimer;
     vector<vector<uchar>> camData;
     queue<camInfo> camSaveQueue;

     int imageCount=0;
     int imageWidth,imageHeight;
     camInfo oneCamInfo;
private slots:
    void startTime();
    void getpic();
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
//    void onSocketReadyRead(); //读取socket传入的数据
    void on_pushButton_grab_clicked();
};

#endif // MAINWINDOW_H
