#include "mainwindow.h"
#include "ui_mainwindow.h"
#include <QDebug>
#include <iostream>
#include <fstream>
#include "jsonxx/json.hpp"



MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)
    , ui(new Ui::MainWindow),
      b_grabPic(false)
{
    ui->setupUi(this);
    QStringList item_Resolution,item_ipAddrs;

    p_systemTimer=new QTimer(this);
    p_controlSocket = new QTcpSocket(this);
    startTime();//开启系统定时
    ParseFromJson();
    if(m_ip_addr1.isNull()!=true){
        item_ipAddrs<<m_ip_addr1<<m_ip_addr2<<m_ip_addr3<<m_ip_addr4;
    }

    ui->comboBox_ipAddr->addItems(item_ipAddrs);
    ui->comboBox_ipAddr->setCurrentIndex(0);
    connect(p_systemTimer,SIGNAL(timeout()),this,SLOT(systemInfoUpdate()));
    connect(p_controlSocket,SIGNAL(readyRead()),this,SLOT(recvData()));
    connect(p_controlSocket,SIGNAL(disconnected()),this,SLOT(onDisconnect()));

    ui->pauseButton->setDisabled(true);
    mPlayer_run_flag = false;
}

MainWindow::~MainWindow()
{
    if(p_systemTimer != nullptr)
    {
        delete p_systemTimer;
        p_systemTimer = nullptr;
    }
    delete ui;
}


void MainWindow::on_startButton_clicked()
{
    static bool flag = true;

    if(flag)
    {
        //将播放路径传入videoplayer
        mPlayer = new VideoPlayer;
        connect(mPlayer,SIGNAL(sig_GetOneFrame(QImage)),this,SLOT(slotGetOneFrame(QImage)));
        mPlayer->setFileName(ui->urlList->currentText());

        ui->textBrowser_log->append(getCurrentTime()+":open url for stream");
        //开启播放线程
        mPlayer->startPlay();
        mPlayer_run_flag = true;
        //改变ui
        ui->startButton->setText("Close");
        ui->pauseButton->setEnabled(true);
        flag = false;
    }else {
        //停止播放线程
        if(mPlayer->state()==Paused)
            on_pauseButton_clicked();
        qDebug() << "fun: " <<__func__ <<"line:"<< __LINE__<< "analysis stop play or rtsp server stop (connect disconnect)";
        disconnect(mPlayer,SIGNAL(sig_GetOneFrame(QImage)),this,SLOT(slotGetOneFrame(QImage)));
        mPlayer->stopPlay();
        mPlayer_run_flag = false;
        ui->textBrowser_log->append(getCurrentTime()+":stop play");
        //改变ui
        ui->startButton->setText("Open");
        ui->pauseButton->setDisabled(true);
        delete mPlayer;
        mPlayer = nullptr;
        flag = true;
    }
}

void MainWindow::startTime()
{
    qDebug() << "fun: " <<__func__;

    p_systemTimer->start(500);
}

void MainWindow::systemInfoUpdate()
{
    QDateTime datetime;
    //        qDebug() <<m_sysTimestr<<":系统时间更新测试\n";
    getCurrentTime(); // 更新当前时间
    p_systemTimer->setTimerType(Qt::PreciseTimer);
    m_sysTimestr=datetime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss");
    ui->label_sysTime->setStyleSheet("color:green;");
    ui->label_sysTime->setText(m_sysTimestr);

}


QString MainWindow::getCurrentTime()
{
    QDateTime datetime;
    //        qDebug() <<m_sysTimestr<<":系统时间更新测试\n";
    m_timestr=datetime.currentDateTime().toString("HH:mm:ss");  //

    return m_timestr;
}

void MainWindow::closeEvent(QCloseEvent *event)
{
    if(mPlayer_run_flag)
    {
        mPlayer->stopPlay();
    }
}


void MainWindow::on_pauseButton_clicked()
{
    static bool flag = true;

    if(flag)
    {

        //暂停播放线程开启播放线程
        mPlayer->pause();
        //改变ui
        ui->pauseButton->setText("play");
        flag = false;
    }else {
        //开启播放线程
        mPlayer->resume();
        //改变ui
        ui->pauseButton->setText("pause");
        flag = true;
    }
}

void MainWindow::slotGetOneFrame(QImage img)
{
    ui->widget->displayImage(img);
    if(b_grabPic == true){
        saveImage(img);
    }
}

void MainWindow::saveImage(QImage img)
{

    QDateTime datetime;
    QString timestr=datetime.currentDateTime().toString("yyyyMMdd_HHmmss");
    QString SAVE_NAME=timestr+"_IMG_"+ QString::number(m_saveIndex)+".jpg";
    //        assert(pRgbFrameBuf!=nullptr); //增加，来测试是否截图时，出现错误 1128
    //        qDebug()<<__LINE__<<" inside,test grab error";
    qDebug() <<"SAVE_NAME "<<SAVE_NAME;
    bool saveState=false;
    saveState= img.save(SAVE_NAME,"JPG",100);
    assert(saveState==true); //增加截图是否成功判断
    QString timestrLog=datetime.currentDateTime().toString("HH:mm:ss");

    ui->textBrowser_log->append(timestrLog+QString::asprintf("截图成功%s",SAVE_NAME.toStdString().c_str()));
    m_saveIndex++;
    b_grabPic = false;

}

void MainWindow::on_pushButton_saveImg_clicked()
{
    //    qDebug()<<__LINE__<<"save Img button clicked:"<<endl;
    b_grabPic = true;
}


void MainWindow::on_pushButton_CARconnect_clicked()
{
    qDebug()<<"first test connect:"<<m_str_addr<<"controlSocket->state():"<<p_controlSocket->state()<<endl;
    p_controlSocket->connectToHost(m_str_addr,6868); //车的控制端口，6868
    qDebug()<<"test connect:"<<m_str_addr<<"p_controlSocket->state():"<<p_controlSocket->state()<<endl;
    if(p_controlSocket->state()==QTcpSocket::ConnectingState){
        ui->textBrowser_log->append(m_timestr+"正在连接:"+m_str_addr+" Robot---");
    }
    p_controlSocket->waitForConnected(3000);
    if(p_controlSocket->state()==QTcpSocket::ConnectedState){
        ui->textBrowser_log->append(m_timestr+"机器人连接:"+m_str_addr+" OK++");
        //        initControlUI(true);
    }
    else{
        ui->textBrowser_log->append(m_timestr+"机器人连接失败--");
    }

    //    ui->textBrowser_log->append(p_controlSocket->peerAddress().toString());
    connect(p_controlSocket,SIGNAL(connected()),this,SLOT(carControl()));
}


void MainWindow::on_comboBox_ipAddr_currentTextChanged(const QString &arg1)
{
    m_str_addr=arg1;
    qDebug()<<"current connect addr:"<<m_str_addr;
}

/*-------------car control-----------------*/
void MainWindow::STOP(){
    char buf ='P';  // UNO单片机端，目前只支持单字母。 2023.05 （python端，支持字符串）
    long ret = 0;
    // 对写入命令是否成功做判断 2023.06
    ret = p_controlSocket->write(&buf,sizeof(buf));
    if(ret < 0){
         ui->textBrowser_log->append(m_timestr+"写入命令:"+buf+" "+"failed"+" ret:"+QString::number(ret));
    }
}

void MainWindow::goHead(){
    char buf ='F';
    qDebug()<<__LINE__<<"test send CAR CMD:"<<buf<<endl;
    p_controlSocket->write(&buf,sizeof(buf));
}
void MainWindow::goBack(){
    char buf ='B';
    p_controlSocket->write(&buf,sizeof(buf));
}
void MainWindow::goLeft(){

    char buf ='L';
    qDebug()<<__LINE__<<"test send CAR CMD:"<<buf<<endl;
    long ret = 0;
    ret = p_controlSocket->write(&buf,sizeof(buf));
    if(ret < 0){
         ui->textBrowser_log->append(m_timestr+"写入命令:"+buf+" "+"failed"+" ret:"+QString::number(ret));
    }
}
void MainWindow::goRight(){
    char buf ='R';
    p_controlSocket->write(&buf,sizeof(buf));
}
void MainWindow::goLeftHead(){
    char buf[] ="PlayMusic";
    p_controlSocket->write(buf,sizeof(buf));
}
void MainWindow::goLeftBack(){
    char buf[2] ="6";
    p_controlSocket->write(buf,sizeof(buf));
}
void MainWindow::goRightHead(){
    char buf[2] ="7";
    p_controlSocket->write(buf,sizeof(buf));
}
void MainWindow::goRightBack(){
    char buf[] ="Cam";
    p_controlSocket->write(buf,sizeof(buf));
}

void MainWindow::on_pushButton_goFront_clicked()
{
    goHead();
    qDebug()<<"test control car"<<endl;
}


void MainWindow::on_pushButtonCARBACK_clicked()
{
    goBack();
}


void MainWindow::on_pushButton_turnLeft_clicked()
{
    goLeft();
}


void MainWindow::on_pushButton_turnRight_clicked()
{
    goRight();
}


void MainWindow::ParseFromJson()
{
    std::ifstream ifs;
    ifs.open(m_ip_config_path, std::ios::binary);
    if(!ifs){
        std::cout << "Open json file Error " << std::endl;
        //        LogError("Open json file Error,%s \n",m_ip_config_path.c_str());
        return ;
    }
    else
    {
        std::ifstream ifs(m_ip_config_path);
        jsonxx::json json_flow;
        ifs >> json_flow;
        std::string  str_ip1,str_ip2,str_ip3,str_ip4;

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


void MainWindow::carControl()
{
    ui->pushButton_CARconnect->setEnabled(false);
    qDebug()<<"car connected OK";

}

void MainWindow::on_pushButton_stop_clicked()
{
    qDebug()<<"test Pause a car"<<endl;
    STOP();
}




void MainWindow::on_pushButton_disconnect_clicked()
{
    QString tmp_qstr="<font color=\"#FF0000\">" + m_timestr + "断开连接"+ "</font>";
    if(p_controlSocket->state() ==QTcpSocket::ConnectedState){
        p_controlSocket->disconnectFromHost();
    }

    ui->textBrowser_log->append(tmp_qstr);
    ui->pushButton_CARconnect->setEnabled(true);
}

void MainWindow::onDisconnect()
{
    QString tmp_qstr="<font color=\"#FF0000\">" + m_timestr + "服务器断开连接"+ "</font>";
    ui->pushButton_CARconnect->setEnabled(true);
}

void MainWindow::recvData()
{
    QByteArray bytes=nullptr;
    long long int bytesNum=0;
        qDebug()<<"\n fun:"<<__func__<<"currentThreadId:"<<QThread::currentThreadId();
//    qDebug()<<"\n fun:"<<__func__<<"size:"<<m_read_image_size;
    //    bytes.resize(MAX_LEN);//ADD 0309
//    mutex.lock();
    qDebug() <<"socket Available bytes:"<<p_controlSocket->bytesAvailable()<<endl;
    //读到一张图的字节或超时，就退出循环！！  0404
    while(p_controlSocket->waitForReadyRead(300)) //200--->300
    {
        //        bytes.append((QByteArray)m_camSocket->readAll());
        if(p_controlSocket->bytesAvailable()){
            bytes.append((QByteArray)p_controlSocket->readAll());
            QString tmp_qstr = bytes;
            ui->textBrowser_log->append(tmp_qstr);
        }
        else{

        }

//        bytesNum=m_camSocket->bytesAvailable();
     }
}
