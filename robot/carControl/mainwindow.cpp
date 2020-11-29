#include "mainwindow.h"
#include "ui_mainwindow.h"
#include <QMessageBox>


MainWindow::MainWindow(QWidget *parent) :
    QMainWindow(parent),
    ui(new Ui::MainWindow)
{
    ui->setupUi(this);
    myTimer = new QTimer(this);
    pictureSocket = new QTcpSocket(this);
    controlSocket = new QTcpSocket(this);
    imageWidth=640;
    imageHeight=480;
    ui->lineEdit_IP->setText("192.168.0.105");


}

MainWindow::~MainWindow()
{
    delete ui;
}

void MainWindow::startTime(){
//    qDebug() << "fun: " <<__func__;
    ui->textBrowser_log->append("相机连接成功");
    myTimer->start(200);
}

void MainWindow::sendcmd(){
    pictureSocket->write("PIC");
    pictureSocket->flush();
}

/*-----------------------------图像传输-----------------------------------------------*/


void MainWindow::getpic(){

    int ret;
    char response[20];
    char *len;
    unsigned int piclen;
    char picbuf[1024 * 1024];
    qDebug() << "fun: " <<__func__;

    QByteArray bytes=NULL;
    while(pictureSocket->waitForReadyRead(100))
    {
        bytes.append((QByteArray)pictureSocket->readAll());
    }
    imageCount++;
    //    ReceiveCount->setText(QString::number(imagecount,10));
    memcpy(imagebuffer, bytes, IMAGESIZE);
    //    image_receive=new QImage(imagebuffer, imagewidth,imageheight,QImage::Format_RGB888);
    ShowImage(imagebuffer, imageWidth,imageHeight,QImage::Format_RGB888);
}

void MainWindow::on_pushButtonConnect_clicked()
{

    pictureSocket->connectToHost(addr,6800);
    qDebug()<<"connected Cam test";
    connect(pictureSocket,SIGNAL(connected()),this,SLOT(tips()));  //test
    connect(pictureSocket,SIGNAL(error(QAbstractSocket::SocketError)),this,SLOT(connectError()));
//    connect(pictureSocket,SIGNAL(error(QAbstractSocket::SocketError)),this,SLOT(connectError()));
    connect(pictureSocket,SIGNAL(connected()),this,SLOT(startTime()));

    connect(pictureSocket,SIGNAL(readyRead()),this,SLOT(getpic()));

    connect(myTimer,SIGNAL(timeout()),this,SLOT(sendcmd()));
}

void MainWindow::tips(){

    qDebug()<<"car connected OK";

}

void MainWindow::connectError()
{
    QMessageBox::warning(this,QString::fromLocal8Bit("错误"),QString::fromLocal8Bit("连接失败。可能IP地址错误，请重新输入!"));

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
    image = QImage(pRgbFrameBuf,nWidth, nHeight, QImage::Format_RGB888);
    // 将QImage的大小收缩或拉伸，与label的大小保持一致。这样label中能显示完整的图片
    // Shrink or stretch the size of Qimage to match the size of the label. In this way, the complete image can be displayed in the label
    QImage imageScale = image.scaled(QSize(ui->label_Pixmap->width(), ui->label_Pixmap->height()));
    QPixmap pixmap = QPixmap::fromImage(imageScale);
    ui->label_Pixmap->setPixmap(pixmap);

    //    m_mxDisplay.unlock();
    //    if(pRgbFrameBuf != NULL)
    //    {
    //        free(pRgbFrameBuf);
    //        pRgbFrameBuf = NULL;
    //    }

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
