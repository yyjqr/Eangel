#include "mainwindow.h"

#include <QApplication>
#include <QTextCodec>   //中文支持



int main(int argc, char *argv[])
{
    QApplication a(argc, argv);
    QTextCodec::setCodecForLocale(QTextCodec::codecForName("UTF-8")); //中文字符支持
    MainWindow w;
    w.show();
    w.setWindowTitle(QString::fromLocal8Bit("机器人交互控制—v1.2"));
    return a.exec();
}
