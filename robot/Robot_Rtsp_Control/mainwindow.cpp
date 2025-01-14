#include "mainwindow.h"
#include "ui_mainwindow.h"
#include <QDebug>
#include <iostream>
#include <fstream>
#include <QMessageBox>
#include "json.hpp"
#include "logging.h"
using json=nlohmann::json ;


MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)
    , ui(new Ui::MainWindow),
      b_grabPic(false)
{
    ui->setupUi(this);
    QStringList item_Resolution,item_urls;
    QStringList item_ipAddrs;
    p_systemTimer=new QTimer(this);
    p_controlSocket = new QTcpSocket(this);
    startTime();//开启系统定时
    ParseFromJson();
    for (auto i: m_qstr_ips) {
        item_ipAddrs<<i;
    }
    for (auto i: m_qstr_urls) {
        item_urls<<i;
    }


    ui->comboBox_ipAddr->addItems(item_ipAddrs);
    ui->comboBox_ipAddr->setCurrentIndex(0);
    // 增加取流地址
    ui->urlList->addItems(item_urls);
    connect(p_systemTimer,SIGNAL(timeout()),this,SLOT(systemInfoUpdate()));
    connect(p_controlSocket,SIGNAL(readyRead()),this,SLOT(recvData()));
    connect(p_controlSocket,SIGNAL(disconnected()),this,SLOT(onDisconnect()));

    ui->pauseButton->setDisabled(true);
    ui->pauseButton->setCheckable(true);  // set to use checked flag
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
    if(mPlayer != nullptr)
    {
        delete mPlayer;
        mPlayer = nullptr;
    }

}


void MainWindow::on_startButton_clicked()
{
    static bool flag = true;

    if(flag)
    {
        //将播放路径传入videoplayer
        mPlayer = new VideoPlayer;
        connect(mPlayer,SIGNAL(sig_GetOneFrame(QImage)),this,SLOT(slotGetOneFrame(QImage)));
        connect(mPlayer,SIGNAL(sig_StreamError(QString)),this,SLOT(handleStreamError(QString)));
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
            on_pauseButton_clicked(true);
        qDebug() << "fun: " <<__func__ <<"line:"<< __LINE__<< "analysis stop play or rtsp server stop (connect disconnect)";
        disconnect(mPlayer,SIGNAL(sig_GetOneFrame(QImage)),this,SLOT(slotGetOneFrame(QImage)));
        mPlayer->stopPlay();
        qDebug()<<__func__<<"line:"<<__LINE__<<"play or connect error issue";
        mPlayer_run_flag = false;
        ui->textBrowser_log->append(getCurrentTime()+":stop play");
        //改变ui
        ui->startButton->setText("Open");
        ui->pauseButton->setDisabled(true);

        flag = true;
    }
}

void MainWindow::startTime()
{
    qDebug() << "fun: " <<__func__;

    p_systemTimer->start(500);
}

void MainWindow::warningOnce(QString info)
{
    QMessageBox*  box = new  QMessageBox(QMessageBox::Warning, tr("告警"), info);
    QTimer::singleShot(2500, box, SLOT(accept()));   // 2.5s弹框自动消失
    box->exec();
    delete box;
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


void MainWindow::on_pauseButton_clicked(bool checked)
{

    qDebug()<<"line:"<<__LINE__<<"test checked"<<checked;
    if(checked)  //  not use flag variable, static variable!
    {
        qDebug()<<"line:"<<__LINE__<<"play or connect error issue";
        //暂停播放线程
        mPlayer->pause();
        //改变ui
        ui->pauseButton->setText(tr("继续播放"));
        // flag = false;
    }else {
        //开启播放线程
        mPlayer->resume();
        //改变ui
        ui->pauseButton->setText(tr("暂停播放"));
        qDebug()<<"line:"<<__LINE__<<"play or connect error issue";
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
    //    qDebug()<<__LINE__<<"save Img button clicked:";
    b_grabPic = true;
}


void MainWindow::on_pushButton_CARconnect_clicked()
{
    qDebug()<<"first test connect:"<<m_str_addr<<"controlSocket->state():"<<p_controlSocket->state();
    p_controlSocket->connectToHost(m_str_addr,6868); //车的控制端口，6868
    qDebug()<<"test connect:"<<m_str_addr<<"p_controlSocket->state():"<<p_controlSocket->state();
    LogInfo("connect robot ip:%s, state:%d",m_str_addr.toStdString().c_str(),p_controlSocket->state());
    if(p_controlSocket->state()==QTcpSocket::ConnectingState){
        ui->textBrowser_log->append(m_timestr+"正在连接:"+m_str_addr+" Robot---");
    }
    p_controlSocket->waitForConnected(3000);
    if(p_controlSocket->state()==QTcpSocket::ConnectedState){
        ui->textBrowser_log->append(m_timestr+"机器人连接:"+m_str_addr+" OK++");
        LogInfo("connect robot OK,ip:%s, state:%d",m_str_addr.toStdString().c_str(),p_controlSocket->state());
        //        initControlUI(true);
    }
    else{
        ui->textBrowser_log->append(m_timestr+"机器人连接失败--");
        LogWarning("connect robot ip:%s, state:%d",m_str_addr.toStdString().c_str(),p_controlSocket->state());
        warningOnce(tr("机器人连接失败,请检查"));
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
void MainWindow::writeCmdToSocketBuf(char cmd )
{
    long ret = -1;
    // 对写入命令是否成功做判断 2023.06
    qDebug()<<__LINE__<<"test send CAR CMD:"<<cmd;
    ret = p_controlSocket->write(&cmd,sizeof(cmd));
    LogInfo("send cmd to robot,cmd:%c, ret:%d",cmd,ret);
    if(ret < 0){
        ui->textBrowser_log->append(m_timestr+"写入命令:"+cmd+" "+"failed"+" ret:"+QString::number(ret));
    }
}

void MainWindow::writeCmdStringToSocketBuf(char *pCmd )
{
    long ret = -1;
    // 对写入命令是否成功做判断 2023.06
    qDebug()<<__LINE__<<"test send CAR CMD:"<<*pCmd<<"strlen(pCmd)"<<strlen(pCmd);
    ret = p_controlSocket->write(pCmd,strlen(pCmd)+1);
    LogInfo("send long cmd to robot,cmd:%s, ret:%d",pCmd,ret);
    if(ret < 0){
        ui->textBrowser_log->append(m_timestr+"写入命令:"+pCmd+" "+"failed"+" ret:"+QString::number(ret));
    }
}

void MainWindow::STOP(){
    char buf ='P';  // UNO单片机端，目前只支持单字母。 （python端，支持字符串） 2023.05
    writeCmdToSocketBuf(buf);
}

void MainWindow::goHead(){
    char buf ='F';
    writeCmdToSocketBuf(buf);
}
void MainWindow::goBack(){
    char buf ='B';
    p_controlSocket->write(&buf,sizeof(buf));
}
void MainWindow::goLeft(){

    char buf ='L';
    writeCmdToSocketBuf(buf);
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

void MainWindow::cleanCommandBuffer(){
    char buf[] ="Clear";
    writeCmdStringToSocketBuf(buf);
}

void MainWindow::on_pushButton_goFront_clicked()
{
    goHead();
    qDebug()<<"test control car";
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
        json json_flow;
        ifs >>json_flow;
        json one_dev_json = nlohmann::json::array(); //数组
        std::string  str_ip1,str_rtsp_url;

        for(int i=0;i<json_flow.size();i++){
            std::string tmp_str="dev"+std::to_string(i);
            qDebug()<<"test one_dev_json,line:"<<__LINE__<<QString::fromStdString(tmp_str);
         one_dev_json = json_flow[tmp_str]; // key is a string!!

         str_ip1       = one_dev_json["ip_addr"];
         str_rtsp_url =  one_dev_json["url"];
        qDebug()<<"test one_dev_json,line:"<<QString::fromStdString(str_ip1)<<" " <<QString::fromStdString(str_rtsp_url);
         m_qstr_ips.push_back(QString::fromStdString(str_ip1));
         m_qstr_urls.push_back(QString::fromStdString(str_rtsp_url));


       }

    }
}




void MainWindow::carControl()
{
    ui->pushButton_CARconnect->setEnabled(false);
    qDebug()<<"car connected OK";

}

void MainWindow::on_pushButton_stop_clicked()
{
    qDebug()<<"test Pause a car";
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
    ui->pushButton_disconnect->setEnabled(false);
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
    qDebug() <<"socket Available bytes:"<<p_controlSocket->bytesAvailable();
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

void MainWindow::on_pushButton_clearCommand_clicked()
{
    cleanCommandBuffer();
}

void MainWindow::handleStreamError(QString msg)
{
    ui->textBrowser_log->append(m_timestr+msg);
}

