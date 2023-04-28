#include "mainwindow.h"
#include "ui_mainwindow.h"

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)
    , ui(new Ui::MainWindow)
{
    ui->setupUi(this);
    //mPlayer = new VideoPlayer;
    //connect(mPlayer,SIGNAL(sig_GetOneFrame(QImage)),this,SLOT(slotGetOneFrame(QImage)));
    ui->pauseButton->setDisabled(true);
    mPlayer_run_flag = false;
}

MainWindow::~MainWindow()
{
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

        disconnect(mPlayer,SIGNAL(sig_GetOneFrame(QImage)),this,SLOT(slotGetOneFrame(QImage)));
        mPlayer->stopPlay();
        mPlayer_run_flag = false;
        //改变ui
        ui->startButton->setText("Open");
        ui->pauseButton->setDisabled(true);
        delete mPlayer;
        mPlayer = nullptr;
        flag = true;
    }
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
}

