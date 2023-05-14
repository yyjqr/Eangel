#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QMainWindow>
#include "videoplayer.h"

QT_BEGIN_NAMESPACE
namespace Ui { class MainWindow; }
QT_END_NAMESPACE

class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    MainWindow(QWidget *parent = nullptr);
    ~MainWindow();

private slots:
    void on_startButton_clicked();
    void on_pauseButton_clicked();
    void closeEvent(QCloseEvent *event);


    void slotGetOneFrame(QImage img);

private:
    Ui::MainWindow *ui;
    VideoPlayer *mPlayer;
    bool mPlayer_run_flag;
};
#endif // MAINWINDOW_H
