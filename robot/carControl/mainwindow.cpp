#include "mainwindow.h"
#include "ui_mainwindow.h"
#include <QDateTime>

MainWindow::MainWindow(QWidget *parent) :
    QMainWindow(parent),
    ui(new Ui::MainWindow)
  ,b_grabPic(false)
  ,m_saveIndex(0)
{
    ui->setupUi(this);
    myTimer = new QTimer(this);
    pictureSocket = new QTcpSocket(this);
    controlSocket = new QTcpSocket(this);
    imageWidth=960;
    imageHeight=720;
    ui->lineEdit_IP->setText("192.168.0.100");
    connect(&systemTimer,SIGNAL(timeout()),this,SLOT(systemInfoUpdate()));
    addr="192.168.0.100";
}

MainWindow::~MainWindow()
{
    delete ui;
}

void MainWindow::startTime()
{
    qDebug() << "fun: " <<__func__;
    ui->textBrowser_log->append("相机连接成功");
    myTimer->start(300);
    systemTimer.start(500);
}

void MainWindow::sendcmd()
{
    pictureSocket->write("PIC");
    pictureSocket->flush();
    //    ui->label_RecvPictureNums->setText(QString::number(imageCount));
}

void MainWindow::getpic(){

    int ret;
    char response[20];
    char *len;
    unsigned int piclen;
    //    qDebug() << "fun: " <<__func__;

    QByteArray bytes=NULL;
    while(pictureSocket->waitForReadyRead(100))
    {
//        bytes.append((QByteArray)pictureSocket->read(IMAGESIZE));//readAll--->read
        bytes.append((QByteArray)pictureSocket->readAll());//readAll--->read
    }

    qDebug() <<"QByteArray size:" <<bytes.size();
    oneCamInfo.imageBuf=(uint8_t*)malloc(sizeof(uint8_t)*IMAGESIZE); //分配内存
    if(oneCamInfo.imageBuf!=nullptr)
    {
        qDebug()  <<"malloc pic mem OK\n";
    }
    if(bytes.size()<IMAGESIZE)
    {
//        memcpy(imagebuffer, bytes, bytes.size());
        memcpy(oneCamInfo.imageBuf,bytes,bytes.size());
        imageCount++;
    }
    else
    {
//        memcpy(imagebuffer, bytes, IMAGESIZE);
        memcpy(oneCamInfo.imageBuf,bytes,IMAGESIZE);
        imageCount++;
    }

    //   memcpy(imagebuffer, bytes, bytes.size());


    camSaveQueue.push(oneCamInfo);
    qDebug() <<" camSaveQueue.size() "<<camSaveQueue.size();
    if(camSaveQueue.size()!=0)
    {
        camInfo oneFrameInfo;
        oneFrameInfo=camSaveQueue.front();
        qDebug() <<"After get, camSaveQueue.size() "<<camSaveQueue.size();
        ShowImage(oneFrameInfo.imageBuf, imageWidth,imageHeight,QImage::Format_BGR888);//Format_RGB888---->Format_BGR888  (imread BGR格式）
        camSaveQueue.pop();//   弹出对首元素
    }
    //    ShowImage(imagebuffer, imageWidth,imageHeight,QImage::Format_RGB888);
}

void MainWindow::on_pushButtonConnect_clicked()
{

    pictureSocket->connectToHost(addr,6800);
    ui->textBrowser_log->append("连接ip:"+addr);
    qDebug()<<"connected Cam test";
    connect(pictureSocket,SIGNAL(connected()),this,SLOT(tips()));  //test
    connect(pictureSocket,SIGNAL(connected()),this,SLOT(startTime()));

    connect(pictureSocket,SIGNAL(readyRead()),this,SLOT(getpic()));

    connect(myTimer,SIGNAL(timeout()),this,SLOT(sendcmd()));
    connect(pictureSocket,SIGNAL(disconnected()),this,SLOT(socket_disconnect()));
}

void MainWindow::tips()
{
    ui->pushButtonConnect->setEnabled(false);
    qDebug()<<"car connected OK";

}

void MainWindow::socket_disconnect()
{
    ui->textBrowser_log->append("服务器断开连接\n");
    myTimer->stop();
    ui->pushButtonConnect->setEnabled(true);

}

void MainWindow::systemInfoUpdate()
{
    ui->label_RecvPictureNums->setText(QString::number(imageCount));
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
    ui->textBrowser_log->append("服务器断开连接\n");
    pictureSocket->disconnectFromHost();
    myTimer->stop();
    ui->pushButtonConnect->setEnabled(true);
}
