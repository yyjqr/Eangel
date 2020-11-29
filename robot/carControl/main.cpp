#include "mainwindow.h"
#include <QApplication>
#include <QDateTime>
#include <QTextCodec>   //中文支持

int main(int argc, char *argv[])
{
    QApplication a(argc, argv);
    QTextCodec::setCodecForLocale(QTextCodec::codecForName("UTF-8")); //中文字符支持
    QDateTime datetime;
    QString timestr=datetime.currentDateTime().toString("MMdd_HHmmss");  //yyyyMMdd_HHmmss
    std::string log_file="/var/log/robot/cam";   //日志在打开cam之前创建。
    log_file+=timestr.toStdString();
    log_file+=".log";
    //    camlog.SetFile(log_file.c_str());

    MainWindow w;
    w.show();

    return a.exec();
}
