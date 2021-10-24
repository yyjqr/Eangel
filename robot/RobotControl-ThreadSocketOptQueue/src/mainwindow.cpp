#include "mainwindow.h"
#include "ui_mainwindow.h"

#include "logging.h"

MainWindow::MainWindow(QWidget *parent) :
    QMainWindow(parent),
    ui(new Ui::MainWindow)
  ,b_grabPic(false)
  ,m_saveIndex(0)
  ,m_getImageCount(0)
  ,m_picToshow({nullptr,1280,720,0})
{
    ui->setupUi(this);
    camTimer = new QTimer(this);
    systemTimer=new QTimer(this);
    controlSocket = new QTcpSocket(this);
    showThread= new MyThread();
    QStringList item_Resolution;
    item_Resolution<<"720p"<<"480p"<<"1080p";
    ui->comboBox_Res->addItems(item_Resolution);
    ui->comboBox_Res->setCurrentIndex(0);
    if(CAM_ResolutionRatio==3){
        m_imageWidth=1280;
        m_imageHeight=720;
    }

    addr="192.168.0.101";
    ui->lineEdit_IP->setText(addr);
    startTime();//开启系统定时
    connect(systemTimer,SIGNAL(timeout()),this,SLOT(systemInfoUpdate()));
    connect(camTimer,SIGNAL(timeout()),this,SLOT(onTimeGetFrameToShow()));
    //    connect(showThread,SIGNAL(SIGNAL_get_one_frame(camInfo)),this,SLOT(getPicThread(camInfo)));
    //增加失去服务器连接的相关操作
    connect(showThread,SIGNAL(SIGNAL_camSocketDisconnect()),this,SLOT(disconnect_Deal()));
    connect(showThread, SIGNAL(finished()), showThread, SLOT(deleteLater()));

}

MainWindow::~MainWindow()
{
    delete ui;
    if(camTimer!=nullptr){
        delete  camTimer;
        camTimer=nullptr;
    }
    if(systemTimer!=nullptr){
        delete  systemTimer;
        systemTimer=nullptr;
    }
    //线程结束
    if(controlSocket!=nullptr){
        delete controlSocket;
        controlSocket=nullptr;
    }
}

void MainWindow::startTime()
{
    qDebug() << "fun: " <<__func__;

    systemTimer->setTimerType(Qt::PreciseTimer);
    systemTimer->start(500);
}


void MainWindow::on_pushButtonConnect_clicked()
{
//    qDebug()<<"\n fun:"<<__func__<<"currentThreadId:"<<QThread::currentThreadId();
    QDateTime m_datetime;
    QString timestr=m_datetime.currentDateTime().toString("HH:mm:ss");
    ui->textBrowser_log->append(timestr+":连接ip:"+addr);
    if(showThread->connectTCPSocket(addr)){
        ui->textBrowser_log->append("相机连接成功");
        LogInfo("%s","相机连接成功");
        ui->pushButtonConnect->setStyleSheet("background-color:green;");
        camTimer->setTimerType(Qt::PreciseTimer);
        camTimer->start(400);
        //增加断开连接后，再次连接时，使能while循环标志，传输图片线程运行 0711
        showThread->setThreadFlag(true);
        showThread->start();
    }
    else {
        ui->pushButtonConnect->setStyleSheet("background-color:blue;");
        ui->textBrowser_log->append(timestr+"连接ip:"+addr +"失败");
        LogInfo("相机连接失败，ip %s",addr.toStdString().c_str());
    }

}

void MainWindow::tips()
{
    ui->pushButtonConnect->setEnabled(false);
    qDebug()<<"car connected OK";

}

//获取相机数据，来显示
void MainWindow::getPicToShow(camInfo& frameToShow)
{
    //    qDebug()<<"\n fun:"<<__func__<<"currentThreadId:"<<QThread::currentThreadId();
    m_getImageCount++;

    qDebug() <<"frameToShow m_getImageCount:"<<m_getImageCount;
    qDebug() << "fun: " <<__func__<<"frameToShow.imageBuf:"<<frameToShow.imageBuf;
    if(frameToShow.imageBuf!=nullptr){
        //每3帧显示一帧图像
        if(m_getImageCount%2==0)
        {
            qDebug() <<"\n"<<__LINE__<<"frameToShow -----"<<"frameToShow.imageBuf:"<<frameToShow.imageBuf;

            ShowImage(frameToShow.imageBuf, m_imageWidth,m_imageHeight,QImage::Format_RGB888);//(imread BGR格式） linux系统中只有Format_RGB888
        }
        else
        {
            //add 未显示的数据，直接释放,避免内存增长 0620
            qDebug() <<__LINE__<<"free buf\n";
            if(frameToShow.imageBuf!=nullptr){
                qDebug() <<__LINE__<<"analysis double free";
                try{
                    free(frameToShow.imageBuf);
                }
                catch(std::exception &e ){
                    std::cout << "Standard exception: " << e.what() << std::endl;
                    LogError("Standard exception %s\n",e.what());
                    qDebug()  <<"test free error----------\n";
                }

                frameToShow.imageBuf=nullptr;
            }

        }

    }
}


void MainWindow::getPicToShow()
{
    //    qDebug()<<"\n fun:"<<__func__<<"currentThreadId:"<<QThread::currentThreadId();
    m_getImageCount++;

    qDebug() <<"frameToShow m_getImageCount:"<<m_getImageCount;
//    qDebug() << "fun: " <<__func__<<"frameToShow.imageBuf:"<<m_picToshow.imageBuf;
    if(m_picToshow.imageBuf!=nullptr){
        //每3帧显示一帧图像
        if(m_getImageCount%2==0)
        {
            qDebug() <<"\n"<<__LINE__<<"frameToShow -----";  // <<"frameToShow.imageBuf:"<<m_picToshow.imageBuf;

            ShowImage(m_picToshow.imageBuf, m_imageWidth,m_imageHeight,QImage::Format_RGB888);//(imread BGR格式） linux系统中只有Format_RGB888

        }
        else
        {
            //add 未显示的数据，直接释放,避免内存增长 0620
            if(m_picToshow.imageBuf!=nullptr){
                qDebug() <<__LINE__<<"analysis double free";
                try{
                    free(m_picToshow.imageBuf);

                }
                catch(std::exception &e ){
                    std::cout << "Standard exception: " << e.what() << std::endl;
                    LogError("Standard exception %s\n",e.what());
                }

            }
        }

    }
}

void MainWindow::systemInfoUpdate()
{
    QDateTime datetime;
    QString timestr=datetime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss");
    ui->label_sysTime->setStyleSheet("color:green;");
    ui->label_sysTime->setText(timestr);

}
//定时取数据显示
void MainWindow::onTimeGetFrameToShow()
{
    QTime t_analysisMem;
    t_analysisMem.start();
    if(m_picToshow.imageBuf==nullptr) //开始为空,或者释放内存后再分配 0929test
    {
        m_picToshow.imageBuf=(uint8_t *)malloc(sizeof(uint8_t)*m_imageWidth*m_imageHeight);
        if(m_picToshow.imageBuf!=nullptr){
            //                 qDebug()<<"malloc OK";
        }
        else{
            qDebug()<<"malloc failed-------!!!!!!!";
            LogError("%s","CAM DATA malloc failed, so not to show in GUI\n");
            return;
        }

    }
//    qDebug()<<"malloc mem time:"<<t_analysisMem.elapsed();
    m_picToshow=showThread->getCamOneFrame();
//    qDebug() << "fun: " <<__func__<<"picToshow.imageBuf:"<<m_picToshow.imageBuf;
    if(m_picToshow.imageBuf!=nullptr)
    {
        getPicToShow();
        m_picToshow.imageBuf=nullptr;//显示后，将其置空 0717
    }
    ui->label_RecvPictureNums->setText(QString::number(m_getImageCount));

}
void MainWindow::on_pushButtonCAR_clicked()
{
    controlSocket->connectToHost(addr,8200);
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
    image = QImage(pRgbFrameBuf,nWidth, nHeight, QImage::Format_RGB888);//Format_BGR888 --->Format_RGB888
    if(b_grabPic==true)
    {
        QDateTime datetime;
        QString timestr=datetime.currentDateTime().toString("yyyyMMdd_HHmmss");
        QString SAVE_NAME=timestr+"_IMG_"+ QString::number(m_saveIndex)+".jpg";
        qDebug()<<__LINE__<<" inside,test grab error";
        qDebug() <<"SAVE_NAME "<<SAVE_NAME;
        image.save(SAVE_NAME,"JPG",80);
        QString timestrLog=datetime.currentDateTime().toString("HH:mm:ss");
        ui->textBrowser_log->append(timestrLog+QString::asprintf("截图成功%s",SAVE_NAME.toStdString().c_str()));
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
//        qDebug()<<__LINE__<<"test free buf\n";
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
    QDateTime datetime;
    QString timestr=datetime.currentDateTime().toString("HH:mm:ss.zzz");
    qDebug()<<timestr<<"analysis grab error"<<__LINE__<<endl;
    b_grabPic=true;
}

void MainWindow::on_pushButton_disconnect_clicked()
{
    QDateTime datetime;
    QString timestr=datetime.currentDateTime().toString("HH:mm:ss");
    ui->textBrowser_log->setStyleSheet("color:red;");
    ui->textBrowser_log->append(timestr+"服务器断开连接\n");
    LogInfo("%s","服务器断开");
    camTimer->stop();
    showThread->setThreadStop();
    //    qDebug()<<"test close error";
    ui->pushButtonConnect->setEnabled(true);
}


void MainWindow::disconnect_Deal()
{
    QDateTime datetime;
    QString timestr=datetime.currentDateTime().toString("HH:mm:ss");
    ui->textBrowser_log->setStyleSheet("color:red;");
    ui->textBrowser_log->append(timestr+"服务器断开连接\n");
    ui->pushButtonConnect->setEnabled(true);
}

void MainWindow::on_comboBox_Res_currentIndexChanged(int index)
{
    qDebug()<<"Resolution select index:"<<index;
    switch (index) {
    case 1:
        m_CAM_ResolutionRatio=3;
        break;
    case 2:
        m_CAM_ResolutionRatio=1;
        break;
    case 3:
        m_CAM_ResolutionRatio=3;
        break;
    default:
        m_CAM_ResolutionRatio=3;
    }
    if(m_CAM_ResolutionRatio==3){
        m_imageWidth=1280;
        m_imageHeight=720;
    }
    else if(m_CAM_ResolutionRatio==1){
        m_imageWidth=640;
        m_imageHeight=480;
    }
    else{
        m_imageWidth=1920;
        m_imageHeight=1080;
    }
}

