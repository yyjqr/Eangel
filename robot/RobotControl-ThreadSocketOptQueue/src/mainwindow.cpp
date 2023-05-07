/**
 *  @brief   Robot control GUI,based on USB cam and socket,tcp.
 *  机器人交互控制界面，采用USB摄像头，基于tcp,socket进行传输，qt多线程开发
 *  @author  Jack
 *  @date  2020.12-2022.08
 *  @E-mail  yyjqr789@sina.com
*/

#include "mainwindow.h"
#include "ui_mainwindow.h"
#include "logging.h"
#include "jsonxx/json.hpp"
#include <sstream>
#include <iostream>
#include <fstream>

#define TEXT_COLOR_RED(STRING)         "<font color=red>" STRING "</font>" "<font color=black> </font>"
#define TEXT_COLOR_BLUE(STRING)        "<font color=blue>" STRING "</font>" "<font color=black> </font>"
#define TEXT_COLOR_GREEN(STRING)       "<font color=green>" STRING "</font>" "<font color=black> </font>"
stCamResolution  stCamLowRes={ 640,480,Small_480p};
stCamResolution  stCommon720pRes={ 1280,720,Common_Type720p};




MainWindow::MainWindow(QWidget *parent) :
    QMainWindow(parent),
    ui(new Ui::MainWindow)
  ,b_grabPic(false)
  ,m_saveIndex(0)
  ,m_getImageCount(0)
  ,m_getOneTimeImageNums(0)
  ,showThread(nullptr)
  ,m_picToshow({nullptr,1280,720,0})
  ,m_NoDataToShow_Times(0)
  ,m_imageSize(2764800)
{
    ui->setupUi(this);
    ui->pushButton_disconnect->setEnabled(false);
    camTimer = new QTimer(this);
    systemTimer=new QTimer(this);
    controlSocket = new QTcpSocket(this);
    //    showThread= new CamThread();
    QStringList item_Resolution,item_ipAddrs;
    item_Resolution<<"720p"<<"480p"<<"1080p";
    ui->comboBox_Res->addItems(item_Resolution);
    ui->comboBox_Res->setCurrentIndex(0);
    if(CAM_ResolutionRatio==3){
        m_imageWidth=1280;
        m_imageHeight=720;
    }
    ParseFromJson();
    if(m_ip_addr1.isNull()!=true){
        item_ipAddrs<<m_ip_addr1<<m_ip_addr2<<m_ip_addr3<<m_ip_addr4;
    }

    ui->comboBox_ipAddr->addItems(item_ipAddrs);
    ui->comboBox_ipAddr->setCurrentIndex(0);

    initControlUI(false);

    startTime();//开启系统定时
    connect(systemTimer,SIGNAL(timeout()),this,SLOT(systemInfoUpdate()));
    connect(camTimer,SIGNAL(timeout()),this,SLOT(onTimeGetFrameToShow()));


    //    connect(showThread, SIGNAL(finished()), showThread, SLOT(deleteLater()));//信号槽中已有删除，析构函数中使用的回收资源更清晰！！！

}


MainWindow::~MainWindow()
{
    //释放socket的资源
    if(controlSocket!=nullptr){
        delete controlSocket;
        controlSocket=nullptr;
    }
    //线程结束 删除线程资源202201
    qDebug()<<__LINE__<<"try to delete thread"<<endl;
    showThread->setThreadStop();
    //退出线程 0116
    showThread->quit();
    //回收资源
    showThread->wait();
    if(showThread!=nullptr){
        delete showThread;
        showThread=nullptr;
    }

    if(camTimer!=nullptr){
        delete  camTimer;
        camTimer=nullptr;
    }
    if(systemTimer!=nullptr){
        delete  systemTimer;
        systemTimer=nullptr;
    }
    delete ui;

}

void MainWindow::initControlUI(bool flag)
{
    ui->pushButtonCARFRONT->setEnabled(flag);
    ui->pushButtonCARBACK->setEnabled(flag);
    ui->pushButtonCARLEFT->setEnabled(flag);
    ui->pushButtonCARRIGHT->setEnabled(flag);
}

void MainWindow::startTime()
{
    qDebug() << "fun: " <<__func__;

    systemTimer->start(500);
}


void MainWindow::on_pushButtonConnect_clicked()
{
    //    qDebug()<<"\n fun:"<<__func__<<"currentThreadId:"<<QThread::currentThreadId();
    m_getOneTimeImageNums=0;
    ui->textBrowser_log->append(m_timestr+":连接ip:"+m_str_addr);
    if(showThread==nullptr){
        qDebug()<<"\n fun:"<<__func__<<"showThread ptr:"<<showThread;
        showThread= new CamThread(m_imageSize);
        //增加失去服务器连接的相关操作--->revise to this 0821
        connect(showThread,SIGNAL(SIGNAL_camSocketDisconnectToMainThread()),this,SLOT(disconnect_Deal()));
    }
    if(showThread->connectTCPSocket(m_str_addr,m_imageSize)){
        qDebug()<<"\n Test fun:"<<__func__<<"showThread ptr:"<<showThread<<endl;
        ui->textBrowser_log->append(TEXT_COLOR_GREEN("相机连接成功\n"));
        LogInfo("%s","相机连接成功");
        ui->pushButtonConnect->setStyleSheet("background-color:green;");
        ui->pushButtonConnect->setEnabled(false);
        ui->pushButton_disconnect->setEnabled(true);

        camTimer->setTimerType(Qt::PreciseTimer);
        camTimer->start(400);
        //增加断开连接后，再次连接时，使能while循环标志，传输图片线程运行 0711
        showThread->setThreadFlag(true);
        showThread->start();
    }
    else {
        ui->pushButtonConnect->setStyleSheet("background-color:blue;");
        QString tmp_qstr=m_timestr+"连接ip:"+m_str_addr +"失败";
        ui->textBrowser_log->append(TEXT_COLOR_RED("连接失败"));
        LogInfo("相机连接失败，ip %s",m_str_addr.toStdString().c_str());
        ui->pushButtonConnect->setEnabled(true);
    }

}

void MainWindow::tips()
{
    ui->pushButtonConnect->setEnabled(false);
    qDebug()<<"car connected OK";

}

//获取相机数据，来显示
void MainWindow::getPicToShow()
{
    //    qDebug()<<"\n fun:"<<__func__<<"currentThreadId:"<<QThread::currentThreadId();
    m_getOneTimeImageNums++;
    m_getImageCount++;

    qDebug() <<"frameToShow m_getImageCount:"<<m_getImageCount;

    if(m_picToshow.imageBuf!=nullptr){
        //每3帧显示一帧图像
        if(m_getImageCount%2==0)
        {
            //            qDebug() <<"\n"<<__LINE__<<"frameToShow -----";  // <<"frameToShow.imageBuf:"<<m_picToshow.imageBuf;
            assert(m_picToshow.imageBuf!=nullptr);
            ShowImage(m_picToshow.imageBuf, m_imageWidth,m_imageHeight,QImage::Format_RGB888);//(imread BGR格式） linux系统中只有Format_RGB888
            qDebug() <<"\n"<<__LINE__<<"Show frame finish----";
        }
        else
        {
            //add 未显示的数据，直接释放,避免内存增长 0620
            if(m_picToshow.imageBuf!=nullptr){

                //重点调试地方！！！！(maybe the QArray data operate sometimes error!!
                try{
//                    qDebug()<<__LINE__<<"test free IMAGE buf\n";
                    assert(m_picToshow.imageBuf!=nullptr);
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
    //        qDebug() <<m_sysTimestr<<":系统时间更新测试\n";
    m_timestr=datetime.currentDateTime().toString("HH:mm:ss");  //
    systemTimer->setTimerType(Qt::PreciseTimer);
    m_sysTimestr=datetime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss");
    ui->label_sysTime->setStyleSheet("color:green;");
    ui->label_sysTime->setText(m_sysTimestr);

}
//定时取数据显示
void MainWindow::onTimeGetFrameToShow()
{
    QTime t_analysisMem;
    t_analysisMem.start();

    /*****数据获取****************/
    /***************************/
    m_picToshow=showThread->getCamOneFrame();
    //未获取到图像数据，会一直在空指针下，再获取一帧，会分配内存，导致内存过大！ 1023
    if(m_picToshow.imageBuf!=nullptr){
        ui->label_RecvOneTimePictureNums->setText(QString::number(m_getOneTimeImageNums));
        //        qDebug() << "Get the data,m_picToshow.imageBuf:"<<m_picToshow.imageBuf;
        getPicToShow();
        //每次的地址是不一样的，目前不需要在测试这里。 0404
        //        qDebug() << "After show:" <<__func__<<"picToshow.imageBuf:"<<m_picToshow.imageBuf;
        m_picToshow.imageBuf=nullptr;   //显示后，将其置空 0717--->
        ui->label_RecvPictureNums->setText(QString::number(m_getImageCount));
        qDebug()<<"get and show ,take time(ms):"<<t_analysisMem.elapsed()<<endl;
        ui->textBrowser_log->append(m_timestr+TEXT_COLOR_GREEN("图片获取")+QString::number(m_getImageCount));
        //为了获取连续多次没有取到图像数据的情况，因此一次获取正常，一次不正常，则需做减法！！ 0404
        if(m_NoDataToShow_Times>0){
            m_NoDataToShow_Times--;
        }

    }
    else
    {
        //              qDebug() << "No get data ,test picToshow.imageBuf:"<<m_picToshow.imageBuf;
        qDebug() <<"no data to show------\n";
        m_NoDataToShow_Times++;
        if(m_NoDataToShow_Times>5){
            ui->textBrowser_log->append(m_timestr+TEXT_COLOR_RED("已经有几次未获取到有效数据来显示"));
            m_NoDataToShow_Times=0;
        }
    }

}



void MainWindow::on_pushButtonCAR_clicked()
{
    qDebug()<<"first test connect:"<<m_str_addr<<"controlSocket->state():"<<controlSocket->state()<<endl;
    controlSocket->connectToHost(m_str_addr,6868); //车的控制端口，6868
    qDebug()<<"test connect:"<<m_str_addr<<"controlSocket->state():"<<controlSocket->state()<<endl;
    if(controlSocket->state()==QTcpSocket::ConnectingState){
        ui->textBrowser_log->append(m_timestr+"正在连接:"+m_str_addr+" Robot---");
    }
    controlSocket->waitForConnected(3000);
    if(controlSocket->state()==QTcpSocket::ConnectedState){
        ui->textBrowser_log->append(m_timestr+"机器人连接:"+m_str_addr+" OK++");
        initControlUI(true);
    }
    else{
        ui->textBrowser_log->append(m_timestr+"机器人连接失败--");
    }

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
    //Format_BGR888 (Format_RGB888) 从摄像头读取的默认格式是BGR，（c端服务器是这样，Python程序做cvt转换可变成其它格式）
    image = QImage(pRgbFrameBuf,nWidth, nHeight, QImage::Format_RGB888);
    if(b_grabPic==true)
    {
        QDateTime datetime;
        QString timestr=datetime.currentDateTime().toString("yyyyMMdd_HHmmss");
        QString SAVE_NAME=timestr+"_IMG_"+ QString::number(m_saveIndex)+".jpg";
        assert(pRgbFrameBuf!=nullptr); //增加，来测试是否截图时，出现错误 1128
        qDebug()<<__LINE__<<" inside,test grab error";
        qDebug() <<"SAVE_NAME "<<SAVE_NAME;
        bool saveState=false;
        saveState= image.save(SAVE_NAME,"JPG",100);
        assert(saveState==true); //增加截图是否成功判断
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

    if(pRgbFrameBuf != NULL)
    {
        //      qDebug()<<__LINE__<<"test free buf\n";
        free(pRgbFrameBuf);
        qDebug()<<__LINE__<<"add to analysis free buf\n";
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
    qDebug()<<__LINE__<<"test send CAR CMD:"<<buf<<endl;
    controlSocket->write(&buf,sizeof(buf));
}
void MainWindow::goBack(){
    char buf ='B';
    controlSocket->write(&buf,sizeof(buf));
}
void MainWindow::goLeft(){

    char buf ='L';
    qDebug()<<__LINE__<<"test send CAR CMD:"<<buf<<endl;
    controlSocket->write(&buf,sizeof(buf));
}
void MainWindow::goRight(){
    char buf ='R';
    controlSocket->write(&buf,sizeof(buf));
}
void MainWindow::goLeftHead(){
    char buf[] ="PlayMusic";
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
    char buf[] ="Cam";
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
    //    goHead();
}

//void MainWindow::on_pushButtonCARFRONT_released()
//{
//    STOP();
//}

void MainWindow::on_pushButtonCARLF_pressed()
{
    qDebug()<<"test play music"<<endl;
    goLeftHead();
}

//void MainWindow::on_pushButtonCARLF_released()
//{
//    STOP();
//}

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
    qDebug()<<__LINE__<<"test send CAR CMD\n";
    goLeft();
}

void MainWindow::on_pushButtonCARLEFT_released()
{
    //    STOP();
}



//void MainWindow::on_pushButtonCARLB_pressed()
//{
//    goLeftBack();
//}

//void MainWindow::on_pushButtonCARLB_released()
//{
//    STOP();
//}



void MainWindow::on_pushButtonCARRB_pressed()
{
    //    goRightBack();
    qDebug()<<"test capture picture"<<endl;
    camCapture();
}

//void MainWindow::on_pushButtonCARRB_released()
//{
//    STOP();
//}

void MainWindow::camCapture(){
    char buf[] ="Cam";
    controlSocket->write(buf,sizeof(buf));
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

    qDebug()<<m_timestr<<"analysis grab error"<<__LINE__<<endl;
    b_grabPic=true;
}

void MainWindow::on_pushButton_disconnect_clicked()
{
    QString tmp_qstr="<font color=\"#FF0000\">" + m_timestr + "断开连接\n"+ "</font>";
    ui->textBrowser_log->append(tmp_qstr);
    LogInfo("%s","服务器断开");
    //增加对指针的判断，让程序更健壮  0122
    if(camTimer!=nullptr){
        camTimer->stop();
    }

    //线程循环结束，线程也结束--->删除之前的线程指针--->是否需要删除？？？0116
    if(showThread!=nullptr){
        showThread->setThreadStop();
    }

    qDebug()<<__LINE__<<"Socket disconnect,test delete thread"<<endl;


    ui->pushButtonConnect->setEnabled(true);
}


void MainWindow::disconnect_Deal()
{

    QString tmp_qstr="<font color=\"#FF0000\">" + m_timestr + "服务器断开连接"+ "</font>";
    ui->textBrowser_log->append(tmp_qstr);

    camTimer->stop(); //服务器断开后，取数据定时器也停止  1113
    //立即删除线程，会报Destroyed while thread is still running的错误！！！
    ui->pushButton_disconnect->setEnabled(false);
    ui->pushButtonConnect->setStyleSheet("background-color:blue;");
    ui->pushButtonConnect->setEnabled(true);
}

void MainWindow::on_comboBox_Res_currentIndexChanged(int index)
{

    qDebug()<<"Resolution select index:"<<index;
    switch (index) {
    case Small_480p:
        cout<<"test cam  Res type:"<<Small_480p<<endl;
        m_CAM_ResolutionRatio=3;
        m_imageWidth=stCamLowRes.imageWidth;
        m_imageHeight=stCamLowRes.imageHeight;
        m_imageSize=m_imageWidth*m_imageHeight*3;
        break;
    case Common_Type720p:
        cout<<"test cam default Res type:"<<Common_Type720p<<endl;
        m_CAM_ResolutionRatio=3;
        m_imageWidth=stCommon720pRes.imageWidth;
        m_imageHeight=stCommon720pRes.imageHeight;
        m_imageSize=m_imageWidth*m_imageHeight*3;
        break;
    case Common_Type1080p:
        m_CAM_ResolutionRatio=3;
        break;
    default:
        m_CAM_ResolutionRatio=3;
    }

}

void MainWindow::ParseFromJson()
{
    std::ifstream ifs;
    ifs.open(m_ip_config_path, std::ios::binary);
    if(!ifs){
        std::cout << "Open json file Error " << std::endl;
        LogError("Open json file Error,%s \n",m_ip_config_path.c_str());
        return ;
    }
    else
    {
        std::ifstream ifs(m_ip_config_path);
        jsonxx::json json_flow;
        ifs >> json_flow;
        string  str_ip1,str_ip2,str_ip3,str_ip4;

        str_ip1       = json_flow["ip_addr1"].as_string();
        m_ip_addr1=QString::fromStdString(str_ip1);

        str_ip2       = json_flow["ip_addr2"].as_string();
        m_ip_addr2=QString::fromStdString(str_ip2);
        str_ip3       = json_flow["ip_addr3"].as_string();
        m_ip_addr3=QString::fromStdString(str_ip3);
        str_ip4       = json_flow["ip_addr4"].as_string();
        m_ip_addr4=QString::fromStdString(str_ip4);



    }
}

void MainWindow::on_comboBox_ipAddr_currentTextChanged(const QString &arg1)
{
    m_str_addr=arg1;
    qDebug()<<"current connect addr:"<<m_str_addr;
}


void MainWindow::on_pushButtonCARFRONT_clicked()
{
    goHead();
    qDebug()<<"test control car"<<endl;
}


void MainWindow::on_pushButtonCarStop_clicked()
{
    qDebug()<<"test Pause a car"<<endl;
    STOP();
}


void MainWindow::on_pushButtonCARBACK_clicked()
{
    goBack();
}


void MainWindow::on_pushButtonCARRIGHT_clicked()
{
    goRight();
}

