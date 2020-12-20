/** @brief moving robot control, using cam
 *  @date 2020.12
 * @author Jack
 * @addr  yyjqr789@sina.com
 */
#include "mainwindow.h"
#include <QApplication>
#include "logging.h"
#include <QDateTime>
#include <QTextCodec>   //中文支持

int main(int argc, char *argv[])
{
    QApplication a(argc, argv);
    QDateTime datetime;
    Log camlog;
    QTextCodec::setCodecForLocale(QTextCodec::codecForName("UTF-8")); //中文字符支持
    QString timestr=datetime.currentDateTime().toString("yyyyMMdd_HHmmss");  //yyyyMMdd_HHmmss-->MMdd_HHmmss
    std::string log_file="./log/camDetect/cam";   //日志在打开cam之前创建。
    log_file+=timestr.toStdString();
    log_file+=".log";
    camlog.SetFile(log_file.c_str());
    MainWindow w;
    w.show();
    w.setWindowTitle(QString::fromLocal8Bit("移动机器人交互控制软件_v1.0.0"));
    return a.exec();
}
