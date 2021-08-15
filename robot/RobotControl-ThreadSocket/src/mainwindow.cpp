#include "mainwindow.h"
#include "ui_mainwindow.h"
#include <QDateTime>
#include "logging.h"

MainWindow::MainWindow(QWidget *parent) :
    QMainWindow(parent),
    ui(new Ui::MainWindow)
  ,b_grabPic(false)
  ,m_saveIndex(0)
  ,m_getImageCount(0)
{
    ui->setupUi(this);
    myTimer = new QTimer(this);
    systemTimer=new QTimer(this);
    controlSocket = new QTcpSocket(this);
    showThread= new MyThread();
    imageWidth=1280;
    imageHeight=720;
    addr="192.168.0.104";
    ui->lineEdit_IP->setText(addr);

    connect(systemTimer,SIGNAL(timeout()),this,SLOT(systemInfoUpdate()));
    //
    connect(showThread,SIGNAL(SIGNAL_get_one_frame(camInfo)),this,SLOT(getPicThread(camInfo)));
    //增加失去服务器连接的相关操作
    connect(showThread,SIGNAL(SIGNAL_camSocketDisconnect()),this,SLOT(on_pushButton_disconnect_clicked()));


}

MainWindow::~MainWindow()
{
    delete ui;

    delete controlSocket;
}

void MainWindow::startTime()
{
    qDebug() << "fun: " <<__func__;
    ui->textBrowser_log->append("相机连接成功");
    //    myTimer->start(300);
    systemTimer->start(500);
}


void MainWindow::on_pushButtonConnect_clicked()
{
    qDebug()<<"\n fun:"<<__func__<<"currentThreadId:"<<QThread::currentThreadId();
    QDateTime datetime;
    QString timestr=datetime.currentDateTime().toString("HH:mm:ss");
    ui->textBrowser_log->append(timestr+":连接ip:"+addr);
    if(showThread->connectTCPSocket(addr)){
        startTime();//开启系统定时
        showThread->start();
    }
    else {
        ui->textBrowser_log->append("连接ip:"+addr +"失败");
    }


    qDebug()<<"\n fun:"<<__func__<<__LINE__<<"connected Cam test";
    //将线程的接受信号和主线程的显示管理起来  0619
    //哪种方式来显示所取得的图像 0614
    //    connect(myTimer,SIGNAL(timeout()),this,SLOT(getPicThread()));
    //    connect(pictureSocket,SIGNAL(disconnected()),this,SLOT(socket_disconnect()));
}

void MainWindow::tips()
{
    ui->pushButtonConnect->setEnabled(false);
    qDebug()<<"car connected OK";

}

//相机接收socket数据线程
void MainWindow::getPicThread(camInfo frameToShow)
{
    qDebug()<<"\n fun:"<<__func__<<"currentThreadId:"<<QThread::currentThreadId();
    m_getImageCount++;
    //     qDebug() << "fun: " <<__func__<<"frameToShow.imageBuf:"<<frameToShow.imageBuf;
    //    qDebug() <<"frameToShow.imageHeight:"<<frameToShow.imageHeight;
    if(frameToShow.imageBuf!=nullptr){

        if(m_getImageCount%3==0){
            ShowImage(frameToShow.imageBuf, imageWidth,imageHeight,QImage::Format_BGR888);//Format_RGB888---->Format_BGR888  (imread BGR格式）
        }
        else
        {
            //add 未显示的数据，直接释放,避免内存增长 0620
            free(frameToShow.imageBuf);
            frameToShow.imageBuf=nullptr;
        }

    }
}

void MainWindow::systemInfoUpdate()
{
    //    camInfo picToshow=showThread->getCamOneFrame();
    //    qDebug() << "fun: " <<__func__<<"picToshow.imageBuf:"<<picToshow.imageBuf;
    //    if(picToshow.imageBuf!=nullptr)
    //    {

    //    getPicThread(picToshow);
    //    }
    ui->label_RecvPictureNums->setText(QString::number(m_getImageCount));

}
void MainWindow::on_pushButtonCAR_clicked()
{

    //    controlSocket->connectToHost("192.168.0.108",6868);
    controlSocket->connectToHost(addr,6868);
    ui->textBrowser_log->append("连接成功");
    //    ui->textBrowser_log->append(controlSocket->peerAddress().toString());
    connect(controlSocket,SIGNAL(connected()),this,SLOT(tips()));
}

bool MainWindow::ShowImage(uint8_t* pRgbFrameBuf, int nWidth, int nHeight, uint64_t nPixelFormat)
{
    QImage image;
    if (NULL == pRgbFrameBuf ||
            nWidth == 0 ||
            nHeight == 0)
    {
        printf("%s image is invalid.\n", __FUNCTION__);
        return false;
    }
    //    if (gvspPixelMono8 == nPixelFormat)
    //    {
    //        image = QImage(pRgbFrameBuf, nWidth, nHeight, QImage::Format_Grayscale8);
    //    }
    //    else
    //    {
    //        image = QImage(pRgbFrameBuf,nWidth, nHeight, QImage::Format_RGB888);
    //    }
    image = QImage(pRgbFrameBuf,nWidth, nHeight, QImage::Format_BGR888);
    if(b_grabPic==true)
    {
        QDateTime datetime;
        QString timestr=datetime.currentDateTime().toString("yyyyMMdd_HHmmss");
        QString SAVE_NAME=timestr+"_IMG_"+ QString::number(m_saveIndex)+"_"+".jpg";
        //qTempString +=SAVE_NAME;
        qDebug() <<"SAVE_NAME "<<SAVE_NAME;
        image.save(SAVE_NAME,"JPG",80);
        ui->textBrowser_log->append(QString::asprintf("截图成功%s",SAVE_NAME.toStdString().c_str()));
        m_saveIndex++;
        b_grabPic=false;
    }
    // 将QImage的大小收缩或拉伸，与label的大小保持一致。这样label中能显示完整的图片
    // Shrink or stretch the size of Qimage to match the size of the label. In this way, the complete image can be displayed in the label
    QImage imageScale = image.scaled(QSize(ui->label_Pixmap->width(), ui->label_Pixmap->height()));
    QPixmap pixmap = QPixmap::fromImage(imageScale);
    ui->label_Pixmap->setPixmap(pixmap);

    //    m_mxDisplay.unlock();
    if(pRgbFrameBuf != NULL)
    {
        free(pRgbFrameBuf);
        pRgbFrameBuf = NULL;
    }

    return true;


}

void MainWindow::STOP(){
    char buf[6] ="Pause";
    controlSocket->write(buf,sizeof(buf));
}

void MainWindow::UP(){
    char buf[3] = "VU";
    controlSocket->write(buf,sizeof(buf));
}
void MainWindow::DOWN(){
    char buf[3] = "VD";
    controlSocket->write(buf,sizeof(buf));
}
void MainWindow::LEFT(){
    char buf[3] = "HL";
    controlSocket->write(buf,sizeof(buf));
}
void MainWindow::RIGHT(){
    char buf[3] = "HR";
    controlSocket->write(buf,sizeof(buf));
}
/*-------------car control-----------------*/

void MainWindow::goHead(){
    char buf ='F';
    controlSocket->write(&buf,sizeof(buf));
}
void MainWindow::goBack(){
    char buf ='B';
    controlSocket->write(&buf,sizeof(buf));
}
void MainWindow::goLeft(){
    char buf ='L';
    controlSocket->write(&buf,sizeof(buf));
}
void MainWindow::goRight(){
    char buf ='R';
    controlSocket->write(&buf,sizeof(buf));
}
void MainWindow::goLeftHead(){
    char buf[2] ="5";
    controlSocket->write(buf,sizeof(buf));
}
void MainWindow::goLeftBack(){
    char buf[2] ="6";
    controlSocket->write(buf,sizeof(buf));
}
void MainWindow::goRightHead(){
    char buf[2] ="7";
    controlSocket->write(buf,sizeof(buf));
}
void MainWindow::goRightBack(){
    char buf[2] ="8";
    controlSocket->write(buf,sizeof(buf));
}

void MainWindow::on_pushButton_LEFT_pressed()
{
    LEFT();
}

void MainWindow::on_pushButton_UP_pressed()
{
    UP();
}

void MainWindow::on_pushButton_DOWN_pressed()
{
    DOWN();
}

void MainWindow::on_pushButton_RIGHT_pressed()
{
    RIGHT();
}

void MainWindow::on_pushButton_RIGHT_released()
{

}


/*-----------------------------小车方向-----------------------------------------------*/

void MainWindow::on_pushButtonCARFRONT_pressed()
{
    goHead();
}

void MainWindow::on_pushButtonCARFRONT_released()
{
    STOP();
}

void MainWindow::on_pushButtonCARLF_pressed()
{
    goLeftHead();
}

void MainWindow::on_pushButtonCARLF_released()
{
    STOP();
}

void MainWindow::on_pushButtonCARRF_pressed()
{
    goRightHead();
}

void MainWindow::on_pushButtonCARRF_released()
{
    STOP();
}

void MainWindow::on_pushButtonCARLEFT_pressed()
{
    goLeft();
}

void MainWindow::on_pushButtonCARLEFT_released()
{
    STOP();
}

void MainWindow::on_pushButtonCARRIGHT_pressed()
{
    goRight();
}

void MainWindow::on_pushButtonCARRIGHT_released()
{
    STOP();
}

void MainWindow::on_pushButtonCARLB_pressed()
{
    goLeftBack();
}

void MainWindow::on_pushButtonCARLB_released()
{
    STOP();
}

void MainWindow::on_pushButtonCARBACK_pressed()
{
    goBack();
}

void MainWindow::on_pushButtonCARBACK_released()
{
    STOP();
}

void MainWindow::on_pushButtonCARRB_pressed()
{
    goRightBack();
}

void MainWindow::on_pushButtonCARRB_released()
{
    STOP();
}


void MainWindow::on_lineEdit_IP_editingFinished()
{
    addr=ui->lineEdit_IP->text();

}

void MainWindow::on_lineEdit_port_editingFinished()
{
    port=ui->lineEdit_port->text();
}

void MainWindow::on_pushButtonCARRF_clicked()
{

}
//抓图判断
void MainWindow::on_pushButton_grab_clicked()
{
    b_grabPic=true;
}

void MainWindow::on_pushButton_disconnect_clicked()
{
    QDateTime datetime;
    QString timestr=datetime.currentDateTime().toString("HH:mm:ss");
    ui->textBrowser_log->setStyleSheet("color:red;");
    ui->textBrowser_log->append(timestr+"服务器断开连接\n");
    myTimer->stop();
    showThread->setThreadStop();
    ui->pushButtonConnect->setEnabled(true);
}
